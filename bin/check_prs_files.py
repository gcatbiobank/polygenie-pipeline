#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Script Name   : check_prs_files.py
 Author        : Polygenie PheWAS Pipeline
 Description   :
     This script validates the list of PRS files provided in a metadata file.
     It checks for file existence, expected columns, and summarizes how many
     PRS files are valid or missing. Results are written both to a log file
     and to a filtered CSV listing the valid PRS entries.

 Input:
     - A metadata CSV file with at least one column pointing to each PRS file.
     - A PRS directory where the PRS files are staged (from Nextflow).

 Output:
     - prs_present.csv : Metadata subset with only PRS files found on disk.
     - prs_check.log   : Log file with summary statistics and missing files.

 Example:
     python3 bin/check_prs_files.py \
         --metadata data/prs_metadata.csv \
         --prs-dir ./staged_prs/ \
         --output results/preprocessing/prs_present.csv \
         --log results/preprocessing/prs_check.log
===============================================================================
"""

import os
import csv
import argparse
import pandas as pd
from datetime import datetime
from pathlib import Path


# ------------------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------------------

def check_prs_files(metadata_path: str, prs_dir: str, output_path: str, log_path: str, check_columns=None):
    """
    Validate PRS metadata file and write filtered list of available PRS files.

    Parameters
    ----------
    metadata_path : str
        Path to CSV file containing metadata of PRS files.
    prs_dir : str
        Directory where PRS files are located (staged by Nextflow).
    output_path : str
        Path to output CSV containing only rows where the PRS file exists.
    log_path : str
        Path to output log file summarizing results.
    check_columns : list, optional
        Columns expected to be present in each PRS file (e.g., ["ID", "PRS"]).
    """

    start_time = datetime.now()
    log_lines = []

    # --------------------------------------------------------------------------
    # Load PRS metadata
    # --------------------------------------------------------------------------
    log_lines.append(f"Checking PRS metadata file: {metadata_path}")
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

    metadata = pd.read_csv(metadata_path)
    if 'path' not in metadata.columns:
        raise ValueError("Metadata file must include a column named 'path' pointing to PRS files.")

    log_lines.append(f"Loaded metadata with {len(metadata)} entries.\n")

    # --------------------------------------------------------------------------
    # Check each PRS file exists in prs_dir
    # --------------------------------------------------------------------------
    log_lines.append(f"Verifying PRS files inside directory: {prs_dir}")

    # Resolve full paths relative to prs_dir

    metadata['full_path'] = metadata['path'].apply(lambda x: os.path.join(prs_dir, x))
    metadata['file_exists'] = metadata['full_path'].apply(os.path.exists)

    n_found = metadata['file_exists'].sum()
    n_missing = len(metadata) - n_found

    # --------------------------------------------------------------------------
    # Optionally verify column structure inside PRS files
    # --------------------------------------------------------------------------
    if check_columns:
        log_lines.append(f"Checking for expected columns: {check_columns}")
        missing_columns = []
        for i, row in metadata.iterrows():
            if row['file_exists']:
                try:
                    df = pd.read_csv(row['full_path'], nrows=5, sep='\t')
                    for col in check_columns:
                        if col not in df.columns:
                            missing_columns.append((row['full_path'], col))
                            metadata.loc[i, 'file_exists'] = False
                            break
                except Exception as e:
                    metadata.loc[i, 'file_exists'] = False
                    missing_columns.append((row['full_path'], f"Read error: {e}"))
        if missing_columns:
            log_lines.append("Some files are missing expected columns:")
            for path, col in missing_columns:
                log_lines.append(f"   - {path} → missing {col}")
            n_found = metadata['file_exists'].sum()

    # --------------------------------------------------------------------------
    # Write filtered list of valid PRS files
    # --------------------------------------------------------------------------
    valid_prs = metadata[metadata['file_exists']].drop(columns='file_exists')
    #os.makedirs(os.path.dirname(output_path), exist_ok=True)
    valid_prs.to_csv(output_path, index=False, sep=';', quoting=csv.QUOTE_ALL)

    log_lines.append("")
    log_lines.append(f"PRS files found     : {n_found}")
    log_lines.append(f"PRS files missing   : {n_missing}")
    log_lines.append(f"Valid PRS metadata  : {output_path}")
    log_lines.append(f"Completed in {datetime.now() - start_time}\n")

    # --------------------------------------------------------------------------
    # Write summary log
    # --------------------------------------------------------------------------
    #os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w") as f:
        f.write("\n".join(log_lines))

    # Also print to stdout for Nextflow logs
    for line in log_lines:
        print(line)

# ------------------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Check PRS metadata and verify existence of PRS files."
    )
    parser.add_argument("--metadata", required=True, help="Path to PRS metadata CSV.")
    parser.add_argument("--prs-dir", required=True, help="Directory containing staged PRS files.")
    parser.add_argument("--output", required=True, help="Path to output CSV with valid PRS.")
    parser.add_argument("--log", required=True, help="Path to output log file.")
    parser.add_argument(
        "--check-columns",
        nargs="+",
        default=None,
        help="Expected columns in each PRS file (e.g., ID PRS)."
    )
    return parser.parse_args()

# ------------------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    args = parse_args()
    check_prs_files(
        metadata_path=args.metadata,
        prs_dir=args.prs_dir,
        output_path=args.output,
        log_path=args.log,
        check_columns=args.check_columns
    )
