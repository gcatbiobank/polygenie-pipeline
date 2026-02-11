# Toy Dataset Creation Guide

## Overview

This guide explains how to create an anonymized toy dataset for testing the PolyGenie pipeline. The toy dataset allows developers and users to experiment with the pipeline infrastructure without exposing real genetic associations or individual-level data.

**Key Features:**
- 📊 **500 anonymized individuals** (renamed to `ind_1` to `ind_500`)
- 🧬 **10 randomly selected PRS** from the full dataset
- 🔀 **All variables shuffled** to break real associations while preserving data distributions
- 📁 **Self-contained** in a single `toy_dataset/` folder
- ⚡ **Fast pipeline runs** for rapid testing and development

---

## Quick Start

### Prerequisites

- Python 3.10+
- Required packages: `pandas`, `numpy`
- Located in the project root directory

### Running the Script

```bash
cd /path/to/polygenie-pipeline
python scripts/create_toy_dataset.py
```

### Output

The script creates the following structure:

```
toy_dataset/
├── config/
│   └── pipeline_config.yaml          # Pre-configured for toy dataset
├── data/
│   ├── covars.tsv                    # 500 individuals, shuffled covariates
│   ├── prs_metadata.csv              # 10 selected PRS metadata
│   ├── phenotype_metadata.csv        # All phenotypes (unchanged)
│   ├── prs/                          # 10 PRS profile files (shuffled)
│   │   ├── asthma.profiles
│   │   ├── t2d.profiles
│   │   └── ... (8 more PRS)
│   └── phenotypes/                   # All phenotype files (shuffled)
│       ├── icd_codes.csv
│       ├── metabolites.csv
│       ├── phecodes.csv
│       └── questionnaire.csv
└── README.md                         # Usage instructions

```

---

## Detailed Description

### What Gets Created

#### 1. **Covariates File** (`toy_dataset/data/covars.tsv`)

Original covariates are subset to 500 random individuals and shuffled to anonymize:

| Column | Type | Description |
|--------|------|-------------|
| `IID` | string | Individual identifier (ind_1 to ind_500) |
| `PC1-PC10` | float | Principal components (shuffled) |
| `age` | int | Age in years (shuffled) |
| `sex` | string | Biological sex (shuffled) |
| Other covariates | various | All shuffled independently |

**Key Point:** Each column is shuffled *independently*, so correlations between variables are destroyed, breaking real associations.

#### 2. **PRS Files** (`toy_dataset/data/prs/`)

10 randomly selected PRS profiles, each containing:

| Column | Type | Description |
|--------|------|-------------|
| `ID` | string | Individual identifier (ind_1 to ind_500) |
| `PRS` | float | Polygenic Risk Score (shuffled) |

