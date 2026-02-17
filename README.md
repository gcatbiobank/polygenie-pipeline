![Polygenie](app/assets/PolyGenie.png)

*Unearthing Genetic Links with Polygenic Scores*

---

## Overview

PolyGenie is a toolkit for phenome-wide association studies (PheWAS) using Polygenic Risk Scores (PRS). It combines a Nextflow pipeline for statistical analysis with an interactive web dashboard for exploring results.

- Run regression analyses across hundreds of phenotypes using PRS
- Compute disease prevalence by PRS percentile — overall and sex-stratified
- Explore results interactively via a Dash web application
- Supports binary and continuous phenotypes (ICD codes, metabolites, questionnaires, and more)

---

## Implementation Example

An example implementation using the GCAT cohort is hosted at [polygenie.igtp.cat](https://polygenie.igtp.cat/). The pipeline was run on over 100 PRS across a wide variety of phenotypes, including diseases, metabolites, and questionnaire-derived variables. The standard interface was extended to include additional cohort-specific information.

---

## Quick Start

### 1. Install Dependencies

PolyGenie requires Python 3.10+ and Nextflow. Create the conda environment:

```bash
conda env create -f envs/polygenie-pipeline.yml
conda activate polygenie-pipeline
```

### 2. Prepare Your Data

You will need the following files before running the pipeline:

| File | Description |
|------|-------------|
| `data/phenotype_metadata.csv` | Maps each phenotype variable to its data file, type, and covariates |
| `data/prs_metadata.csv` | Maps each PRS to its profile file and label |
| `data/covars.tsv` | Individual-level covariates (age, sex, principal components, etc.) |
| `data/prs/*.profiles` | One tab-delimited file per PRS with columns `ID` and `PRS` |
| `data/phenotypes/*.csv` | Wide-format phenotype tables, one file per category |

See the [Input Data Formats](#input-data-formats) section for detailed file specifications.

### 3. Run the Pipeline

```bash
nextflow run main.nf -c config/your_config.yaml
```

The pipeline will compute regressions, generate percentile data, and write results to the output directory specified in your config file.

### 4. Build the Database

```bash
python scripts/db/db_loader.py config/your_config.yaml
```

If no config file is provided, the script will fall back to default paths.

### 5. Launch the Web App

```bash
cd app
python app.py
```

Open [http://127.0.0.1:8050](http://127.0.0.1:8050) in your browser. Select a PRS and percentile grouping to explore the PheWAS plot and prevalence charts.

---

## Project Structure

| Folder / File | Purpose |
|---------------|---------|
| `main.nf` | Main Nextflow workflow entry point |
| `app/` | Dash web application (`app.py` and UI components) |
| `config/` | Nextflow configuration files |
| `data/` | Input data and reference files (GWAS metadata, etc.) |
| `db/` | SQLite database and schema definition |
| `envs/` | Conda environment YAML |
| `modules/` | Nextflow process modules |
| `results/` | Pipeline outputs: regressions, percentiles, summaries |
| `scripts/` | Helper scripts for pipeline steps and database loading |

---

## Input Data Formats

### Phenotype Metadata

A semicolon-delimited CSV mapping each phenotype to its data file and analysis settings.

```csv
Variable;Description;Class;ClassFile;Domain;Type;Sex;Covariates
BMI;Body Mass Index;Questionnaire;data/phenotypes/questionnaire.csv;Measurements;continuous;both;sex
```

| Column | Description |
|--------|-------------|
| `Variable` | Internal variable name (must match the column name in the data file) |
| `Description` | Human-readable label shown in the web app |
| `Class` | High-level phenotype category (e.g., Questionnaire, ICD) |
| `ClassFile` | Relative path to the data file containing this variable |
| `Type` | `continuous` or `binary` |
| `Sex` | `male`, `female`, or `both` |
| `Covariates` | Comma-separated covariates to include in regression |

### PRS Metadata

A comma-delimited CSV mapping each PRS to its profile file.

```csv
name,path,label,sex
frailty,data/prs/frailty.profiles,Fried Frailty,both
```

### Covariates File

A tab-delimited file with one row per individual. Must include an `IID` column, plus any covariates used in regression (e.g., `age`, `sex`, `PC1`–`PC10`).

```tsv
IID	PC1	PC2	age	sex
IND001	0.002	-0.023	52	female
```

### PRS Profile Files

One tab-delimited file per PRS. Individual IDs must match the covariates and phenotype files.

```tsv
ID	PRS
IND001	0.876
```

### Phenotype Files

Wide-format semicolon-delimited CSVs, one per phenotype category. Binary phenotypes should be encoded as `0`/`1`.

```csv
ID;A02;A03;BMI
IND001;0;1;24.3
```

---

## Configuration

Create a YAML configuration file to specify input paths and analysis parameters. A template is provided in `config/`.

The config file defines the input paths, filtering thresholds, and how the PRS will be partitioned for analysis. Under `regression_runs`, you can define multiple analysis jobs per PRS — each specifying the number of quantile groups, whether to normalize the PRS, and whether intermediate groups are pooled into the reference category (e.g. top decile vs. all others) or excluded so that only the top and bottom groups are compared.

```yaml
# Paths to input files
paths:
  phenotype_metadata: "data/phenotype_metadata.csv"
  prs_metadata: "data/prs_metadata.csv"
  covariates: "data/covars.csv"
  output_dir: "results/"
  envs_dir: "envs/"

# Minimum number of cases in a binary phenotype to be included in the analysis
thresholds:
  min_cases: 10

# Percentile plot settings (for COMPUTE_PRS_PERCENTILES)
percentile_plot:
  groups: 100      # number of bins for the prevalence-by-percentile plots
  normalize: true  # whether to normalize PRS before plotting

# Regression run settings (for COMPUTE_PRS_REGRESSIONS)
# Each entry defines one regression job per PRS — multiple runs are supported
regression_runs:
  - groups: 10
    include_intermediates: false
    normalize: true
    label: "deciles_no_intermediate"
  - groups: 10
    include_intermediates: true
    normalize: true
    label: "deciles_with_intermediate"
  - groups: 4
    include_intermediates: false
    normalize: true
    label: "quartiles_no_intermediate"
  - groups: 4
    include_intermediates: true
    normalize: true
    label: "quartiles_with_intermediate"

# Covariates included in all regressions
covariates:
  base: "age,PC1,PC2,PC3,PC4,PC5,PC6,PC7,PC8,PC9,PC10"
```

Run the pipeline with your config:

```bash
nextflow run main.nf -c config/your_config.yaml
```

---

## Web Application

The Dash-based web app provides three main views for exploring pipeline results:

- **PheWAS Plot** — Shows association strength (effect size, p-value) across all tested phenotypes for a selected PRS
- **Prevalence by Percentile** — Displays disease prevalence across PRS percentiles, deciles, or quartiles — overall, male, and female
- **Top Hits Table** — Sortable table of the strongest associations

**To launch:**

1. Run the pipeline and build the database (see [Quick Start](#quick-start))
2. `cd app && python app.py`
3. Open [http://127.0.0.1:8050](http://127.0.0.1:8050) in your browser
4. Select a PRS from the dropdown and choose a percentile grouping
5. Click any point on the PheWAS plot to view prevalence curves

---

## Try It: Demo Dataset

Not ready with your own data? Use the built-in demo dataset to explore the pipeline immediately. It contains 500 anonymized individuals with 10 PRS profiles — all associations are randomized so no real genetic information is exposed.

```bash
# Run the pipeline with the demo dataset config
nextflow run main.nf -c config/pipeline_config.yaml

# Results will be in results/
```

> **Note:** The demo dataset is intended for testing and exploration only. All associations are randomized and it is not suitable for scientific analysis or publication.

---

## License & Citation

PolyGenie is released under the MIT License — see [LICENSE](LICENSE) for details.

If you use this tool in your research, please cite the relevant GWAS sources and acknowledge the PolyGenie pipeline.