# polygenie-pipeline

## Running on SGE Clusters

This pipeline supports parallel execution on Sun Grid Engine (SGE) clusters using Nextflow's SGE executor. To enable SGE support:

1. **Configure SGE parameters in `config/pipeline_config.yaml`:**

	```yaml
	sge:
	  queue: "all.q"            # SGE queue name (e.g., all.q, short.q)
	  parallel_env: "smp"       # SGE parallel environment name (e.g., smp, threaded)
	  walltime: "04:00:00"      # Default walltime (hh:mm:ss)
	```

2. **Launch the pipeline with the SGE profile:**

	```bash
	nextflow run main.nf -profile sge -resume
	```

	You can override SGE parameters at runtime:

	```bash
	nextflow run main.nf -profile sge --sge.queue short.q --sge.parallel_env threaded --sge.walltime 02:00:00
	```

3. **Resource mapping:**
	- Each process requests CPUs according to its `cpus` directive (see `modules/2-analysis.nf`).
	- The SGE parallel environment must exist and support the requested slot count.
	- The queue should allow jobs with the requested resources.

4. **Tuning tips:**
	- Adjust `cpus` in process definitions for more/less parallelism per job.
	- Set `maxForks` in `nextflow.config` for local runs; SGE handles concurrency automatically.
	- For large runs, ensure your SGE user/job limits and parallel environment are configured for high throughput.

5. **Example SGE config section:**
	See `config/pipeline_config.yaml` for the recommended SGE parameter block.

## Troubleshooting SGE Runs

## Running on GPU SGE Servers

This pipeline can be executed on GPU-enabled SGE clusters using the `gpu` profile. To request GPU resources:

1. **Configure GPU parameters in `config/pipeline_config.yaml`:**

	```yaml
	gpu:
	  queue: "gpu.q"            # SGE GPU queue name
	  parallel_env: "smp"       # SGE parallel environment name
	  walltime: "04:00:00"      # Default walltime (hh:mm:ss)
	  gpu: 1                    # Number of GPUs to request per job
	```

2. **Launch the pipeline with the GPU profile:**

	```bash
	nextflow run main.nf -profile gpu -resume
	```

	You can override GPU parameters at runtime:

	```bash
	nextflow run main.nf -profile gpu --gpu.gpu 2 --gpu.queue gpu.q
	```

3. **How many GPUs should you select?**
	- For most jobs, set `gpu: 1` unless your code is optimized for multi-GPU.
	- Increase only if your scripts/libraries (e.g., TensorFlow, PyTorch) can use multiple GPUs efficiently.
	- If unsure, start with 1 GPU and scale up as needed.

4. **Requirements:**
	- Your conda environment or container must include GPU-enabled libraries.
	- Your scripts must detect and use the GPU if available.

5. **Example GPU config section:**
	See `config/pipeline_config.yaml` for the recommended GPU parameter block.

- If jobs stay pending, check queue and parallel environment settings.
- If jobs fail with resource errors, reduce `cpus` or request a different queue/PE.
- For more details, see Nextflow's [SGE executor documentation](https://www.nextflow.io/docs/latest/executor.html#sge).

## General Usage

## Flexible Percentile and Regression Runs

You can configure percentile plots and regression analyses independently using the config file:

### Example: `config/pipeline_config.yaml`

```yaml
percentile_plot:
	groups: 10           # e.g. 10 for deciles
	normalize: true      # whether to normalize PRS for plots

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
```

### How it works
- **Percentile plots**: The pipeline uses the `percentile_plot` block for `COMPUTE_PRS_PERCENTILES` jobs.
- **Regressions**: The pipeline iterates over each entry in `regression_runs` and runs a separate regression for each PRS and parameter set.
	- Output files are labeled with the `label` field for clarity.

### Customizing your analysis
- Add or remove entries in `regression_runs` to control which percentiles, grouping, and intermediate options are used for regressions.
- You can run quartiles, deciles, or any other grouping by changing the `groups` value.
- Set `include_intermediates` to `true` or `false` for each run.

### Example output files
- Percentile plots: `results/percentiles/<PRS>_percentiles.csv`
- Regression results: `results/regressions/<PRS>_regressions_<label>.csv`

### Running the pipeline
Just launch as usual:

```bash
nextflow run main.nf -profile sge -resume
```

All parameter sets will be run automatically and in parallel where possible.

See the rest of this README for standard usage, input file formats, and pipeline options.

---

## Deployment (production folder and launching the app) 🔧

We provide a helper script to prepare a production folder with the minimal files the Dash app needs.

1) Copy files to a production folder (example: /srv/polygenie). From repo root run:

```bash
# Default destination (/srv/polygenie) - use sudo if you need privileges
scripts/prepare_prod.sh /srv/polygenie

# Optionally create a venv and install requirements (if you have requirements.txt):
scripts/prepare_prod.sh /srv/polygenie --venv

# Optionally run ingestion right after copying (safe; loader is idempotent and uses upserts):
scripts/prepare_prod.sh /srv/polygenie --ingest
```

2) Populate the database (if you did not use --ingest):

```bash
cd /srv/polygenie
python3 db/ingest_phenotypes.py   # populate target table
python3 db/db_loader.py           # ingest regression runs, percentiles, prs_manifest, gwas_metadata
```

Notes:
- The loader is idempotent and uses INSERT OR REPLACE, so re-running is safe and will update changed rows.
- The app expects the DB under `sqlitedb/polygenie.db`. The prepare script will create a symlink `sqlitedb/polygenie.db` -> `../db/polygenie.db` if the DB file exists.

3) Quick dev run (verify the server starts):

```bash
# From /srv/polygenie
python3 -c "from app.app import app; app.run_server(debug=False, host='0.0.0.0', port=8050)"
# Open http://localhost:8050
```

4) Production run suggestion (Gunicorn + systemd + nginx)

```bash
# example: run gunicorn
pip install gunicorn
gunicorn "app.app:server" -b 127.0.0.1:8050 -w 4 --preload

# create a systemd unit (see earlier README notes) and proxy with nginx for TLS and robustness.
```

If you'd like, I can also generate a sample systemd unit and nginx config and/or a Dockerfile + docker-compose for an all-in-one deploy.