**Example PRS names** (varies per run due to random selection):
- `asthma.profiles`
- `t2d.profiles` (Type 2 Diabetes)
- `copd.profiles`
- `ad.profiles` (Alzheimer's Disease)
- etc.

#### 3. **Phenotype Files** (`toy_dataset/data/phenotypes/`)

Four phenotype files, each with 500 individuals and shuffled values:

##### `icd_codes.csv`
- ICD-10 diagnostic codes (binary: 0/1)
- Columns: ID + ~1000 ICD codes
- Suitable for testing binary phenotype regression

##### `metabolites.csv`
- Metabolomic measurements (continuous values)
- Columns: ID + ~190 metabolite concentrations
- Suitable for testing continuous phenotype associations

##### `phecodes.csv`
- PheCode disease classifications (binary: 0/1)
- Columns: ID + ~600 phecodes
- Hierarchical disease coding system

##### `questionnaire.csv`
- Questionnaire-derived traits (mixed continuous/binary)
- Columns: ID + ~80 phenotypes
- Includes anthropometric measurements, lifestyle factors, health status

#### 4. **Metadata Files**

##### `prs_metadata.csv`
Mapping of PRS names to profile files:

```csv
name,path,label,sex
asthma,data/prs/asthma.profiles,Asthma,both
t2d,data/prs/t2d.profiles,Type 2 Diabetes,both
...
```

##### `phenotype_metadata.csv`
Mapping of phenotype variables to files and types:

```csv
Variable;Description;Class;ClassFile;Domain;Type;Sex;Covariates
BMI;Body Mass Index;Questionnaire;data/phenotypes/questionnaire.csv;Measurements;continuous;both;sex
...
```

#### 5. **Configuration File** (`toy_dataset/config/pipeline_config.yaml`)

Pre-configured for optimal toy dataset performance:

```yaml
paths:
  phenotype_metadata: "data/phenotype_metadata.csv"
  prs_metadata: "data/prs_metadata.csv"
  covariates: "data/covars.tsv"
  output_dir: "results/"

analysis:
  min_cases: 10  # Lower threshold for small dataset
  
regression_runs:
  - groups: 10        # Deciles
  - groups: 4         # Quartiles
```

---

## Running the Pipeline with Toy Data

### From the toy_dataset directory:

```bash
cd toy_dataset
nextflow run ../main.nf -c config/pipeline_config.yaml
```

### From the project root:

```bash
nextflow run main.nf -c toy_dataset/config/pipeline_config.yaml
```

### With additional parameters:

```bash
nextflow run main.nf \
  -c toy_dataset/config/pipeline_config.yaml \
  -resume \
  -with-timeline timeline.html \
  -with-trace trace.txt
```

---

## Data Flow & Anonymization Strategy

```
Original Data (4990+ individuals, 137 PRS, 1000s phenotypes)
    ↓
    ├─→ Random Selection (500 individuals)
    ├─→ Random Selection (10 PRS)
    │
    ↓ (Per column, independently)
Independent Shuffling (np.random.permutation)
    │
    ├─→ Breaks associations with ID
    ├─→ Breaks sex/age structure
    ├─→ Breaks PRS-phenotype associations
    ├─→ Preserves marginal distributions
    │
    ↓
Toy Dataset (500 anonymized individuals: ind_1 to ind_500)
    ├─→ No real genetic associations
    ├─→ Safe for development/testing
    ├─→ Suitable for method validation
```

### Why This Works

1. **Reproducibility**: Fixed random seed (42) ensures same toy dataset each run
2. **Anonymization**: IDs replaced with sequential numbers; all associations destroyed
3. **Statistical Validity**: Marginal distributions preserved for testing methodology
4. **Computational Efficiency**: 10× smaller dataset = 10× faster pipeline runs
5. **No Data Leakage**: Cannot recover real associations or individual identities

---

## Use Cases

### ✅ Suitable For:

- Pipeline infrastructure testing (parsing, I/O, execution)
- Regression and statistical method validation
- PheWAS visualization and web app testing
- Database schema validation
- Documentation and training
- CI/CD pipeline validation
- Performance profiling and optimization

### ❌ NOT Suitable For:

- Scientific analysis or publication
- Benchmarking against real associations
- Demonstrating disease associations
- Any use requiring real genetic relationships

---

## Technical Details

### Shuffling Method

Each variable column is independently shuffled using:

```python
import numpy as np
np.random.seed(42)  # Reproducible
shuffled_values = np.random.permutation(column_values)
```

**Effect:**
- Original value distributions are preserved
- Correlations with other columns are destroyed
- Individual identities are obscured
- Statistical tests should still work (with random null results)

### Metadata Consistency

The script ensures:
- All individual IDs match across files (covars ↔ PRS ↔ phenotypes)
- File paths in metadata are correct
- Phenotype variable names remain unchanged
- PRS metadata reflects only selected PRS

---

## Output Size & Performance

| Metric | Toy Dataset | Full Dataset | Ratio |
|--------|-----------|--------------|-------|
| Individuals | 500 | 4,990 | 0.1× |
| PRS | 10 | 137 | 0.07× |
| Covariates | Same columns | Same columns | 1× |
| Phenotypes | Same columns | Same columns | 1× |
| Total size | ~100 MB | ~1-2 GB | 0.05-0.1× |
| Pipeline run time | 10-30 min | 2-4 hours | 0.05-0.25× |

---

## Troubleshooting

### Issue: "Module not found: pandas"

**Solution:**
```bash
pip install pandas numpy
```

### Issue: "File not found" errors

**Solution:** Ensure you're running the script from the project root:
```bash
cd /path/to/polygenie-pipeline
python scripts/create_toy_dataset.py
```

### Issue: Script exits without creating toy_dataset/

**Solution:** Check console output for specific errors. Common causes:
- Missing original data files in `data/` directory
- Insufficient disk space
- Permission errors in current directory

### Issue: Phenotypes missing after creation

**Solution:** Check that all phenotype files exist in `data/phenotypes/`:
```bash
ls data/phenotypes/*.csv
```

---

## Examples

### Example 1: Create toy dataset and run full pipeline

```bash
# Create toy dataset
python scripts/create_toy_dataset.py

# Run pipeline
cd toy_dataset
nextflow run ../main.nf -c config/pipeline_config.yaml

# Results will be in toy_dataset/results/
```

### Example 2: Testing a new analysis module

```bash
# Quick test on small data
python scripts/create_toy_dataset.py

# Run just preprocessing
cd toy_dataset
nextflow run ../main.nf \
  -c config/pipeline_config.yaml \
  -entry preprocessing
```

### Example 3: Web app testing

```bash
# Create toy dataset
python scripts/create_toy_dataset.py

# Run pipeline
cd toy_dataset
nextflow run ../main.nf -c config/pipeline_config.yaml

# Build database with toy results
python ../scripts/db/ingest.py --results-dir results --db-path polygenie.db

# Launch app
cd ..
python app/app.py
# Visit http://localhost:8050 - now with toy data!
```

---

## Reproducibility

The toy dataset creation uses fixed random seeds:

```python
random.seed(42)
np.random.seed(42)
```

This means:
- Running the script multiple times produces identical datasets
- The same 10 PRS are always selected
- The same 500 individuals are always selected
- All shuffled values are identical

To create a different toy dataset with different random selections:
- Modify the seed values in the script before running

---

## Advanced Customization

To create multiple toy datasets or modify parameters, edit [scripts/create_toy_dataset.py](scripts/create_toy_dataset.py):

```python
# Change number of individuals
n_individuals = 500  # ← Modify this

# Change number of PRS
n_prs = 10  # ← Modify this

# Change random seed for different results
random.seed(42)  # ← Modify this
np.random.seed(42)  # ← Modify this
```

---

## File Specifications

### TSV Format (Covariates)

```
IID	PC1	PC2	...	age	sex
ind_1	0.002	-0.023	...	52	female
ind_2	0.005	0.001	...	46	female
```

### CSV Format (PRS, Phenotypes)

```
ID;value1;value2;...
ind_1;0;1;...
ind_2;1;0;...
```

Note: Different files use different delimiters (TSV vs semicolon-separated CSV).

---

## References

- [Main README](README.md) - General project documentation
- [Pipeline Configuration](config/pipeline_config.yaml) - Analysis parameters
- [Data Schema](db/schema.sql) - Database structure
- [Input Data Guide](README.md#input-data) - Original data format

---

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section above
2. Review console output during script execution
3. Verify input data files exist and are readable
4. Check file permissions and disk space

---

## License

Same as the PolyGenie project. See [LICENSE](../LICENSE) for details.

