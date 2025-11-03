#!/usr/bin/env python3
import argparse
import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
from joblib import Parallel, delayed
import os
import csv


def normalize_prs(df):
    """
    Normalize Polygenic Risk Score (PRS) values by converting them to z-scores.
    
    Parameters:
        df (pandas.DataFrame): DataFrame containing a 'PRS' column to normalize
        
    Returns:
        pandas.DataFrame: Copy of input DataFrame with normalized PRS values
        
    Note:
        Z-score normalization: (x - mean) / standard_deviation
        Uses sample standard deviation (ddof=1)
    """
    df = df.copy()
    df['PRS'] = (df['PRS'] - df['PRS'].mean()) / df['PRS'].std(ddof=1)
    return df


def assign_prs_groups(df, n_groups=10, include_intermediates=False):
    """
    Categorize individuals into binary PRS groups based on their PRS scores.
    
    Parameters:
        df (pandas.DataFrame): DataFrame containing PRS values
        n_groups (int, optional): Number of quantile groups to create (default=10 for deciles)
        include_intermediates (bool, optional): If True, compares top group vs all others.
                                              If False, compares top vs bottom group only.
    
    Returns:
        pandas.DataFrame: DataFrame with added columns:
            - PRS_group_raw: Original quantile group numbers
            - PRS_group: Binary classification (1=top group, 0=reference group)
            
    Note:
        - Handles duplicate values in quantile calculation
        - Drops rows where group assignment results in NaN
        - Returns only samples in the comparison groups
    """
    df = df.copy()
    df['PRS_group_raw'] = pd.qcut(df['PRS'], n_groups, labels=False, duplicates='drop')

    max_group = df['PRS_group_raw'].max()
    min_group = df['PRS_group_raw'].min()

    if include_intermediates:
        df['PRS_group'] = np.where(df['PRS_group_raw'] == max_group, 1, 0)
    else:
        df['PRS_group'] = np.where(df['PRS_group_raw'] == max_group, 1,
                                   np.where(df['PRS_group_raw'] == min_group, 0, np.nan))

    df = df.dropna(subset=['PRS_group'])
    df['PRS_group'] = df['PRS_group'].astype(int)
    return df


def run_regression(merged_df, prs_name, var, p_type, covariates, n_groups, include_intermediates):
    """
    Perform regression analysis between PRS groups and a phenotype, adjusting for covariates.
    
    Parameters:
        merged_df (pandas.DataFrame): DataFrame containing PRS, phenotype and covariate data
        prs_name (str): Name identifier for the PRS being analyzed
        var (str): Name of the phenotype variable column
        p_type (str): Type of phenotype - 'binary' for logistic regression, else linear regression
        covariates (list): List of covariate column names to include in the model
        n_groups (int): Number of quantile groups for PRS categorization
        include_intermediates (bool): Whether to include intermediate groups in reference category
        
    Returns:
        dict or None: Dictionary containing regression results if successful:
            - PRS_name: Name of the PRS
            - phenotype: Name of the phenotype
            - coef: Regression coefficient for PRS_group
            - pvalue: P-value for PRS_group coefficient
            - n_groups: Number of groups used
            - include_intermediates: Whether intermediates were included
            Returns None if regression fails or PRS_group term is missing
            
    Note:
        - Uses statsmodels for regression (logit for binary, ols for continuous)
        - Automatically drops missing values in phenotype and PRS
        - Handles errors gracefully and reports them to stdout
    """
    merged_df = merged_df.dropna(subset=[var, 'PRS'])

    # Assign PRS groups
    merged_df = assign_prs_groups(merged_df, n_groups, include_intermediates)

    # Build formula
    formula = f"{var} ~ PRS_group + " + " + ".join(covariates)

    try:
        if p_type == 'binary':
            model = smf.logit(formula=formula, data=merged_df)
        else:
            model = smf.ols(formula=formula, data=merged_df)

        fit = model.fit(disp=False)

        if 'PRS_group' in fit.params.index:
            return {
                'PRS_name': prs_name,
                'phenotype': var,
                'coef': fit.params['PRS_group'],
                'pvalue': fit.pvalues['PRS_group'],
                'n_groups': n_groups,
                'include_intermediates': include_intermediates
            }
        else:
            return None
    except Exception as e:
        print(f"Error running regression for {var}: {e}")
        return None


