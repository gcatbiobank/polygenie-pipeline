#!/usr/bin/env python
"""
Script to create a toy dataset for testing the PolyGenie pipeline.

Creates:
- 10 random PRS profiles (selected from available PRSs)
- 500 random individuals (renamed to ind_1 to ind_500)
- Shuffled covariates (to break associations while preserving distributions)
- Shuffled phenotypes (to break associations while preserving distributions)
- Updated metadata files
- All in a toy_dataset folder
"""

import os
import random
import pandas as pd
import numpy as np
from pathlib import Path

def main():
    # Paths
    data_dir = Path("data")
    prs_dir = data_dir / "prs"
    phenotypes_dir = data_dir / "phenotypes"
    
    # Toy dataset root directory
    toy_dataset_dir = Path("toy_dataset")
    toy_data_dir = toy_dataset_dir / "data"
    toy_prs_dir = toy_data_dir / "prs"
    toy_phenotypes_dir = toy_data_dir / "phenotypes"
    toy_config_dir = toy_dataset_dir / "config"
    
    # Create directories
    toy_prs_dir.mkdir(parents=True, exist_ok=True)
    toy_phenotypes_dir.mkdir(parents=True, exist_ok=True)
    toy_config_dir.mkdir(parents=True, exist_ok=True)
    
    # Random seed for reproducibility
    random.seed(42)
    np.random.seed(42)
    
    # ========== STEP 1: Load all data ==========
    print("Loading original data...")
    
    # Load covariates (use TSV first, fall back to CSV)
    covars_path = data_dir / "covars.tsv"
    if covars_path.exists():
        covars = pd.read_csv(covars_path, sep="\t")
    else:
        covars = pd.read_csv(data_dir / "covars.csv", sep=";")
    
    # Load PRS metadata
    prs_metadata = pd.read_csv(data_dir / "prs_metadata.csv")
    
    # Load phenotype metadata
    phenotype_metadata = pd.read_csv(data_dir / "phenotype_metadata.csv", sep=";")
    
    print(f"Original dataset: {len(covars)} individuals, {len(prs_metadata)} PRS")
    
    # ========== STEP 2: Select 500 random individuals ==========
    print("Selecting 500 random individuals...")
    n_individuals = 500
    original_ids = random.sample(list(covars["IID"]), n_individuals)
    toy_ids = [f"ind_{i+1}" for i in range(n_individuals)]
    id_mapping = dict(zip(original_ids, toy_ids))
    
    # ========== STEP 3: Select 10 random PRS ==========
    print("Selecting 10 random PRS...")
    n_prs = 10
    selected_prs = prs_metadata.sample(n=n_prs, random_state=42).copy()
    print(f"Selected PRS: {selected_prs['name'].tolist()}")
    
    # ========== STEP 4: Subset and shuffle covariates ==========
    print("Subsetting and shuffling covariates...")
    covars_toy = covars[covars["IID"].isin(original_ids)].copy()
    # Rename IDs
    covars_toy["IID"] = covars_toy["IID"].map(id_mapping)
    
    # Shuffle each numeric column independently to break associations
    numeric_cols = covars_toy.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        covars_toy[col] = np.random.permutation(covars_toy[col].values)
    
    # Save toy covariates
    covars_toy.to_csv(toy_data_dir / "covars.tsv", sep="\t", index=False)
    print(f"Saved toy covariates: {len(covars_toy)} individuals")
    
    # ========== STEP 5: Create and shuffle PRS profiles ==========
    print("Creating toy PRS profiles...")
    
    for _, prs_row in selected_prs.iterrows():
        prs_name = prs_row["name"]
        prs_path = prs_dir / (prs_name + ".profiles")
        
        if prs_path.exists():
            prs_data = pd.read_csv(prs_path, sep="\t")
            # Subset to selected individuals
            prs_toy = prs_data[prs_data["ID"].isin(original_ids)].copy()
            # Rename IDs
            prs_toy["ID"] = prs_toy["ID"].map(id_mapping)
            # Shuffle PRS values
            prs_toy["PRS"] = np.random.permutation(prs_toy["PRS"].values)
            # Save
            prs_toy_path = toy_prs_dir / (prs_name + ".profiles")
            prs_toy.to_csv(prs_toy_path, sep="\t", index=False)
            print(f"  Created: {prs_name} ({len(prs_toy)} individuals)")
        else:
            print(f"  WARNING: {prs_path} not found, skipping")
    
    # ========== STEP 6: Update PRS metadata ==========
    print("Updating PRS metadata...")
    selected_prs["path"] = selected_prs["name"].apply(lambda x: f"data/prs/{x}.profiles")
    selected_prs.to_csv(toy_data_dir / "prs_metadata.csv", index=False)
    print(f"Saved toy PRS metadata: {len(selected_prs)} PRS")
    
    # ========== STEP 7: Subset and shuffle phenotypes ==========
    print("Subsetting and shuffling phenotypes...")
    
    phenotype_files = {
        "icd_codes": "icd_codes.csv",
        "metabolites": "metabolites.csv",
        "phecodes": "phecodes.csv",
        "questionnaire": "questionnaire.csv",
    }
    
    for file_type, filename in phenotype_files.items():
        pheno_path = phenotypes_dir / filename
        if pheno_path.exists():
            pheno_data = pd.read_csv(pheno_path, sep=";")
            # Subset to selected individuals
            pheno_toy = pheno_data[pheno_data["ID"].isin(original_ids)].copy()
            # Rename IDs
            pheno_toy["ID"] = pheno_toy["ID"].map(id_mapping)
            
            # Shuffle each column independently (except ID)
            for col in pheno_toy.columns:
                if col != "ID":
                    pheno_toy[col] = np.random.permutation(pheno_toy[col].values)
            
            # Save
            pheno_toy_path = toy_phenotypes_dir / filename
            pheno_toy.to_csv(pheno_toy_path, sep=";", index=False)
            print(f"  Saved {file_type}: {len(pheno_toy)} individuals, {len(pheno_toy.columns)-1} variables")
        else:
            print(f"  WARNING: {pheno_path} not found, skipping")
    
    # ========== STEP 8: Update phenotype metadata ==========
    print("Updating phenotype metadata...")
    phenotype_metadata_toy = phenotype_metadata.copy()
    phenotype_metadata_toy["ClassFile"] = phenotype_metadata_toy["ClassFile"].apply(
        lambda x: x.replace("data/phenotypes/", "data/phenotypes/")
    )
    phenotype_metadata_toy.to_csv(toy_data_dir / "phenotype_metadata.csv", sep=";", index=False)
    print(f"Saved toy phenotype metadata: {len(phenotype_metadata_toy)} phenotypes")
    
    # ========== STEP 9: Create toy config ==========
    print("Creating toy config...")
    toy_config = f"""# Toy Dataset Configuration
# This configuration uses a small toy dataset (500 individuals, 10 PRS)
# with shuffled variables to break associations but preserve distributions.

# Paths to input files
paths:
  phenotype_metadata: "data/phenotype_metadata.csv"
  prs_metadata: "data/prs_metadata.csv"
  covariates: "data/covars.tsv"
  prs_file: "data/prs_scores.csv"
  output_dir: "results/"
  envs_dir: "envs/"

# Analysis parameters
thresholds:
  min_cases: 10

prs:
  normalize: true
  normalization_method: "zscore"
  check_columns: ["ID", "PRS"]  # expected columns in PRS files

prevalence:
  groups: 10
  include_intermediates: true
  normalize: true

# Percentile plot settings (for COMPUTE_PRS_PERCENTILES)
percentile_plot:
  groups: 100           # e.g. 10 for deciles
  normalize: true      # whether to normalize PRS for plots

# Regression run settings (for COMPUTE_PRS_REGRESSIONS)
# List of parameter sets to run multiple regression jobs per PRS
regression_runs:
  - groups: 10
    include_intermediates: false
    normalize: true
    label: "deciles_no_intermediate"
  - groups: 10
    include_intermediates: true
    normalize: true
    label: "deciles_with_intermediate"

covariates:
  base: "age,PC1,PC2,PC3,PC4,PC5,PC6,PC7,PC8,PC9,PC10"
"""
    
    with open(toy_config_dir / "pipeline_config.yaml", "w") as f:
        f.write(toy_config)
    print(f"Saved toy pipeline config: toy_dataset/config/pipeline_config.yaml")
    
    # ========== STEP 10: Create README ==========
    readme_content = f"""# Toy Dataset

This is a toy dataset for testing the PolyGenie pipeline.

## Dataset Information

- **Individuals**: 500 (anonymized as `ind_1` to `ind_500`)
- **PRS**: 10 (randomly selected from the full dataset)
- **Phenotypes**: All phenotypes from the original dataset
- **Covariates**: All covariates from the original dataset

## Anonymization

- Individual IDs have been replaced with sequential identifiers (`ind_1` to `ind_500`)
- All variables (PRS, covariates, phenotypes) have been shuffled independently
- This breaks any real associations with traits while preserving data distributions
- Suitable for testing the pipeline without exposing real genetic associations

## Selected PRS

The following 10 PRS were randomly selected:
{', '.join(selected_prs['name'].tolist())}

## File Structure

```
toy_dataset/
├── config/
│   └── pipeline_config.yaml      # Configuration for toy dataset
├── data/
│   ├── covars.tsv                # Covariates for 500 individuals
│   ├── prs_metadata.csv          # Metadata for 10 PRS
│   ├── phenotype_metadata.csv    # Phenotype metadata
│   ├── prs/                       # PRS profiles
│   └── phenotypes/                # Phenotype files
└── README.md                      # This file
```

## Usage

To run the pipeline with this toy dataset:

```bash
cd toy_dataset
nextflow run ../main.nf -c config/pipeline_config.yaml
```

Or from the parent directory:

```bash
nextflow run main.nf -c toy_dataset/config/pipeline_config.yaml
```

## Notes

- All associations between PRS, covariates, and phenotypes are random
- This dataset is suitable for testing the pipeline infrastructure
- Do not use for any scientific analysis
"""
    
    with open(toy_dataset_dir / "README.md", "w") as f:
        f.write(readme_content)
    print(f"Saved toy dataset README: toy_dataset/README.md")
    
    # ========== SUMMARY ==========
    print("\n" + "="*60)
    print("TOY DATASET CREATED SUCCESSFULLY")
    print("="*60)
    print(f"Location: toy_dataset/")
    print(f"Individuals: {n_individuals} (renamed to ind_1 to ind_500)")
    print(f"PRS: {n_prs}")
    print(f"Selected PRS: {selected_prs['name'].tolist()}")
    print("\nNew files created:")
    print(f"  - toy_dataset/data/covars.tsv ({len(covars_toy)} individuals)")
    print(f"  - toy_dataset/data/prs/ ({n_prs} PRS profiles)")
    print(f"  - toy_dataset/data/prs_metadata.csv")
    print(f"  - toy_dataset/data/phenotypes/ (shuffled phenotypes)")
    print(f"  - toy_dataset/data/phenotype_metadata.csv")
    print(f"  - toy_dataset/config/pipeline_config.yaml")
    print(f"  - toy_dataset/README.md")
    print("\nTo run the pipeline with toy data:")
    print("  cd toy_dataset")
    print("  nextflow run ../main.nf -c config/pipeline_config.yaml")
    print("="*60)

if __name__ == "__main__":
    main()
