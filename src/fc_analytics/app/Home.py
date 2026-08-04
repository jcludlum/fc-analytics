import csv

import streamlit as st

from fc_analytics.paths import RECIPES_CSV, RECIPES_DIR

TOTAL_REGULAR_ISSUES = 175

st.set_page_config(page_title="Fine Cooking Analytics", layout="wide")

st.title("Fine Cooking Analytics")

st.markdown(
"""
Fine Cooking was a cooking magazine published from 1994 until its
discontinuation in 2019. This website enables Fine Cooking enthusiasts to:

- Search Fine Cooking recipes by title, ingredients, publication year, and more
- View recipes extracted from Fine Cooking PDFs with AI assistance
- Explore two-dimensional clustering of recipes similar to [ArXiv Atlas](https://atlas.uslu.tech/selection.html)
"""
)

st.subheader("Progress")

with RECIPES_CSV.open(encoding="utf-8") as f:
    processed_issues = len({row["issue"] for row in csv.DictReader(f)})
recipe_count = sum(1 for _ in RECIPES_DIR.glob("*.md"))

fraction = processed_issues / TOTAL_REGULAR_ISSUES
st.progress(fraction)

col1, col2, col3 = st.columns(3)
col1.metric("Regular issues processed", f"{processed_issues} / {TOTAL_REGULAR_ISSUES}")
col2.metric("Completion", f"{fraction:.0%}")
col3.metric("Recipes extracted", recipe_count)
