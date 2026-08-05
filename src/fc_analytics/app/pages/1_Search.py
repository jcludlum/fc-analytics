import re

import pandas as pd
import streamlit as st

from fc_analytics.recipes import load_recipes

# Fixed enums from data/RECIPE_INSTRUCTIONS.md, rather than just values seen
# so far, so every valid option is always selectable.
DISH_TYPES = [
    "appetizer",
    "beverage",
    "soup",
    "salad",
    "main dish (meat)",
    "main dish (seafood)",
    "main dish (poultry)",
    "main dish (vegetable)",
    "side dish",
    "sauce/condiment",
    "seasoning",
    "dessert",
]
DIFFICULTIES = ["easy", "moderate", "challenging"]

st.set_page_config(page_title="Search | Fine Cooking Analytics", layout="wide")

st.title("Search Recipes")


@st.cache_data
def get_recipes():
    return load_recipes()


recipes = get_recipes()

cultures = sorted({r.culture for r in recipes if r.culture}, key=str.casefold)
ingredient_options = sorted(
    {ing.base for r in recipes for ing in r.ingredients if ing.base and not ing.is_component},
    key=str.casefold,
)
min_issue, max_issue = min(r.issue for r in recipes), max(r.issue for r in recipes)
min_year, max_year = min(r.year for r in recipes), max(r.year for r in recipes)

with st.container(border=True):

    title_query = st.text_input("Title contains")

    col1, col2 = st.columns(2)
    with col1:
        if min_issue < max_issue:
            issue_range = st.slider("Issue number", min_issue, max_issue, (min_issue, max_issue))
        else:
            issue_range = (min_issue, max_issue)
            st.caption(f"Issue number: {min_issue} (only issue processed so far)")
    with col2:
        if min_year < max_year:
            year_range = st.slider("Publication year", min_year, max_year, (min_year, max_year))
        else:
            year_range = (min_year, max_year)
            st.caption(f"Publication year: {min_year} (only year processed so far)")

    col3, col4, col5, col6 = st.columns(4)
    with col3:
        selected_dish_types = st.multiselect("Dish type", DISH_TYPES)
    with col4:
        selected_cultures = st.multiselect("Culture", cultures)
    with col5:
        selected_difficulties = st.multiselect("Difficulty", DIFFICULTIES)
    with col6:
        selected_ingredients = st.multiselect("Ingredients", ingredient_options)

results = recipes
if title_query:
    results = [r for r in results if title_query.lower() in r.title.lower()]
if issue_range != (min_issue, max_issue):
    results = [r for r in results if issue_range[0] <= r.issue <= issue_range[1]]
if year_range != (min_year, max_year):
    results = [r for r in results if year_range[0] <= r.year <= year_range[1]]
if selected_dish_types:
    results = [r for r in results if r.dish_type in selected_dish_types]
if selected_cultures:
    results = [r for r in results if r.culture in selected_cultures]
if selected_difficulties:
    results = [r for r in results if r.difficulty in selected_difficulties]
if selected_ingredients:
    selected_set = set(selected_ingredients)
    results = [r for r in results if selected_set.issubset({ing.base for ing in r.ingredients})]

results = sorted(results, key=lambda r: (r.issue, r.page))

st.write(f"**{len(results)} recipe(s) found**")

table = pd.DataFrame(
    [
        {
            "recipe": r.title,
            "issue": r.issue,
            "year": r.year,
            "month": r.month,
            "page": r.page,
        }
        for r in results
    ],
    columns=["recipe", "issue", "year", "month", "page"],
)
event = st.dataframe(
    table,
    hide_index=True,
    use_container_width=True,
    height=500,
    on_select="rerun",
    selection_mode="single-row",
)

selected_rows = event.selection.rows
if selected_rows:
    selected_recipe = results[selected_rows[0]]
    st.divider()
    st.subheader(selected_recipe.title)
    st.caption(
        f"Fine Cooking Issue {selected_recipe.issue}, ({selected_recipe.month} {selected_recipe.year}), "
        f"page {selected_recipe.page}"
    )
    body_lines = selected_recipe.body.split("\n", 1)
    display_body = body_lines[1].strip() if body_lines[0].startswith("# ") else selected_recipe.body
    display_body = display_body.split("## Source")[0].rstrip()
    display_body = re.sub(
        r" \*\*\*$",
        " :gray-badge[component recipe]",
        display_body,
        flags=re.MULTILINE,
    )
    display_body = re.sub(r"\n\n\*\*\* = component recipe\n", "\n", display_body)
    st.markdown(display_body)
