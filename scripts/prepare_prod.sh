#!/usr/bin/env bash
set -euo pipefail

# Prepare a production folder with the minimal required files for the Dash app
# Usage: scripts/prepare_prod.sh [DEST] [--ingest] [--venv]
#   DEST default: /srv/polygenie
#   --ingest : run ingest scripts after copying (may create/modify db/polygenie.db)
#   --venv   : create a virtualenv in DEST/.venv and install requirements if found

DEST=${1:-/srv/polygenie}
shift || true
DO_INGEST=0
DO_VENV=0
FORCE=0

while (( "$#" )); do
  case "$1" in
    --ingest) DO_INGEST=1; shift;;
    --venv) DO_VENV=1; shift;;
    --force) FORCE=1; shift;;
    -h|--help) echo "Usage: $0 [DEST] [--ingest] [--venv] [--force]"; exit 0;;
    *) echo "Unknown argument: $1"; echo "Usage: $0 [DEST] [--ingest] [--venv] [--force]"; exit 1;;
  esac
done

echo "Preparing production folder at: $DEST"
mkdir -p "$DEST"

RSYNC_EXCLUDES=( --exclude '.git' --exclude 'work/' --exclude '__pycache__' --exclude '.venv' )

# Directories / files to copy
COPIES=( 
  app 
  db 
  envs 
  data/gwas_metadata.csv 
  results/preprocessing/phenotypes_valid.csv 
  results/preprocessing/prs_present.csv 
  app/assets
  README.md
  scripts/prepare_prod.sh
)

echo "Copying files..."
for p in "${COPIES[@]}"; do
  if [ -e "$p" ]; then
    echo " - $p"
    mkdir -p "${DEST}/$(dirname "$p")"
    rsync -a ${RSYNC_EXCLUDES[@]} "$p" "$DEST/$(dirname "$p")/"
  else
    echo " - Warning: source not found: $p"
  fi
done

# Ensure db folder exists
mkdir -p "$DEST/db"

# Create sqlitedb dir and symlink to db/polygenie.db (if it exists)
mkdir -p "$DEST/sqlitedb"
if [ -e "$DEST/db/polygenie.db" ]; then
  if [ -e "$DEST/sqlitedb/polygenie.db" ]; then
    echo "sqlitedb/polygenie.db already exists in destination"
  else
    ln -s ../db/polygenie.db "$DEST/sqlitedb/polygenie.db" || true
    echo "Created symlink sqlitedb/polygenie.db -> ../db/polygenie.db"
  fi
fi

# Optionally create a venv and install requirements (if requested)
if [ "$DO_VENV" -eq 1 ]; then
  echo "Creating venv in $DEST/.venv"
  python3 -m venv "$DEST/.venv"
  export PATH="$DEST/.venv/bin:$PATH"
  if [ -f requirements.txt ]; then
    echo "Installing requirements from requirements.txt into venv"
    pip install -r requirements.txt
  else
    echo "No requirements.txt found; please use conda env file at envs/polygenie-pipeline.yml or add a requirements.txt"
  fi
fi

# Optionally run ingestion scripts
if [ "$DO_INGEST" -eq 1 ]; then
  echo "Running ingest scripts in $DEST"
  pushd "$DEST" >/dev/null
  # Use .venv python if present
  PY=python3
  if [ -x "$DEST/.venv/bin/python" ]; then
    PY="$DEST/.venv/bin/python"
  fi

  if [ -f db/ingest_phenotypes.py ]; then
    echo " - ingesting phenotypes"
    "$PY" db/ingest_phenotypes.py
  else
    echo " - missing db/ingest_phenotypes.py"
  fi

  if [ -f db/db_loader.py ]; then
    echo " - running db_loader to ingest results (this may take time)"
    "$PY" db/db_loader.py
  else
    echo " - missing db/db_loader.py"
  fi
  popd >/dev/null
fi

cat <<EOF

Done. Next steps (example):
  - If needed, create a python environment in the destination (conda or venv).
  - Populate DB: run inside $DEST: python3 db/ingest_phenotypes.py && python3 db/db_loader.py
  - Ensure the app can find the DB (sqlitedb/polygenie.db should exist or symlink to db/polygenie.db)
  - Start the app for a quick test: python3 -c "from app.app import app; app.run_server(debug=False, host='0.0.0.0', port=8050)"

If you want, run this script with --venv and/or --ingest flags to create a venv & ingest automatically.
EOF
