#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
Script Name   : compute_percentiles.py
Author        : Polygenie PheWAS Pipeline
Description   :
    Compute PRS percentiles and prevalence/mean per percentile.
    - Always compute aggregated z-score (PRS_agg) and sex-stratified z-score (PRS_sex)
    - For sex-specific PRS or phenotypes, only compute for relevant sex
    - Output CSV for plotting: percentile vs prevalence/mean, aggregated and sex-specific

Inputs:
    --prs-file          : CSV with columns [ID, PRS, sex]
    --prs-name          : short name of the prs
    --prs-metadata      : CSV with columns [name, path, sex]
    --phenotype-metadata: CSV with columns [Variable, Type, Sex, ClassFile]
    --covariates        : CSV with columns [ID, sex, ...]
    --percentiles       : number of percentiles (default 100)
    --normalize         : whether to compute z-score normalization
    --output            : output CSV file path

===============================================================================
"""

import os
import argparse
import pandas as pd
import numpy as np

def normalize_prs(df, pheno_sex):
    """Compute aggregated, male, and female z-score PRS."""
    df = df.copy()
    if pheno_sex in ['male','female']:
        df[f'PRS_{pheno_sex}'] = (df['PRS'] - df['PRS'].mean()) / df['PRS'].std(ddof=1)
    else:
        # Global PRS
        df['PRS_agg'] = (df['PRS'] - df['PRS'].mean()) / df['PRS'].std(ddof=1)

        # Default fallbacks
        df['PRS_male'] = df['PRS_agg']
        df['PRS_female'] = df['PRS_agg']

        if 'sex' in df.columns:
            male_mask   = df['sex'].str.lower() == 'male'
            female_mask = df['sex'].str.lower() == 'female'

            if male_mask.any():
                df.loc[male_mask, 'PRS_male'] = (
                    (df.loc[male_mask, 'PRS'] - df.loc[male_mask, 'PRS'].mean())
                    / df.loc[male_mask, 'PRS'].std(ddof=1)
                )

            if female_mask.any():
                df.loc[female_mask, 'PRS_female'] = (
                    (df.loc[female_mask, 'PRS'] - df.loc[female_mask, 'PRS'].mean())
                    / df.loc[female_mask, 'PRS'].std(ddof=1)
                )

    return df

def compute_percentiles(prs_df, phenotypes, n_percentiles=100, prs_sex=None, normalize=True):
    """
    Compute percentiles and prevalence/mean for each phenotype.
    """
    results = []
    # Filter for PRS sex if needed
    if prs_sex in ['male','female']:
        prs_df = prs_df[prs_df['sex'] == prs_sex]

    # Cache loaded phenotype files by path
    pheno_file_cache = {}

    # Loop over phenotypes
    for _, pheno in phenotypes.iterrows():
        var = pheno['Variable']
        p_type = pheno['Type'].lower()
        pheno_sex = pheno['Sex']
        pheno_file_path = pheno['full_path']
        # Load and cache phenotype file if not already loaded
        if pheno_file_path not in pheno_file_cache:
            pheno_file_cache[pheno_file_path] = pd.read_csv(pheno_file_path, sep=';')
        pheno_file_df = pheno_file_cache[pheno_file_path]

        # Filter for phenotype sex if needed
        pheno_df = prs_df.copy()
        if pheno_sex in ['male','female']:
            pheno_df = pheno_df[pheno_df['sex'] == pheno_sex]
        
        pheno_df = pd.merge(pheno_df, pheno_file_df[['ID', var]])

        # Normalize if requested
        if normalize:
            pheno_df = normalize_prs(pheno_df, pheno_sex)
        else:
            pheno_df['PRS_agg'] = pheno_df['PRS']
            pheno_df['PRS_male'] = pheno_df['PRS']
            pheno_df['PRS_female'] = pheno_df['PRS']

        # Choose correct PRS column
        if pheno_sex == 'male':
            prs_col = ['PRS_male']
        elif pheno_sex == 'female':
            prs_col = ['PRS_female']
        else:
            prs_col = ['PRS_agg', 'PRS_female', 'PRS_male']
        
        for prs_var in prs_col:
            if prs_var == 'PRS_female':
                tmp = pheno_df[pheno_df['sex'] == 'female']
            elif prs_var == 'PRS_male':
                tmp = pheno_df[pheno_df['sex'] == 'male']        
            else:
                tmp = pheno_df
            
            # Compute percentiles
            tmp['percentile'] = pd.qcut(
                tmp[prs_var],
                n_percentiles,
                labels=False,
                duplicates='drop'
            )

            for perc in sorted(tmp['percentile'].dropna().unique()):
                subset = tmp[tmp['percentile'] == perc]

                if len(subset) == 0:
                    continue

                if p_type == 'binary':
                    value = subset[var].sum() / len(subset)
                else:
                    value = subset[var].mean()

                results.append({
                    'PRS_column': prs_var,
                    'PRS_name': prs_name,
                    'phenotype': var,
                    'percentile': int(perc),
                    'value': float(value),
                    'sex': pheno_sex if pheno_sex in ['male', 'female'] else 'both',
                    'n': int(len(subset))
                })

    return pd.DataFrame(results)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prs-file", required=True)
    parser.add_argument("--prs-name", required=True)
    parser.add_argument("--prs-metadata", required=True)
    parser.add_argument("--phenotype-metadata", required=True)
    parser.add_argument("--covariates", required=True)
    parser.add_argument("--percentiles", type=int, default=100)
    parser.add_argument("--normalize", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    # -----------------------------------------------------------------
    # SKIP IF OUTPUT ALREADY EXISTS
    # -----------------------------------------------------------------
    if os.path.exists(args.output) and os.path.getsize(args.output) > 0:
        print(f"✅ Skipping {args.prs_name}: output already exists → {args.output}")
        exit(0)

    # Load files
    prs_df = pd.read_csv(args.prs_file, sep='\t', engine='python', quotechar='"') ## TODO improve parsing
    prs_meta = pd.read_csv(args.prs_metadata, sep=';', engine='python', quotechar='"')
    phenotypes = pd.read_csv(args.phenotype_metadata, sep=';', engine='python', quotechar='"')
    covars = pd.read_csv(args.covariates, sep=';', engine='python', quotechar='"')

    log_lines = []
    # Merge covariates
    prs_df = prs_df.merge(covars[['ID','sex']], left_on='ID', right_on='ID', how='left')

    # Determine PRS sex from metadata
    prs_name = args.prs_name
    prs_sex = prs_meta.loc[prs_meta['name']==prs_name, 'sex'].values[0]


    # Compute percentiles and prevalence/mean
    df_out = compute_percentiles(prs_df, phenotypes, n_percentiles=args.percentiles, prs_sex=prs_sex, normalize=args.normalize)
    df_out.to_csv(args.output, index=False)

    with open(f"{prs_name}_percentiles.log", "w") as f:
        f.write("\n".join(log_lines))
