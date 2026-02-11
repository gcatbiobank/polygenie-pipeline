# Documentation Index

## 📚 Toy Dataset & Pipeline Documentation

### 🎯 Main Entry Point

**[START_HERE.md](START_HERE.md)** ← **Start with this file!**
- 6 learning paths based on your needs
- Quick links and navigation
- FAQ and success criteria
- Estimated time for each path

### Quick Start Guides

1. **[TOY_DATASET_QUICK_REFERENCE.md](TOY_DATASET_QUICK_REFERENCE.md)** ⚡
   - Quick overview (2-3 min read)
   - Basic commands and examples
   - Common issues & solutions
   - Start here if you're in a hurry!

2. **[DATASET_CREATION.md](DATASET_CREATION.md)** 📖
   - Comprehensive guide (15-20 min read)
   - Detailed input/output specifications
   - Data flow and anonymization strategy
   - Advanced customization
   - Use cases and performance metrics
   - Troubleshooting & support

3. **[DATA_FORMATTING_AND_CONFIG.md](DATA_FORMATTING_AND_CONFIG.md)** 📋
   - How to format your data (20-30 min read)
   - Covariates, PRS, and phenotype file specifications
   - Metadata file formats with examples
   - Configuration file parameters and examples
   - File checklist and directory structure
   - Best practices and troubleshooting

4. **[README.md](README.md)** 🎯
   - Main project documentation
   - Installation, features, usage
   - Updated with toy dataset section
   - Links to all other documentation

---

## 🔧 Implementation Files

### Python Script

**[scripts/create_toy_dataset.py](scripts/create_toy_dataset.py)**
- Creates anonymized toy dataset (500 individuals, 10 PRS)
- Shuffles all variables independently
- Generates self-contained `toy_dataset/` folder
- Run with: `python scripts/create_toy_dataset.py`

### Generated Output

**Directory:** `toy_dataset/`
```
toy_dataset/
├── config/pipeline_config.yaml     (Pre-configured)
├── data/
│   ├── covars.tsv                  (500 anonymized individuals)
│   ├── prs_metadata.csv            (10 PRS)
│   ├── phenotype_metadata.csv      (all phenotypes)
│   ├── prs/                        (shuffled PRS profiles)
│   └── phenotypes/                 (shuffled phenotypes)
└── README.md                       (Usage in toy_dataset)
```

---

## 📊 Documentation Overview

### Document Content

| Document | Purpose | Audience | Length |
|----------|---------|----------|--------|
| **TOY_DATASET_QUICK_REFERENCE.md** | Quick overview, commands, examples | Everyone | 2-3 min |
| **DATASET_CREATION.md** | Complete technical documentation | Developers, advanced users | 15-20 min |
| **DATA_FORMATTING_AND_CONFIG.md** | Data and config formatting guide | Users preparing their data | 20-30 min |
| **README.md** | Project overview, general usage | All users | 10-15 min |

### Key Topics Covered

#### In TOY_DATASET_QUICK_REFERENCE.md
- ✅ What and why?
- ✅ How to create it?
- ✅ What gets created?
- ✅ How to run the pipeline?
- ✅ Data characteristics
- ✅ Common issues & solutions

#### In DATASET_CREATION.md
- ✅ Overview and quick start
- ✅ Detailed file descriptions
- ✅ Data flow and anonymization strategy
- ✅ Use cases (suitable/unsuitable)
- ✅ Technical implementation details
- ✅ Output size and performance
- ✅ Troubleshooting
- ✅ Examples and workflows
- ✅ Reproducibility notes
- ✅ Advanced customization
- ✅ File specifications
- ✅ References and support

#### In DATA_FORMATTING_AND_CONFIG.md
- ✅ Covariates file format and requirements
- ✅ PRS file format and organization
- ✅ Phenotype file formats (continuous, binary, mixed)
- ✅ Metadata file specifications with examples
- ✅ Configuration file parameters and examples
- ✅ File checklist and validation
- ✅ Directory structure recommendations
- ✅ Complete worked examples
- ✅ Best practices
- ✅ Troubleshooting common issues

---

## 🚀 Quick Start Workflow

### For First-Time Users

1. **Read**: [TOY_DATASET_QUICK_REFERENCE.md](TOY_DATASET_QUICK_REFERENCE.md) (2 min)
2. **Create**: `python scripts/create_toy_dataset.py` (1 min)
3. **Run**: `cd toy_dataset && nextflow run ../main.nf -c config/pipeline_config.yaml` (15-30 min)
4. **Explore**: Check results in `toy_dataset/results/`

### For Developers

1. **Read**: [DATASET_CREATION.md](DATASET_CREATION.md) (full doc)
2. **Understand**: Data flow and anonymization strategy
3. **Customize**: Modify [scripts/create_toy_dataset.py](scripts/create_toy_dataset.py) as needed
4. **Extend**: Use toy dataset in tests, CI/CD, examples

### For Documentation/Training

1. **Use**: Pre-created toy dataset for examples
2. **Point to**: [TOY_DATASET_QUICK_REFERENCE.md](TOY_DATASET_QUICK_REFERENCE.md) for quick intro
3. **Reference**: [DATASET_CREATION.md](DATASET_CREATION.md) for technical details
4. **Show**: Example workflows from the documentation

---

## 🎯 Use Cases

### Rapid Testing
```bash
python scripts/create_toy_dataset.py
cd toy_dataset
nextflow run ../main.nf -c config/pipeline_config.yaml
```
Expected time: ~30 minutes

