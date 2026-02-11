# 🚀 START HERE

Welcome to **PolyGenie** - a tool for polygenic risk score (PRS) analysis, PheWAS, and visualization!

This document helps you navigate the documentation and get started with the pipeline.

---

## 🎯 Choose Your Path

### Path 1: I Want to Try It Quickly ⚡ (30 minutes)

You want to see the pipeline in action without setting up your own data.

**Steps:**
1. Read: [TOY_DATASET_QUICK_REFERENCE.md](TOY_DATASET_QUICK_REFERENCE.md) (2 min)
2. Create toy dataset: `python scripts/create_toy_dataset.py` (1 min)
3. Run pipeline: `cd toy_dataset && nextflow run ../main.nf -c config/pipeline_config.yaml` (15-30 min)
4. Explore results in `toy_dataset/results/`

**Next:** After running toy data, explore [main README](README.md) to understand what you ran.

---

### Path 2: I Have My Own Data 📊 (2-4 hours)

You have your own data and want to run the pipeline on it.

**Steps:**
1. Read: [DATA_FORMATTING_AND_CONFIG.md](DATA_FORMATTING_AND_CONFIG.md) (20-30 min)
   - Learn how to format your covariates, PRS files, and phenotypes
   - Review examples and specifications
   - Prepare your data files

2. Create your configuration file (15-30 min)
   - Use examples from the guide
   - Copy from toy dataset and customize

3. Run file checklist (5-10 min)
   - Validate all files before running
   - Check format compliance

4. Run pipeline: `nextflow run main.nf -c config/your_config.yaml` (2-4 hours)

5. Explore results and build database

