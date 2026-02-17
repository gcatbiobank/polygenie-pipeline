#!/usr/bin/env python3
import sqlite3
import pandas as pd
import glob
import re
import hashlib
from pathlib import Path
import yaml
import sys
import os

# Default config path
default_config_file = Path("config/pipeline_config.yaml")

# Check if a path was supplied via command line
if len(sys.argv) > 1:
    config_file = Path(sys.argv[1])
else:
    config_file = default_config_file

# Load config
if config_file.exists():
    with open(config_file) as f:
        config = yaml.safe_load(f)
        output_dir = config.get('paths', {}).get('output_dir', 'results')
        gwas_meta_path = config.get('paths', {}).get('gwas_metadata', 'data/gwas_metadata.csv')
else:
    output_dir = 'results'
    gwas_meta_path = 'data/gwas_metadata.csv'

print(f"Using config: {config_file}")
print(f"Output dir: {output_dir}")
print(f"GWAS metadata path: {gwas_meta_path}")

DB = Path("db/polygenie.db")
SCHEMA = Path("db/schema.sql")
RESULTS = Path(output_dir)
PHENO_FILE = RESULTS / "preprocessing/phenotypes_valid.csv"
PRS_MANIFEST_FILE = RESULTS / "preprocessing/prs_present.csv"
GWAS_META_FILE = Path(gwas_meta_path)

# ----------------------------
# Helpers
# ----------------------------
def make_run_id(prs, label, groups, normalize, inter):
    """Generate a short unique run ID from parameters."""
    s = f"{prs}|{label}|{groups}|{normalize}|{inter}"
    return hashlib.sha1(s.encode()).hexdigest()[:12]

# ----------------------------
# Database functions
# ----------------------------
def create_schema(con, schema_file):
    """Create database schema if it does not exist."""
    with open(schema_file) as f:
        con.executescript(f.read())
    print("Schema created / verified.")

def load_phenotypes(con, pheno_file):
    """Load phenotype / target table."""
    if not pheno_file.exists():
        print("Phenotype file not found:", pheno_file)
        return
    pheno = pd.read_csv(pheno_file, sep=';', engine='python', quotechar='"')
    pheno.rename(columns={
        "Variable":"target_code",
        "Description":"description",
        "Class":"target_class",
        "ClassFile":"class_file",
        "Domain":"domain",
        "Type":"target_type",
        "Sex":"sex",
        "Covariates":"covariates",
        "full_path":"full_path",
        "FileExists":"file_exists"
    }, inplace=True)
    pheno = pheno[[
        "target_code","description","target_class","class_file",
        "domain","target_type","sex","covariates","full_path","file_exists"
    ]].drop_duplicates()
    rows = [tuple(x) for x in pheno.where(pd.notnull(pheno), None).to_numpy()]
    con.executemany("""
        INSERT OR REPLACE INTO target 
        (target_code, description, target_class, class_file, domain, target_type, sex, covariates, full_path, file_exists)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, rows)
    con.commit()
    print(f"Inserted/updated {len(rows)} phenotype rows into 'target' table")

def load_regressions(con, results_dir):
    """Load PheWAS/regression results from CSVs."""
    regression_files = glob.glob(str(results_dir / "regressions" / "*_regression_*.csv"))
    for reg in regression_files:
        fname = Path(reg).name
        m = re.match(r"(.*)_regression_(.*)_(\d+)groups_(withInter|noInter)\.csv", fname)
        if not m:
            print("Skipping:", fname)
            continue
        prs, label, groups, inter = m.groups()
        groups = int(groups)
        include_inter = (inter == "withInter")
        normalize = True
        run_id = make_run_id(prs, label, groups, normalize, include_inter)
        print(f"Loading run {run_id} → {fname}")

        # Register run
        con.execute("""
            INSERT OR REPLACE INTO analysis_run
            (run_id, prs_name, label, n_groups, include_intermediates, normalize)
            VALUES (?,?,?,?,?,?)
        """, (run_id, prs, label, groups, include_inter, normalize))

        # Load regression CSV
        df = pd.read_csv(reg, sep=';', engine='python', quotechar='"')
        df.rename(columns={"phenotype":"target_code"}, inplace=True)
        df["run_id"] = run_id
        df["prs_name"] = prs

        # Map column names to DB fields
        if 'OR' in df.columns: df['odds_ratio'] = df['OR']
        if 'OR_CI_lower' in df.columns: df['ci_low'] = df['OR_CI_lower']
        if 'OR_CI_upper' in df.columns: df['ci_high'] = df['OR_CI_upper']
        if 'pvalue' in df.columns: df['p_value'] = df['pvalue']
        if 'coef' in df.columns: df['beta'] = df['coef']

        # Fill missing expected columns
        for col in ['SE','CI_lower','CI_upper','n','n_groups','include_intermediates','covariates','formula','sex_filter']:
            if col not in df.columns: df[col] = None

        # Compute logpxdir
        import numpy as np
        def effect_sign(row):
            if row.get('type') == 'continuous' and pd.notnull(row.get('beta')):
                return np.sign(row['beta'])
            if row.get('type') == 'binary' and pd.notnull(row.get('odds_ratio')):
                try: return np.sign(row['odds_ratio'] - 1.0)
                except: return 0
            return 0
        df['logpxdir'] = df.apply(lambda r: (-np.log10(r['p_value']) * effect_sign(r)) if pd.notnull(r['p_value']) and r['p_value']>0 else None, axis=1)

        # Insert into phewas_result
        save_cols = [
            'run_id','prs_name','target_code','odds_ratio','ci_low','ci_high','p_value','beta',
            'SE','CI_lower','CI_upper','n','n_groups','include_intermediates','covariates','formula','sex_filter'
        ]
        rows = [tuple(x) for x in df[save_cols].where(pd.notnull(df[save_cols]), None).to_numpy()]
        if rows:
            con.executemany("""
                INSERT OR REPLACE INTO phewas_result
                (run_id, prs_name, target_code, odds_ratio, ci_low, ci_high, p_value, beta,
                 SE, CI_lower, CI_upper, n, n_groups, include_intermediates, covariates, formula, sex_filter)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, rows)
            con.commit()
            print(f"Inserted/updated {len(rows)} phewas_result rows for run {run_id}")

