# Toy Dataset - Quick Reference

## What is it?

An anonymized, self-contained dataset for testing the PolyGenie pipeline:
- **500 anonymized individuals** (`ind_1` to `ind_500`)
- **10 PRS profiles** (randomly selected)
- **All phenotypes/covariates shuffled** (breaks real associations, preserves distributions)
- **Self-contained** in `toy_dataset/` folder

## Why use it?

✅ **Testing**: Validate pipeline infrastructure quickly  
✅ **Development**: Rapid iteration without full dataset  
✅ **Training**: Demonstrate workflow without sensitive data  
✅ **CI/CD**: Fast automated testing  
✅ **Documentation**: Safe examples for users  

❌ **Not suitable for**: Scientific analysis, publication, benchmarking real associations

## How to create it?

```bash
python scripts/create_toy_dataset.py
```

**Output:** `toy_dataset/` directory (self-contained)

## What gets created?

```
toy_dataset/
├── config/
│   └── pipeline_config.yaml           ← Use this to run pipeline
├── data/
│   ├── covars.tsv                     500 anonymized individuals
│   ├── prs_metadata.csv               10 selected PRS
│   ├── phenotype_metadata.csv         All phenotypes
│   ├── prs/                           10 .profiles files
│   └── phenotypes/                    Shuffled phenotype data
└── README.md                          Usage instructions
```

## How to run the pipeline?

```bash
cd toy_dataset
nextflow run ../main.nf -c config/pipeline_config.yaml
```

Results go to `toy_dataset/results/`

## Data Characteristics

| Aspect | Value |
|--------|-------|
| Individuals | 500 (anon: ind_1 to ind_500) |
| PRS | 10 (randomly selected) |
| Total size | ~100-200 MB |
| Run time | 10-30 minutes |
| Associations | All broken (randomized) |

## Key Files

| File | Purpose |
|------|---------|
| `DATASET_CREATION.md` | Full documentation (detailed) |
| `README.md` | Main project README (updated with toy dataset info) |
| `scripts/create_toy_dataset.py` | Script to generate toy dataset |

## Example Workflow

```bash
# 1. Create toy dataset
python scripts/create_toy_dataset.py

# 2. Run pipeline
cd toy_dataset
nextflow run ../main.nf -c config/pipeline_config.yaml

# 3. Build database with results
cd ..
python scripts/db/ingest.py --results-dir toy_dataset/results --db polygenie_toy.db

# 4. Launch web app with toy data
POLYGENIE_DB=polygenie_toy.db python app/app.py
# Visit http://localhost:8050
```

## Anonymization Details

All variables are shuffled **independently**:
- Breaks correlations with IDs
- Breaks sex/age structure  
- Breaks PRS-phenotype associations
- Destroys individual identities
- **Preserves** marginal distributions (for statistical testing)

**Result:** Can develop/test code with realistic data structure, but zero risk of exposing real associations or identities.

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "Module not found: pandas" | `pip install pandas numpy` |
| Script runs but doesn't create folder | Check console for errors; ensure you're in project root |
| Missing phenotypes | Verify `data/phenotypes/*.csv` files exist |
| Pipeline fails on toy data | Check `toy_dataset/config/pipeline_config.yaml` paths |

## Next Steps

1. **Full Documentation**: Read [DATASET_CREATION.md](DATASET_CREATION.md)
2. **Create Dataset**: `python scripts/create_toy_dataset.py`
3. **Run Pipeline**: `cd toy_dataset && nextflow run ../main.nf -c config/pipeline_config.yaml`
4. **Explore Results**: Check `toy_dataset/results/` and launch the web app
5. **Customize**: Modify `scripts/create_toy_dataset.py` to change # of individuals/PRS

---

**Status**: ✨ Ready to use!
