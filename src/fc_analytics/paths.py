"""Shared filesystem paths for the data processing pipeline."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"

RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
RECIPES_DIR = PROCESSED_DIR / "recipes"
TEXT_EXTRACTION_DIR = PROCESSED_DIR / "text_extraction"

SCRATCH_TXT = DATA_DIR / "scratch.txt"
RECIPES_CSV = DATA_DIR / "recipes.csv"
DB_PATH = DATA_DIR / "fc_analytics.db"
