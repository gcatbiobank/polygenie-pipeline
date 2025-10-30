#!/usr/bin/env python3
import argparse
import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
from joblib import Parallel, delayed
import os
import csv


def normalize_prs(df):
    """Normalize PRS as z-score."""
    df = df.copy()
    df['PRS'] = (df['PRS'] - df['PRS'].mean()) / df['PRS'].std(ddof=1)
    return df


def assign_prs_groups(df, n_groups=10, include_intermediates=False):
    """
    Create a binary PRS group: 1 for top group, 0 for reference (bottom or rest).
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
    """Run linear or logistic regression for one phenotype."""
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

    pheno_data = pd.read_csv(pheno_file, sep=';', engine='python')

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