**Related:** 
- [DATA_FORMATTING_AND_CONFIG.md](DATA_FORMATTING_AND_CONFIG.md) - Full data format guide
- [README.md](README.md) - Main project overview
- [Troubleshooting in DATA_FORMATTING_AND_CONFIG.md](DATA_FORMATTING_AND_CONFIG.md#troubleshooting)

---

### Path 3: I'm Learning About Anonymization 🔐 (1-2 hours)

You want to understand the toy dataset creation, anonymization strategy, and technical details.

**Steps:**
1. Read: [TOY_DATASET_QUICK_REFERENCE.md](TOY_DATASET_QUICK_REFERENCE.md) (3 min)
2. Read: [DATASET_CREATION.md](DATASET_CREATION.md) (15-20 min)
   - Overview and quick start
   - Detailed output descriptions
   - Data flow and anonymization strategy
   - Technical implementation details
   - Use cases and examples

3. Optional: Review [create_toy_dataset.py](scripts/create_toy_dataset.py) script
   - Understand the code
   - Customize for your needs

**Related:**
- [Data Flow diagram](DATASET_CREATION.md#data-flow--anonymization-strategy) in DATASET_CREATION.md
- [Shuffling Method](DATASET_CREATION.md#technical-details) in DATASET_CREATION.md

---

### Path 4: I'm a Developer/Advanced User 🔧 (4+ hours)

You want to understand the complete system, modify code, or extend functionality.

**Steps:**
1. Start with [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) (10 min)
   - Overview of all documentation
   - Navigation guide

2. Read [README.md](README.md) (15 min)
   - Project overview and features
   - Installation and setup

3. Read [DATA_FORMATTING_AND_CONFIG.md](DATA_FORMATTING_AND_CONFIG.md) (30 min)
   - Understand data structures
   - Configuration system

4. Read [DATASET_CREATION.md](DATASET_CREATION.md) (20 min)
   - Technical implementation
   - Anonymization strategy

5. Review source code:
   - [main.nf](main.nf) - Nextflow workflow
   - [scripts/](scripts/) - Analysis scripts
   - [app/app.py](app/app.py) - Web application

6. Explore [db/schema.sql](db/schema.sql) (10 min)
   - Database structure
   - Output format

**Related:**
- [DATASET_CREATION.md - Advanced Customization](DATASET_CREATION.md#advanced-customization)
- [db/schema.sql](db/schema.sql) - Database schema
- [main.nf](main.nf) - Workflow logic

---

### Path 5: I Want to Deploy/Use the Web App 🌐 (1-2 hours)

You want to run the web application to explore results.

**Steps:**
1. Create toy dataset or prepare your data (see Path 1 or 2)
2. Run pipeline to generate results
3. Read [README.md - Launching the App](README.md#launching-the-app) section
4. Build SQLite database from results
5. Launch Dash app
6. Explore via web interface at http://localhost:8050

**Related:**
- [README.md - Launching the App](README.md#launching-the-app)
- [app/app.py](app/app.py) - Web app source code

---

### Path 6: I'm Writing Documentation/Teaching 📚 (30 min)

You want to create examples or teach others how to use PolyGenie.

**Steps:**
1. Read [TOY_DATASET_QUICK_REFERENCE.md](TOY_DATASET_QUICK_REFERENCE.md) (2 min)
2. Create toy dataset (1 min)
3. Use as basis for your documentation
4. Reference [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) for comprehensive examples
5. Link users to appropriate guides based on their needs

**Related:**
- [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) - Complete documentation overview
- [DATA_FORMATTING_AND_CONFIG.md - Examples](DATA_FORMATTING_AND_CONFIG.md#examples) - Multiple worked examples

---

## 📚 Documentation Map

```
README.md (main project page)
├─ Installation
├─ Features
├─ Folder Structure
└─ Links to all resources

START_HERE.md (this file!)
├─ Path 1: Try it quickly → TOY_DATASET_QUICK_REFERENCE.md
├─ Path 2: Use your data → DATA_FORMATTING_AND_CONFIG.md
├─ Path 3: Learn anonymization → DATASET_CREATION.md
├─ Path 4: Developer guide → DOCUMENTATION_INDEX.md
├─ Path 5: Web app → README.md + app code
└─ Path 6: Teaching → All docs + examples

DOCUMENTATION_INDEX.md (navigation hub)
├─ All guides overview
├─ Quick start workflows
├─ FAQ
└─ Reference tables

TOY_DATASET_QUICK_REFERENCE.md (quick lookup)
├─ Quick overview
├─ Essential commands
└─ Common issues

DATASET_CREATION.md (complete technical guide)
├─ How to create toy dataset
├─ Anonymization strategy
├─ Advanced customization
└─ Examples

DATA_FORMATTING_AND_CONFIG.md (how to format your data)
├─ File format specifications
├─ Metadata file examples
├─ Configuration parameters
├─ Complete worked examples
└─ Troubleshooting
```

---

## 🔗 Quick Links

| I want to... | Read this | Time |
|-------------|-----------|------|
| Try it now | [TOY_DATASET_QUICK_REFERENCE.md](TOY_DATASET_QUICK_REFERENCE.md) | 30 min |
| Use my data | [DATA_FORMATTING_AND_CONFIG.md](DATA_FORMATTING_AND_CONFIG.md) | 2-4 hours |
| Understand anonymization | [DATASET_CREATION.md](DATASET_CREATION.md) | 1-2 hours |
| See everything | [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) | 30 min |
| Learn about the project | [README.md](README.md) | 15 min |
| Develop/extend | [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) + source code | 4+ hours |

---

## ⚡ Quick Start Commands

### Fastest Way to Get Running (30 minutes)

```bash
# 1. Create toy dataset
python scripts/create_toy_dataset.py

# 2. Run pipeline
cd toy_dataset
nextflow run ../main.nf -c config/pipeline_config.yaml

# 3. Results are in toy_dataset/results/
```

### Use Your Own Data (2-4 hours)

```bash
# 1. Prepare your data following DATA_FORMATTING_AND_CONFIG.md
# 2. Create config file
# 3. Run pipeline
nextflow run main.nf -c config/your_config.yaml
```

### View Results in Web App

```bash
# After pipeline completes and database is built
python app/app.py
# Visit http://localhost:8050
```

---

## ❓ FAQ

### Q: Where do I start?
**A:** Choose your path above based on what you want to do. Most users start with [Path 1](#path-1-i-want-to-try-it-quickly--30-minutes) or [Path 2](#path-2-i-have-my-own-data--2-4-hours).

### Q: What's the fastest way to see the pipeline work?
**A:** Follow [Path 1](#path-1-i-want-to-try-it-quickly--30-minutes). Takes ~30 minutes total.

### Q: How do I format my data?
**A:** Read [DATA_FORMATTING_AND_CONFIG.md](DATA_FORMATTING_AND_CONFIG.md). It has format specifications and multiple examples.

### Q: What if something goes wrong?
**A:** Check the [Troubleshooting sections](DATA_FORMATTING_AND_CONFIG.md#troubleshooting) in the relevant guide.

### Q: Can I see example data?
**A:** Yes! Use `python scripts/create_toy_dataset.py` to create the toy dataset, then check `toy_dataset/data/`.

### Q: What if I want to understand the technical details?
**A:** Read [DATASET_CREATION.md](DATASET_CREATION.md) for anonymization/technical details, or [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) for complete overview.

### Q: Where's the main README?
**A:** Here: [README.md](README.md)

---

## 🎯 Success Criteria

You'll know you're on the right track when:

- ✅ You've read the documentation for your path
- ✅ You understand the file formats (if using your own data)
- ✅ Your files pass the validation checklist
- ✅ The pipeline runs without errors
- ✅ You have results in the output directory

---

## 📞 Getting Help

1. **For data formatting issues:** Read [DATA_FORMATTING_AND_CONFIG.md - Troubleshooting](DATA_FORMATTING_AND_CONFIG.md#troubleshooting)

2. **For pipeline execution issues:** Check [README.md](README.md) and relevant documentation

3. **For technical questions:** See [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) for comprehensive reference

4. **For anonymization questions:** Read [DATASET_CREATION.md](DATASET_CREATION.md)

---

## 🗺️ Navigation Cheat Sheet

- **Main Project Page:** [README.md](README.md)
- **All Documentation:** [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)
- **Quick Lookup:** [TOY_DATASET_QUICK_REFERENCE.md](TOY_DATASET_QUICK_REFERENCE.md)
- **Your Data:** [DATA_FORMATTING_AND_CONFIG.md](DATA_FORMATTING_AND_CONFIG.md)
- **Toy Dataset:** [DATASET_CREATION.md](DATASET_CREATION.md)
- **You Are Here:** [START_HERE.md](START_HERE.md) ← 👈

---

## 🚀 Ready to Start?

Pick your path above and let's get started!

- 🏃 **Quick Try:** → [Path 1](#path-1-i-want-to-try-it-quickly--30-minutes)
- 📊 **My Data:** → [Path 2](#path-2-i-have-my-own-data--2-4-hours)
- 🔐 **Learn Details:** → [Path 3](#path-3-im-learning-about-anonymization--1-2-hours)
- 🔧 **Developer:** → [Path 4](#path-4-im-a-developeradvanced-user--4-hours)
- 🌐 **Web App:** → [Path 5](#path-5-i-want-to-deployuse-the-web-app--1-2-hours)
- 📚 **Teaching:** → [Path 6](#path-6-im-writing-documentationteaching--30-min)

---

**Questions?** Check [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) for the complete overview and FAQ section.

