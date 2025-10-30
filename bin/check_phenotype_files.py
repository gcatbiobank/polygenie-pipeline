#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Script Name   : check_phenotype_files.py
 Author        : Polygenie PheWAS Pipeline
 Description   :
     Validates phenotype metadata and verifies that all expected variables
     exist in their respective ClassFile datasets. For binary variables,
     filters out those with fewer than a given minimum number of cases.

 Input:
     - Phenotype metadata CSV (with columns like Variable, ClassFile, Type, etc.)
 Output:
     - phenotypes_valid.csv : Subset of metadata for valid, analyzable variables
     - phenotypes_check.log : Log summary report
===============================================================================
"""

import os
import csv
import argparse
import pandas as pd
from datetime import datetime

def check_phenotype_files(metadata_path: str, output_path: str, log_path: str,  project_dir: str, min_cases=0):
    start_time = datetime.now()
    log_lines = []
    log_lines.append(f"🔍 Checking phenotype metadata: {metadata_path}")

    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

    meta = pd.read_csv(metadata_path, sep=';', engine='python', quotechar='"')
    if 'Variable' not in meta.columns or 'ClassFile' not in meta.columns:
        raise ValueError("Metadata must contain 'Variable' and 'ClassFile' columns.")
    
    meta['full_path'] = meta['ClassFile'].apply(lambda x: os.path.join(project_dir, x))
    meta['FileExists'] = meta['full_path'].apply(os.path.exists)
    log_lines.append(f"Total variables: {len(meta)}")
    log_lines.append(f"Unique phenotype files: {meta['ClassFile'].nunique()}")

    valid_rows = []
    missing_vars = []

    for file, subset in meta.groupby('full_path'):
        log_lines.append(f"\nChecking file: {file}")
        if not os.path.exists(file):
            log_lines.append(f"   ❌ File not found: {file}")
            continue

        try:
            df = pd.read_csv(file, sep=';')
        except Exception as e:
            log_lines.append(f"   Could not read {file}: {e}")
            continue

        for _, row in subset.iterrows():
            var = row['Variable']
            if var not in df.columns:
                log_lines.append(f"   Missing variable: {var}")
                missing_vars.append(var)
                continue

            if str(row.get('Type', '')).lower() == 'binary':
                n_cases = (df[var] == 1).sum()
                if n_cases < min_cases:
                    log_lines.append(f"   {var}: only {n_cases} cases (< {min_cases})")
                    continue

            valid_rows.append(row)

    valid_meta = pd.DataFrame(valid_rows)
    valid_meta.to_csv(output_path, index=False, sep=';', quoting=csv.QUOTE_ALL)

    log_lines.append("\nSummary")
    log_lines.append(f"Valid variables: {len(valid_meta)}")
    log_lines.append(f"Excluded variables: {len(meta) - len(valid_meta)}")
    log_lines.append(f"Completed in {datetime.now() - start_time}")

    with open(log_path, 'w') as f:
        f.write("\n".join(log_lines))

    for line in log_lines:
        print(line)

# ------------------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check phenotype metadata and files.")
    parser.add_argument("--metadata", required=True, help="Phenotype metadata CSV file.")
    parser.add_argument("--output", required=True, help="Output CSV for valid phenotypes.")
    parser.add_argument("--project-dir", required=True, help="path were the pipeline is stored.")
    parser.add_argument("--log", required=True, help="Log file path.")
    parser.add_argument("--min-cases", type=int, default=10, help="Minimum number of cases for binary traits.")
    args = parser.parse_args()

    check_phenotype_files(
        metadata_path=args.metadata,
        output_path=args.output,
        log_path=args.log,
        project_dir=args.project_dir,
        min_cases=args.min_cases
        
    )