def process_pheno(pheno, prs_df, base_covariates, args):
    """
    Process a single phenotype for PRS regression analysis.
    
    Parameters:
        pheno (pandas.Series): Row from phenotype metadata containing:
            - Variable: Name of the phenotype variable
            - Type: Phenotype type ('binary' or continuous)
            - Sex: Sex specificity ('male', 'female', or 'both')
            - full_path: Path to phenotype data file
            - Covariates: Optional additional covariates (comma-separated)
        prs_df (pandas.DataFrame): DataFrame containing PRS scores and base covariates
        base_covariates (list): List of base covariate names to include in all analyses
        args (argparse.Namespace): Command line arguments including:
            - prs_name: Name of the PRS
            - normalize: Whether to normalize PRS
            - n_groups: Number of PRS groups
            - include_intermediates: Whether to include intermediate groups
            
    Returns:
        dict or None: Results from run_regression() if successful, None if failed
        
    Note:
        - Handles sex-specific analyses by filtering data appropriately
        - Merges PRS data with phenotype data
        - Supports additional covariates specified in phenotype metadata
        - Optionally normalizes PRS before analysis
    """
    var = pheno['Variable']
    p_type = pheno['Type'].lower()
    pheno_sex = pheno.get('Sex', 'both')
    pheno_file = pheno['full_path']
    extra_covariates = pheno.get('Covariates', None)

    if extra_covariates and isinstance(extra_covariates, str):
        extra_covariates = [c.strip() for c in extra_covariates.split(',') if c.strip()]
    else:
        extra_covariates = []

    covariates = base_covariates + extra_covariates

    # Use a global cache for phenotype files
    if not hasattr(process_pheno, "pheno_file_cache"):
        process_pheno.pheno_file_cache = {}
    pheno_file_cache = process_pheno.pheno_file_cache

    if pheno_file not in pheno_file_cache:
        pheno_file_cache[pheno_file] = pd.read_csv(pheno_file, sep=';', engine='python')
    pheno_data = pheno_file_cache[pheno_file]

    merged_df = prs_df.copy()
    merged_df = pd.merge(merged_df, pheno_data[['ID', var]], on='ID', how='inner')

    if pheno_sex in ['male', 'female'] and 'sex' in merged_df.columns:
        merged_df = merged_df[merged_df['sex'] == pheno_sex]

    if args.normalize:
        merged_df = normalize_prs(merged_df)

    return run_regression(
        merged_df,
        args.prs_name,
        var,
        p_type,
        covariates,
        args.n_groups,
        args.include_intermediates
    )


def main():
    """
    Main function for the PRS regression analysis pipeline.
    
    This function:
        1. Parses command line arguments for analysis configuration
        2. Loads required data files:
           - PRS scores
           - Phenotype metadata
           - Covariate data
           - PRS metadata
        3. Handles sex-specific PRS filtering
        4. Processes each phenotype in parallel (if specified)
        5. Collates results and writes to CSV file
        
    The output filename includes the number of groups and whether
    intermediate groups were included in the analysis.
    
    Command line arguments handled:
        --prs-file: Path to PRS data file
        --prs-name: Name identifier for the PRS
        --prs-metadata: Path to PRS metadata file
        --phenotype-metadata: Path to phenotype metadata file
        --covariates: Path to covariate data file
        --base-covariates: List of base covariates to include
        --output: Output file path
        --n-groups: Number of PRS groups (default=10)
        --normalize: Whether to normalize PRS
        --include-intermediates: Whether to include intermediate groups
        --n-jobs: Number of parallel jobs (default=1)
    """
    parser = argparse.ArgumentParser(description="Compute PRS regressions by percentile group")
    parser.add_argument("--prs-file", required=True, help="PRS file (ID, PRS)")
    parser.add_argument("--prs-name", required=True, help="PRS short name")
    parser.add_argument("--prs-metadata", required=True, help="PRS metadata file")
    parser.add_argument("--phenotype-metadata", required=True,
                        help="CSV with phenotype info (Variable, Type, Sex, full_path, [Covariates])")
    parser.add_argument("--covariates", required=True, help="CSV with covariate data (ID, covars...)")
    parser.add_argument("--base-covariates", required=True,
                        help="Comma-separated list of base covariates (e.g. 'CURRENT_AGE,GENDER,PC1,PC2,PC3')")
    parser.add_argument("--output", required=True, help="Output CSV file")
    parser.add_argument("--n-groups", type=int, default=10, help="Number of PRS groups (e.g. 10 for deciles)")
    parser.add_argument("--normalize", action='store_true', help="Normalize PRS before grouping")
    parser.add_argument("--include-intermediates", action='store_true',
                        help="Use rest (all but top) as reference instead of only bottom group")
    parser.add_argument("--n-jobs", type=int, default=1, help="Parallel jobs")
    args = parser.parse_args()
    print("===== PRS Regression Analysis Parameters =====")
    for arg, value in vars(args).items():
        print(f"{arg}: {value}")
    print("==============================================")

    # Load data
    prs_df = pd.read_csv(args.prs_file, sep='\t', engine='python', quotechar='"')
    phenotypes = pd.read_csv(args.phenotype_metadata, sep=';', engine='python', quotechar='"')
    covars = pd.read_csv(args.covariates, sep=';', engine='python', quotechar='"')
    prs_meta = pd.read_csv(args.prs_metadata, sep=';', engine='python', quotechar='"')


    # Merge PRS and covariates
    prs_df = prs_df.merge(covars, on='ID', how='left')
    prs_name = args.prs_name

    prs_sex = prs_meta.loc[prs_meta['name']==prs_name, 'sex'].values[0]
    if prs_sex in ['male','female']:
        prs_df = prs_df[prs_df['sex'] == prs_sex]

    # Parse base covariates
    base_covariates = [c.strip() for c in args.base_covariates.split(',') if c.strip()]

    # Run regressions
    results = Parallel(n_jobs=args.n_jobs)(
        delayed(process_pheno)(pheno, prs_df, base_covariates, args)
        for _, pheno in phenotypes.iterrows()
    )

    # Filter valid results
    results = [r for r in results if r is not None]

    if results:
        df_out = pd.DataFrame(results)
        suffix = f"{args.n_groups}groups_{'withInter' if args.include_intermediates else 'noInter'}"
        out_file = os.path.splitext(args.output)[0] + f"_{suffix}.csv"
        df_out.to_csv(out_file, sep=';', index=False, quoting=csv.QUOTE_ALL)
        print(f"✅ Results written to {out_file}")
    else:
        print("⚠️ No valid results generated.")


if __name__ == "__main__":
    main()