### Infrastructure Validation
```bash
python scripts/create_toy_dataset.py
cd toy_dataset
nextflow run ../main.nf -c config/pipeline_config.yaml -resume
# Test reproducibility, parallelization, error handling
```

### Web App Demo
```bash
python scripts/create_toy_dataset.py
cd toy_dataset
nextflow run ../main.nf -c config/pipeline_config.yaml
cd ..
python scripts/db/ingest.py --results-dir toy_dataset/results --db demo.db
POLYGENIE_DB=demo.db python app/app.py
# Visit http://localhost:8050
```

### Method Validation
```bash
# Use toy dataset with your new analysis method
python scripts/create_toy_dataset.py
# Add your code to scripts/
cd toy_dataset
nextflow run ../main.nf -c config/pipeline_config.yaml
# Validate with known distributions (null results expected)
```

---

## 📋 Reference Table

### File Formats

| File | Format | Delimiter | Example |
|------|--------|-----------|---------|
| `covars.tsv` | TSV | Tab | `ind_1	0.002	-0.023	...	52	female` |
| `.profiles` | TSV | Tab | `ind_1	0.823` |
| `*_metadata.csv` | CSV | Semicolon | `name;path;label;sex` |
| `icd_codes.csv` | CSV | Semicolon | `ID;A01;A02;...` |
| `metabolites.csv` | CSV | Semicolon | `ID;Glucose;Cholesterol;...` |
| `phecodes.csv` | CSV | Semicolon | `ID;10;1000;...` |
| `questionnaire.csv` | CSV | Semicolon | `ID;height;weight;...` |

### Data Characteristics

| Aspect | Full Dataset | Toy Dataset |
|--------|-------------|------------|
| Individuals | 4,990 | 500 |
| PRS | 137 | 10 |
| Phenotypes | 1000+ | 1000+ |
| Covariates | 13 | 13 |
| Size | 1-2 GB | 100-200 MB |
| Run time | 2-4 hours | 15-30 min |

---

## ❓ FAQ

### Q: Is the toy dataset real data?
**A:** No, it's anonymized with shuffled values. Individual identities are obscured and all associations are randomized.

### Q: Can I use it for research?
**A:** No, it's only suitable for testing, development, and training. All real associations are destroyed.

### Q: How long does it take to create?
**A:** 1-5 minutes on most systems, depending on I/O speed.

### Q: Can I customize it?
**A:** Yes! Edit [scripts/create_toy_dataset.py](scripts/create_toy_dataset.py) to change number of individuals, PRS, random seed, etc.

### Q: Will I get the same dataset each time?
**A:** Yes, the random seed is fixed (42), ensuring reproducibility.

### Q: Where do I get detailed technical info?
**A:** See [DATASET_CREATION.md](DATASET_CREATION.md) for complete technical documentation.

---

## 🔗 Cross-References

### From README.md
- [START_HERE.md](START_HERE.md) - Main entry point (new!)
- [Demo / Toy Dataset section](README.md#demo--toy-dataset)
- [Creating a Toy Dataset section](README.md#creating-a-toy-dataset)
- [Installation section](README.md#installation)
- [Pipeline Usage section](README.md#pipeline-usage)

### From START_HERE.md (new!)
- [Path 1: Try it quickly](START_HERE.md#path-1-i-want-to-try-it-quickly--30-minutes)
- [Path 2: Use your data](START_HERE.md#path-2-i-have-my-own-data--2-4-hours)
- [Path 3: Learn anonymization](START_HERE.md#path-3-im-learning-about-anonymization--1-2-hours)
- [Path 4: Developer guide](START_HERE.md#path-4-im-a-developeradvanced-user--4-hours)
- [Path 5: Web app deployment](START_HERE.md#path-5-i-want-to-deployuse-the-web-app--1-2-hours)
- [Path 6: Teaching/documentation](START_HERE.md#path-6-im-writing-documentationteaching--30-min)
- [FAQ section](START_HERE.md#-faq)

### From DATASET_CREATION.md
- Quick Start section
- Data Flow & Anonymization Strategy section
- Use Cases section
- Examples section
- Troubleshooting section

### From TOY_DATASET_QUICK_REFERENCE.md
- What is it? section
- How to create it? section
- Example Workflow section

---

## 📞 Support

### Common Issues

**"Module not found: pandas"**
```bash
pip install pandas numpy
```

**"File not found" errors**
```bash
# Ensure you're in project root
cd /path/to/polygenie-pipeline
python scripts/create_toy_dataset.py
```

**Script runs but doesn't create folder**
- Check console output for errors
- Verify `data/` directory exists and has required files
- Check disk space and write permissions

### Getting Help

1. Check the [Troubleshooting section](DATASET_CREATION.md#troubleshooting) in DATASET_CREATION.md
2. Review console output during execution
3. Verify input data files and permissions
4. Check [Common Issues](TOY_DATASET_QUICK_REFERENCE.md#common-issues--solutions) in Quick Reference

---

## 📝 Documentation Status

| Document | Status | Last Updated | Size |
|----------|--------|--------------|------|
| TOY_DATASET_QUICK_REFERENCE.md | ✅ Complete | Feb 10, 2026 | 3.7 KB |
| DATASET_CREATION.md | ✅ Complete | Feb 10, 2026 | 11 KB |
| README.md | ✅ Updated | Feb 10, 2026 | 8.8 KB |
| scripts/create_toy_dataset.py | ✅ Complete | Feb 10, 2026 | 11 KB |
| DOCUMENTATION_INDEX.md | ✅ This file | Feb 10, 2026 | - |

---

**Last Updated**: February 10, 2026  
**Version**: 1.0  
**Status**: 🎉 Ready to use!

