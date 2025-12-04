#!/usr/bin/env bash
set -e

# ---- CONFIG: edit these for your environment ----
DB_NAME="fitness_tracker"
DB_USER="postgres"    # change if needed
DB_HOST="localhost"
DB_PORT="5432"
# -------------------------------------------------

echo "Creating database (if needed)..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" \
  | grep -q 1 || psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "CREATE DATABASE $DB_NAME;"

echo "Loading schema..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f schema.sql

echo "Creating virtual env & installing deps..."
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

echo "Starting CLI app..."
python app.py
