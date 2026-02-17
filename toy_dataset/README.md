# Toy Dataset

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
scz, asi, palsy, restless_leg, fev1, diet_fat, osteoarthritis, reti_count, mono, neut_perc

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