def load_percentiles(con, results_dir):
    """Load percentile/prevalence results."""
    perc_files = glob.glob(str(results_dir / "percentiles" / "*_percentiles.csv"))
    for perc_file in perc_files:
        prs_name = Path(perc_file).stem.replace('_percentiles','')
        df = pd.read_csv(perc_file)
        df["run_id"] = df.get("run_id") or None

        # Expected columns in DB
        expected_cols = ['run_id','PRS_name','phenotype','PRS_column','value','percentile','sex','n']
        df = df[[c for c in expected_cols if c in df.columns]].copy()
        df.rename(columns={
            "phenotype":"target_code",
            "PRS_column":"prs_column",
            "value":"prevalence"
        }, inplace=True)
        df = df.where(pd.notnull(df), None)
        rows = [tuple(x) for x in df.to_numpy()]
        if rows:
            con.executemany("""
                INSERT OR REPLACE INTO prevalence
                (run_id, prs_name, target_code, prs_column, prevalence, percentile, sex, n)
                VALUES (?,?,?,?,?,?,?,?)
            """, rows)
            con.commit()
            print(f"Inserted/updated {len(rows)} prevalence rows for {prs_name}")

def load_prs_manifest(con, manifest_file):
    """Load PRS manifest CSV."""
    if not manifest_file.exists(): return
    df = pd.read_csv(manifest_file, sep=';', engine='python', quotechar='"')
    df.rename(columns={'name':'prs_name','path':'path','label':'label','sex':'sex','full_path':'full_path'}, inplace=True)
    df = df[['prs_name','path','label','sex','full_path']].drop_duplicates()
    rows = [tuple(x) for x in df.where(pd.notnull(df), None).to_numpy()]
    if rows:
        con.executemany("""
            INSERT OR REPLACE INTO prs_manifest
            (prs_name, path, label, sex, full_path)
            VALUES (?,?,?,?,?)
        """, rows)
        con.commit()
        print(f"Inserted/updated {len(rows)} prs_manifest rows")

def load_gwas_metadata(con, gwas_file):
    """Load GWAS metadata CSV."""
    if not gwas_file.exists(): return
    df = pd.read_csv(gwas_file)
    expected = ['name','path','label','n_cases','n_controls','n','population','sex','sampling','prevalence',
                'mean','sd','source','sumstats_source','prevalence_mean_source','comments']
    for col in expected:
        if col not in df.columns: df[col] = None
    df = df[expected].drop_duplicates()
    rows = [tuple(x) for x in df.where(pd.notnull(df), None).to_numpy()]
    if rows:
        con.executemany("""
            INSERT OR REPLACE INTO gwas_metadata
            (name, path, label, n_cases, n_controls, n, population, sex, sampling, prevalence,
             mean, sd, source, sumstats_source, prevalence_mean_source, comments)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, rows)
        con.commit()
        print(f"Inserted/updated {len(rows)} gwas_metadata rows")

# ----------------------------
# Main script
# ----------------------------
if __name__ == "__main__":
    con = sqlite3.connect(DB)
    create_schema(con, SCHEMA)
    load_phenotypes(con, PHENO_FILE)
    load_regressions(con, RESULTS)
    load_percentiles(con, RESULTS)
    load_prs_manifest(con, PRS_MANIFEST_FILE)
    load_gwas_metadata(con, GWAS_META_FILE)
    con.close()
    print("Database build completed.")

