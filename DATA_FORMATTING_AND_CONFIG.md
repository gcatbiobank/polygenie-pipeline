# Data Formatting & Pipeline Configuration Guide

## Overview

This guide explains how to format your own data and configure the PolyGenie pipeline to run your analysis. It covers:
- ✅ Data file formats and requirements
- ✅ Metadata file specifications
- ✅ Pipeline configuration
- ✅ Best practices and common pitfalls

---

## Table of Contents

1. [Input Data Overview](#input-data-overview)
2. [Covariates File](#covariates-file)
3. [PRS Files](#prs-files)
4. [Phenotype Files](#phenotype-files)
5. [Metadata Files](#metadata-files)
6. [Configuration File](#configuration-file)
7. [File Checklist](#file-checklist)
8. [Directory Structure](#directory-structure)
9. [Examples](#examples)
10. [Troubleshooting](#troubleshooting)

---

## Input Data Overview

The pipeline requires three main types of input data:

```
Input Data
├── Covariates (1 file)
│   └── Individual-level covariates: age, PC1-PC10, sex, etc.
│
├── PRS Files (multiple files)
│   └── One TSV file per PRS with ID and PRS score
│
├── Phenotypes (multiple files)
│   ├── Continuous phenotypes (metabolites, measurements)
│   ├── Binary phenotypes (ICD codes, phecodes)
│   └── Mixed phenotypes (questionnaires)
│
└── Metadata (3 files)
    ├── prs_metadata.csv (paths to PRS files)
    ├── phenotype_metadata.csv (phenotype definitions)
    └── gwas_metadata.csv (optional: GWAS source info)
```

**Key Principle:** All files must use **consistent individual identifiers (IDs)** across covariates, PRS, and phenotypes.

---

## Covariates File

### Format

**File type:** Tab-separated values (TSV)  
**Naming:** `covars.tsv` or `covars.csv`  
**Delimiter:** Tab (`\t`) for TSV or semicolon (`;`) for CSV  
**Required columns:** `IID` (Individual ID)  
**Required values:** All numeric columns must have valid numbers (not `NA` or `null`)

### Required Columns

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `IID` | String | Unique individual identifier | `SUBJECT_001`, `ind_1` |

### Standard Columns (Recommended)

| Column | Type | Description | Notes |
|--------|------|-------------|-------|
| `age` | Integer | Age in years | Required for age-adjusted models |
| `sex` | String | Biological sex | `male`, `female`, `M`, `F` |
| `PC1` | Float | Principal component 1 | For ancestry adjustment |
| `PC2` | Float | Principal component 2 | For ancestry adjustment |
| ... | Float | More PCs | Typically PC1-PC10 |
| Other | Float/Int | Any additional covariates | Flexible |

### Example File (TSV format)

```
IID	age	sex	PC1	PC2	PC3	PC4	PC5	PC6	PC7	PC8	PC9	PC10	bmi	smoking_status
SUBJECT_001	45	male	0.00242	-0.0233	-0.0021	0.0096	-0.0021	-0.0208	-0.0343	0.0100	-0.0067	0.0183	24.5	0
SUBJECT_002	52	female	0.00582	0.00154	-0.0186	0.0271	-0.0043	-0.0218	-0.0067	0.0098	-0.0236	0.0106	28.2	1
SUBJECT_003	38	female	0.00509	-0.0243	0.00541	-0.0053	-0.0171	-0.0112	0.0171	-0.0041	-0.0063	-0.0088	22.1	0
```

### Key Requirements

✅ **DO:**
- Include `IID` column as first column
- Use numeric values for all numeric columns
- Handle missing values consistently (omit rows with missing covariates)
- Use consistent delimiter throughout
- Ensure IID matches exactly with PRS and phenotype files

❌ **DON'T:**
- Use `NA`, `NULL`, `.`, or empty strings for numeric columns
- Mix delimiters (e.g., some tabs, some commas)
- Use non-ASCII characters in IIDs
- Include duplicates IIDs
- Use spaces in IID values

### Missing Value Handling

**Recommendation:** Remove individuals with missing covariate values before running the pipeline.

```bash
# In R
covars <- read.table("covars.tsv", header=TRUE, sep="\t")
covars_clean <- na.omit(covars)
write.table(covars_clean, "covars.tsv", sep="\t", quote=FALSE, row.names=FALSE)
```

```python
# In Python
import pandas as pd
covars = pd.read_csv("covars.tsv", sep="\t")
covars_clean = covars.dropna()
covars_clean.to_csv("covars.tsv", sep="\t", index=False)
```

---

## PRS Files

### Format

**File type:** Tab-separated values (TSV)  
**Naming:** `{prs_name}.profiles` (e.g., `asthma.profiles`, `t2d.profiles`)  
**Delimiter:** Tab (`\t`)  
**Required columns:** `ID`, `PRS`

### File Structure

| Column | Type | Description |
|--------|------|-------------|
| `ID` | String | Individual identifier (matches IID in covars) |
| `PRS` | Float | Polygenic Risk Score (any numeric value) |

### Example File

```
ID	PRS
SUBJECT_001	0.823
SUBJECT_002	2.500
SUBJECT_003	2.228
SUBJECT_004	0.687
SUBJECT_005	0.583
```

### File Organization

```
data/
└── prs/
    ├── asthma.profiles
    ├── t2d.profiles
    ├── copd.profiles
    ├── cad.profiles
    ├── stroke.profiles
    ├── ckd.profiles
    ├── ibd.profiles
    ├── psoriasis.profiles
    ├── ra.profiles
    └── ad.profiles
```

### Key Requirements

✅ **DO:**
- Name files descriptively (e.g., `asthma.profiles`, not `prs_1.profiles`)
- Use lowercase names (e.g., `t2d`, not `T2D`)
- Include all individuals from covariates file
- Use consistent IDs across PRS files
- Store in `data/prs/` directory

❌ **DON'T:**
- Use spaces in filenames
- Mix ID formats (e.g., some with prefix, some without)
- Include missing values (NaN, NA, etc.)
- Use extremely large or small values without checking
- Store in different directories

### Handling Missing Individuals

If some individuals lack PRS scores:

```python
# Add rows with NA for missing individuals
import pandas as pd
import numpy as np

# Load PRS
prs = pd.read_csv("t2d.profiles", sep="\t")

# Load covariates to get all IIDs
covars = pd.read_csv("covars.tsv", sep="\t")

# Add missing individuals
all_ids = set(covars["IID"])
prs_ids = set(prs["ID"])
missing_ids = all_ids - prs_ids

if missing_ids:
    missing_df = pd.DataFrame({"ID": list(missing_ids), "PRS": np.nan})
    prs = pd.concat([prs, missing_df])
    prs = prs.sort_values("ID").reset_index(drop=True)
    prs.to_csv("t2d.profiles", sep="\t", index=False)
```

---

## Phenotype Files

### Overview

Phenotype files contain the outcome variables for association testing. The pipeline supports:
- **Continuous phenotypes** (e.g., metabolite levels, measurements)
- **Binary phenotypes** (e.g., disease status, ICD codes)
- **Mixed phenotypes** (e.g., questionnaire responses)

### Format

**File type:** CSV with semicolon delimiter  
**Naming:** Descriptive names (e.g., `questionnaire.csv`, `metabolites.csv`)  
**Delimiter:** Semicolon (`;`)  
**Required columns:** `ID` (Individual identifier)  
**Other columns:** Phenotype variables

### Example: Questionnaire Phenotypes

```
ID;height_cm;weight_kg;bmi;systolic_bp;diastolic_bp;hdl_cholesterol;ldl_cholesterol;triglycerides
SUBJECT_001;165.5;63.75;23.27;109.0;78.67;1.45;3.21;1.12
SUBJECT_002;172.5;89.25;30.05;135.0;86.33;1.12;3.89;1.95
SUBJECT_003;160.0;53.45;20.83;115.0;74.67;1.68;2.95;0.87
```

### Example: ICD Codes (Binary)

```
ID;E11;E14;I10;I50;K21;M19;N18
SUBJECT_001;0;0;1;0;0;0;1
SUBJECT_002;1;0;1;1;0;1;0
SUBJECT_003;0;0;0;0;0;0;0
```

### Example: Metabolites (Continuous)

```
ID;glucose_mmol;ldl_cholesterol_mmol;hdl_cholesterol_mmol;triglycerides_mmol;apolipoprotein_a
SUBJECT_001;5.2;3.21;1.45;1.12;1.89
SUBJECT_002;6.1;3.89;1.12;1.95;2.15
SUBJECT_003;4.8;2.95;1.68;0.87;1.76
```

### File Organization

```
data/
└── phenotypes/
    ├── questionnaire.csv      (mixed continuous/binary)
    ├── metabolites.csv        (continuous)
    ├── icd_codes.csv          (binary)
    ├── phecodes.csv           (binary)
    └── lab_measurements.csv   (continuous)
```

### Key Requirements

✅ **DO:**
- Name files descriptively
- Use consistent delimiter (`;`) throughout
- Include all individuals from covariates
- Use consistent ID format
- Document what each column represents
- Include column headers

❌ **DON'T:**
- Mix delimiters
- Use spaces in column names (use underscores instead)
- Include ID duplicates
- Mix phenotype types in one file (e.g., don't mix binary and continuous without documentation)
- Use special characters in column names (use letters, numbers, underscores only)

### Handling Missing Values

For phenotype files, missing values can be handled in different ways:

```python
import pandas as pd
import numpy as np

# Option 1: Remove individuals with any missing phenotypes
df = pd.read_csv("metabolites.csv", sep=";")
df_clean = df.dropna()

# Option 2: Keep missing values (represented as NaN/NA)
# Pipeline typically excludes individuals with missing phenotypes from that specific analysis

# Save
df_clean.to_csv("metabolites.csv", sep=";", index=False)
```

---

## Metadata Files

### 1. PRS Metadata (`prs_metadata.csv`)

**Purpose:** Maps PRS names to their profile files and provides metadata

**Format:**
- Delimiter: Comma (`,`)
- Required columns: `name`, `path`, `label`, `sex`

**Example:**

```csv
name,path,label,sex
asthma,data/prs/asthma.profiles,Asthma,both
t2d,data/prs/t2d.profiles,Type 2 Diabetes,both
copd,data/prs/copd.profiles,COPD,both
cad,data/prs/cad.profiles,Coronary Artery Disease,both
stroke,data/prs/stroke.profiles,Stroke,both
ckd,data/prs/ckd.profiles,Chronic Kidney Disease,both
ibd,data/prs/ibd.profiles,Inflammatory Bowel Disease,both
psoriasis,data/prs/psoriasis.profiles,Psoriasis,both
ra,data/prs/ra.profiles,Rheumatoid Arthritis,both
ad,data/prs/ad.profiles,Alzheimer's Disease,both
```

**Column Definitions:**

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `name` | String | Internal PRS identifier (matches filename) | `t2d`, `asthma` |
| `path` | String | Relative path to PRS profile file | `data/prs/t2d.profiles` |
| `label` | String | Human-readable label for display | `Type 2 Diabetes` |
| `sex` | String | Sex applicability: `male`, `female`, or `both` | `both` |

**Key Requirements:**
- `name` must match the filename without `.profiles` extension
- `path` should be relative to project root
- `sex` must be exactly `male`, `female`, or `both`
- Include all PRS you want to analyze

---

### 2. Phenotype Metadata (`phenotype_metadata.csv`)

**Purpose:** Defines phenotype variables, their types, and covariates to use

**Format:**
- Delimiter: Semicolon (`;`)
- Required columns: `Variable`, `Description`, `Class`, `ClassFile`, `Domain`, `Type`, `Sex`, `Covariates`

**Example:**

```csv
Variable;Description;Class;ClassFile;Domain;Type;Sex;Covariates
height_cm;Height;Questionnaire;data/phenotypes/questionnaire.csv;Anthropometry;continuous;both;sex
weight_kg;Weight;Questionnaire;data/phenotypes/questionnaire.csv;Anthropometry;continuous;both;sex
bmi;Body Mass Index;Questionnaire;data/phenotypes/questionnaire.csv;Anthropometry;continuous;both;sex
systolic_bp;Systolic Blood Pressure;Questionnaire;data/phenotypes/questionnaire.csv;Cardiovascular;continuous;both;age,sex
E11;Type 2 Diabetes;ICD;data/phenotypes/icd_codes.csv;Metabolic;binary;both;age,sex
I10;Essential Hypertension;ICD;data/phenotypes/icd_codes.csv;Cardiovascular;binary;both;age,sex
glucose;Glucose;Metabolites;data/phenotypes/metabolites.csv;Metabolism;continuous;both;age,sex,PC1,PC2,PC3
ldl_cholesterol;LDL Cholesterol;Metabolites;data/phenotypes/metabolites.csv;Lipids;continuous;both;age,sex,PC1,PC2,PC3
```

**Column Definitions:**

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `Variable` | String | Column name in phenotype file | `height_cm`, `E11`, `glucose` |
| `Description` | String | Human-readable description | `Height`, `Type 2 Diabetes` |
| `Class` | String | Phenotype class/category | `Questionnaire`, `ICD`, `Metabolites` |
| `ClassFile` | String | Path to phenotype file containing this variable | `data/phenotypes/questionnaire.csv` |
| `Domain` | String | Subcategory/measurement type | `Anthropometry`, `Cardiovascular` |
| `Type` | String | `continuous` or `binary` | `continuous` for measurements, `binary` for disease status |
| `Sex` | String | Sex applicability: `male`, `female`, or `both` | `both` |
| `Covariates` | String | Comma-separated list of covariates to include in regression | `age,sex,PC1,PC2` |

**Key Requirements:**
- `Variable` must exactly match column name in phenotype file
- `ClassFile` must be valid path to phenotype file
- `Type` must be exactly `continuous` or `binary`
- `Covariates` must be comma-separated, with no spaces
- All covariates listed must exist in covariates file

**Covariate Selection Tips:**
- Continuous phenotypes: `age,sex,PC1,PC2,PC3` (typically)
- Binary diseases: `age,sex` (or `age,sex,PC1,PC2,PC3` for ancestry adjustment)
- Metabolites: `age,sex,PC1,PC2,PC3,PC4,PC5` (more PCs for metabolites)
- Height/weight: Include `sex` (strong sex effect)

---

### 3. GWAS Metadata (`gwas_metadata.csv`) - Optional

**Purpose:** Documents the GWAS source for each PRS (for reference, not used by pipeline)

**Format:**
- Delimiter: Comma (`,`)
- Recommended columns: `name`, `label`, `n`, `n_cases`, `n_controls`, `population`

**Example:**

```csv
name,label,n,n_cases,n_controls,population
asthma,Asthma,490000,100000,390000,European
t2d,Type 2 Diabetes,898130,74124,824006,European
copd,COPD,35694,10127,25567,European
cad,Coronary Artery Disease,184305,60801,123504,European
stroke,Stroke,446696,67162,379534,European
```

**Column Definitions:**

| Column | Type | Description | Optional |
|--------|------|-------------|----------|
| `name` | String | PRS name (matches prs_metadata.csv) | No |
| `label` | String | Human-readable label | No |
| `n` | Integer | Total sample size | Yes |
| `n_cases` | Integer | Number of cases (binary traits) | Yes |
| `n_controls` | Integer | Number of controls (binary traits) | Yes |
| `population` | String | Ancestry/population | Yes |

---

## Configuration File

### Overview

The configuration file (`pipeline_config.yaml`) controls how the pipeline runs. It specifies data paths, analysis parameters, and output settings.

### File Location

```
config/
└── pipeline_config.yaml
```

### Basic Structure

```yaml
# Paths to input files
paths:
  phenotype_metadata: "data/phenotype_metadata.csv"
  prs_metadata: "data/prs_metadata.csv"
  covariates: "data/covars.tsv"
  output_dir: "results/"
  envs_dir: "envs/"

# Analysis parameters
thresholds:
  min_cases: 10

prs:
  normalize: true
  normalization_method: "zscore"
  check_columns: ["ID", "PRS"]

# Other analysis settings...
```

### Complete Configuration Reference

```yaml
# ========== FILE PATHS ==========
paths:
  # Path to phenotype metadata file (semicolon-separated CSV)
  phenotype_metadata: "data/phenotype_metadata.csv"
  
  # Path to PRS metadata file (comma-separated CSV)
  prs_metadata: "data/prs_metadata.csv"
  
  # Path to covariates file (TSV format)
  covariates: "data/covars.tsv"
  
  # Path where results will be saved
  output_dir: "results/"
  
  # Path to conda environments directory
  envs_dir: "envs/"

# ========== ANALYSIS PARAMETERS ==========
thresholds:
  # Minimum number of cases required for binary phenotype analysis
  # Phenotypes with fewer cases will be excluded
  min_cases: 10

prs:
  # Whether to normalize PRS before analysis
  normalize: true
  
  # Normalization method: "zscore" or other
  normalization_method: "zscore"
  
  # Expected column names in PRS files
  check_columns: ["ID", "PRS"]

# ========== PREVALENCE BY PERCENTILE ==========
prevalence:
  # Number of groups for prevalence calculation (e.g., 10 = deciles)
  groups: 10
  
  # Include intermediate percentiles
  include_intermediates: true
  
  # Normalize PRS for percentile calculation
  normalize: true

# ========== PERCENTILE PLOTS ==========
percentile_plot:
  # Number of groups for percentile plots (e.g., 100 = percentiles)
  groups: 100
  
  # Normalize PRS for plots
  normalize: true

# ========== REGRESSION ANALYSIS ==========
# List of parameter sets to run multiple regression jobs per PRS
# Each entry creates a separate analysis run
regression_runs:
  # First analysis: Deciles without intermediate percentiles
  - groups: 10
    include_intermediates: false
    normalize: true
    label: "deciles_no_intermediate"
  
  # Second analysis: Deciles with intermediate percentiles
  - groups: 10
    include_intermediates: true
    normalize: true
    label: "deciles_with_intermediate"
  
  # Third analysis: Quartiles without intermediate percentiles
  - groups: 4
    include_intermediates: false
    normalize: true
    label: "quartiles_no_intermediate"
  
  # Fourth analysis: Quartiles with intermediate percentiles
  - groups: 4
    include_intermediates: true
    normalize: true
    label: "quartiles_with_intermediate"

# ========== COVARIATES ==========
covariates:
  # Base covariates to include in all models (comma-separated)
  # Phenotype-specific covariates are added from phenotype_metadata.csv
  base: "age,PC1,PC2,PC3,PC4,PC5,PC6,PC7,PC8,PC9,PC10"
```

### Configuration File Examples

#### Example 1: Minimal Configuration (Toy Dataset)

```yaml
paths:
  phenotype_metadata: "data/phenotype_metadata.csv"
  prs_metadata: "data/prs_metadata.csv"
  covariates: "data/covars.tsv"
  output_dir: "results/"
  envs_dir: "envs/"

thresholds:
  min_cases: 10

prs:
  normalize: true
  normalization_method: "zscore"
  check_columns: ["ID", "PRS"]

prevalence:
  groups: 10
  include_intermediates: true
  normalize: true

percentile_plot:
  groups: 100
  normalize: true

regression_runs:
  - groups: 10
    include_intermediates: false
    normalize: true
    label: "deciles"

covariates:
  base: "age,PC1,PC2,PC3,PC4,PC5"
```

#### Example 2: Complete Configuration (Production)

```yaml
paths:
  phenotype_metadata: "/absolute/path/to/phenotype_metadata.csv"
  prs_metadata: "/absolute/path/to/prs_metadata.csv"
  covariates: "/absolute/path/to/covars.tsv"
  output_dir: "/results/path/"
  envs_dir: "envs/"

thresholds:
  min_cases: 20

prs:
  normalize: true
  normalization_method: "zscore"
  check_columns: ["ID", "PRS"]

prevalence:
  groups: 10
  include_intermediates: true
  normalize: true

percentile_plot:
  groups: 100
  normalize: true

regression_runs:
  - groups: 10
    include_intermediates: false
    normalize: true
    label: "deciles_no_int"
  - groups: 10
    include_intermediates: true
    normalize: true
    label: "deciles_with_int"
  - groups: 4
    include_intermediates: false
    normalize: true
    label: "quartiles_no_int"

covariates:
  base: "age,PC1,PC2,PC3,PC4,PC5,PC6,PC7,PC8,PC9,PC10"
```

#### Example 3: Sex-Specific Configuration

```yaml
paths:
  phenotype_metadata: "data/phenotype_metadata.csv"
  prs_metadata: "data/prs_metadata.csv"
  covariates: "data/covars.tsv"
  output_dir: "results_sex_specific/"
  envs_dir: "envs/"

thresholds:
  min_cases: 10

prs:
  normalize: true
  normalization_method: "zscore"
  check_columns: ["ID", "PRS"]

prevalence:
  groups: 10
  include_intermediates: true
  normalize: true

percentile_plot:
  groups: 100
  normalize: true

# Separate analyses by sex
regression_runs:
  - groups: 10
    include_intermediates: false
    normalize: true
    label: "deciles_males"
    sex_filter: "male"
  - groups: 10
    include_intermediates: false
    normalize: true
    label: "deciles_females"
    sex_filter: "female"

covariates:
  # Note: don't include 'sex' if doing sex-specific analysis
  base: "age,PC1,PC2,PC3,PC4,PC5,PC6,PC7,PC8,PC9,PC10"
```

### Key Configuration Parameters

| Parameter | Type | Description | Default | Notes |
|-----------|------|-------------|---------|-------|
| `phenotype_metadata` | String | Path to phenotype metadata file | Required | Must exist |
| `prs_metadata` | String | Path to PRS metadata file | Required | Must exist |
| `covariates` | String | Path to covariates file | Required | Must exist |
| `output_dir` | String | Output directory path | Required | Will be created if missing |
| `min_cases` | Integer | Minimum cases for binary phenotype | 10 | Increase for larger studies |
| `normalize` | Boolean | Normalize PRS (zscore) | true | Recommended to keep true |
| `groups` | Integer | Number of percentile groups | 10 | 4=quartiles, 10=deciles, 100=percentiles |
| `include_intermediates` | Boolean | Include intermediate percentiles | true | See pipeline output for details |

---

## File Checklist

Before running the pipeline, verify all files:

### ✅ Data Files

- [ ] `data/covars.tsv`
  - [ ] Contains `IID` column as first column
  - [ ] All numeric columns have valid numbers (no NA/NULL)
  - [ ] Tab-separated format
  - [ ] No duplicate IIDs

- [ ] `data/prs/*.profiles` (one per PRS)
  - [ ] Named descriptively (e.g., `asthma.profiles`)
  - [ ] Contains `ID` and `PRS` columns
  - [ ] All individuals from covars.tsv are included
  - [ ] No missing PRS values

- [ ] `data/phenotypes/*.csv` (one or more)
  - [ ] Semicolon-separated format
  - [ ] Contains `ID` column (matches IID in covars)
  - [ ] Column names are descriptive and simple (letters/numbers/underscores only)
  - [ ] Data types are appropriate (numeric for continuous, 0/1 for binary)

### ✅ Metadata Files

- [ ] `data/prs_metadata.csv`
  - [ ] Contains columns: `name`, `path`, `label`, `sex`
  - [ ] All rows have valid values
  - [ ] Paths point to existing PRS files
  - [ ] Names match filenames

- [ ] `data/phenotype_metadata.csv`
  - [ ] Contains columns: `Variable`, `Description`, `Class`, `ClassFile`, `Domain`, `Type`, `Sex`, `Covariates`
  - [ ] All rows have valid values
  - [ ] Variables match phenotype file column names
  - [ ] Covariates exist in covars.tsv
  - [ ] ClassFile paths are correct

### ✅ Configuration File

- [ ] `config/pipeline_config.yaml`
  - [ ] All file paths are correct and files exist
  - [ ] YAML syntax is valid (use online validator if unsure)
  - [ ] `min_cases` is appropriate for your data
  - [ ] `covariates.base` lists existing covariates

### ✅ Directory Structure

```
your_project/
├── config/
│   └── pipeline_config.yaml
├── data/
│   ├── covars.tsv
│   ├── prs_metadata.csv
│   ├── phenotype_metadata.csv
│   ├── prs/
│   │   ├── asthma.profiles
│   │   ├── t2d.profiles
│   │   └── ... (more PRS)
│   └── phenotypes/
│       ├── questionnaire.csv
│       ├── metabolites.csv
│       ├── icd_codes.csv
│       └── ... (more phenotypes)
├── main.nf
└── nextflow.config
```

---

## Directory Structure

### Recommended Project Layout

```
polygenie-pipeline/
├── main.nf                          # Main Nextflow workflow
├── nextflow.config                  # Nextflow runtime config
├── config/
│   ├── pipeline_config.yaml         # Your analysis config
│   └── pipeline_config.example.yaml # Example config
├── data/
│   ├── covars.tsv                   # Individual covariates
│   ├── prs_metadata.csv             # PRS metadata
│   ├── phenotype_metadata.csv       # Phenotype definitions
│   ├── gwas_metadata.csv            # (Optional) GWAS source info
│   ├── prs/                         # PRS profile files
│   │   ├── asthma.profiles
│   │   ├── t2d.profiles
│   │   ├── cad.profiles
│   │   └── ... (more PRS)
│   └── phenotypes/                  # Phenotype files
│       ├── questionnaire.csv
│       ├── metabolites.csv
│       ├── icd_codes.csv
│       ├── phecodes.csv
│       └── ... (more phenotypes)
├── scripts/
│   ├── preprocessing/
│   ├── analysis/
│   ├── db/
│   └── ... (utility scripts)
├── results/                         # Output (created by pipeline)
│   ├── preprocessing/
│   ├── regressions/
│   ├── percentiles/
│   └── log/
├── db/
│   ├── schema.sql
│   └── polygenie.db
├── app/
│   ├── app.py
│   ├── assets/
│   └── ... (Dash app)
└── README.md
```

### Minimal Example Setup

For testing purposes, you need only:

```
my_test/
├── config/
│   └── pipeline_config.yaml
├── data/
│   ├── covars.tsv
│   ├── prs_metadata.csv
│   ├── phenotype_metadata.csv
│   ├── prs/
│   │   ├── prs1.profiles
│   │   └── prs2.profiles
│   └── phenotypes/
│       └── phenotypes.csv
└── (main.nf and scripts from polygenie-pipeline)
```

---

## Examples

### Example 1: Complete Toy Dataset Setup

**Step 1:** Create directory structure
```bash
mkdir -p my_analysis/config my_analysis/data/prs my_analysis/data/phenotypes
cd my_analysis
```

**Step 2:** Create covariates file (`data/covars.tsv`)
```
IID	age	sex	PC1	PC2	PC3	PC4	PC5	PC6	PC7	PC8	PC9	PC10
ind_1	45	male	0.00242	-0.0233	-0.0021	0.0096	-0.0021	-0.0208	-0.0343	0.0100	-0.0067	0.0183
ind_2	52	female	0.00582	0.00154	-0.0186	0.0271	-0.0043	-0.0218	-0.0067	0.0098	-0.0236	0.0106
ind_3	38	female	0.00509	-0.0243	0.00541	-0.0053	-0.0171	-0.0112	0.0171	-0.0041	-0.0063	-0.0088
```

**Step 3:** Create PRS files (`data/prs/asthma.profiles`)
```
ID	PRS
ind_1	0.823
ind_2	2.500
ind_3	2.228
```

**Step 4:** Create phenotype file (`data/phenotypes/phenotypes.csv`)
```
ID;bmi;asthma_diagnosis;cholesterol_mg_dl
ind_1;24.5;0;195
ind_2;28.2;1;220
ind_3;22.1;0;180
```

**Step 5:** Create PRS metadata (`data/prs_metadata.csv`)
```csv
name,path,label,sex
asthma,data/prs/asthma.profiles,Asthma,both
```

**Step 6:** Create phenotype metadata (`data/phenotype_metadata.csv`)
```csv
Variable;Description;Class;ClassFile;Domain;Type;Sex;Covariates
bmi;Body Mass Index;Questionnaire;data/phenotypes/phenotypes.csv;Anthropometry;continuous;both;age,sex
asthma_diagnosis;Asthma Diagnosis;Medical;data/phenotypes/phenotypes.csv;Respiratory;binary;both;age,sex
cholesterol_mg_dl;Cholesterol;Lab;data/phenotypes/phenotypes.csv;Lipids;continuous;both;age,sex,PC1,PC2
```

**Step 7:** Create config file (`config/pipeline_config.yaml`)
```yaml
paths:
  phenotype_metadata: "data/phenotype_metadata.csv"
  prs_metadata: "data/prs_metadata.csv"
  covariates: "data/covars.tsv"
  output_dir: "results/"
  envs_dir: "envs/"

thresholds:
  min_cases: 1

prs:
  normalize: true
  normalization_method: "zscore"
  check_columns: ["ID", "PRS"]

regression_runs:
  - groups: 2
    include_intermediates: false
    normalize: true
    label: "binary_groups"

covariates:
  base: "age,PC1,PC2"
```

### Example 2: Real Study Setup

For a larger study with multiple phenotypes and PRS:

**Covariates:** 10,000 individuals, 15 covariates
**PRS:** 50 PRS files
**Phenotypes:** 5 phenotype files with 500+ phenotypes combined

File sizes:
- `covars.tsv`: ~2 MB
- All `*.profiles`: ~50 MB
- All phenotype CSVs: ~500 MB
- Total: ~550 MB

Expected runtime: 2-4 hours

---

## Troubleshooting

### Common Issues

#### ❌ "File not found" error

**Cause:** Path in config doesn't exist or is incorrect

**Solution:**
```bash
# Verify file exists
ls -la config/pipeline_config.yaml
ls -la data/covars.tsv
ls -la data/prs/asthma.profiles

# Check config paths
grep "path:" config/pipeline_config.yaml
```

#### ❌ "Column not found" error

**Cause:** Phenotype variable in metadata doesn't exist in file

**Solution:**
```bash
# Check column names in phenotype file
head -1 data/phenotypes/questionnaire.csv | tr ';' '\n'

# Compare with phenotype_metadata.csv
grep "questionnaire" data/phenotype_metadata.csv | cut -d';' -f1
```

#### ❌ "ID mismatch" error

**Cause:** Individual IDs differ across files

**Solution:**
```bash
# Extract IIDs from each file
cut -f1 data/covars.tsv | sort > covars_ids.txt
cut -f1 data/prs/asthma.profiles | sort > prs_ids.txt
cut -d';' -f1 data/phenotypes/questionnaire.csv | sort > pheno_ids.txt

# Compare
diff covars_ids.txt prs_ids.txt
diff covars_ids.txt pheno_ids.txt
```

#### ❌ "Invalid YAML" error

**Cause:** Syntax error in config file

**Solution:**
```bash
# Validate YAML online or with python
python3 -c "import yaml; yaml.safe_load(open('config/pipeline_config.yaml'))"

# Common issues:
# - Incorrect indentation (use spaces, not tabs)
# - Missing colons after keys
# - Unquoted strings with special characters
```

#### ❌ "No valid cases" after filtering

**Cause:** `min_cases` threshold too high or insufficient data

**Solution:**
- Lower `min_cases` in config
- Check number of cases in phenotypes
- Verify phenotype types (binary vs continuous)

#### ❌ Empty regression results

**Cause:** Missing values or no variation in phenotypes

**Solution:**
```bash
# Check for missing values
python3 << 'EOF'
import pandas as pd
pheno = pd.read_csv("data/phenotypes/questionnaire.csv", sep=";")
print(pheno.isnull().sum())
print(pheno.describe())
EOF

# Remove rows with missing values if needed
pheno_clean = pheno.dropna()
pheno_clean.to_csv("data/phenotypes/questionnaire_clean.csv", sep=";", index=False)
```

---

## Best Practices

✅ **DO:**
1. Validate all file formats before running pipeline
2. Use consistent ID formatting across all files
3. Document data sources and phenotype definitions
4. Keep config file organized and commented
5. Test with small subset first
6. Save intermediate results
7. Version control your data/config
8. Backup original data before processing

❌ **DON'T:**
1. Use spaces in filenames or IDs
2. Mix delimiters across files
3. Include special characters in column names
4. Run pipeline directly on production data (test first)
5. Modify data during pipeline execution
6. Use extremely high `min_cases` for small studies
7. Forget to document changes to data
8. Share pipeline outputs without anonymizing

---

## References

- [Main README](README.md)
- [Toy Dataset Creation Guide](DATASET_CREATION.md)
- [Database Schema](db/schema.sql)
- [Pipeline Workflow](main.nf)

---

## Support

For questions or issues with data formatting:
1. Check examples in this document
2. Review the schema in [db/schema.sql](db/schema.sql)
3. Look at example toy dataset structure
4. Check [Troubleshooting](#troubleshooting) section

