"""Parsing recipe Markdown files (frontmatter + body) into structured records."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from .paths import RECIPES_DIR

_TITLE_RE = re.compile(r"(?m)^# (.+)$")
_SOURCE_RE = re.compile(r"Fine Cooking Issue (\d+) \((.+?) (\d+)\), page (\d+)")


@dataclass
class Ingredient:
    full: str
    base: str
    unit: str
    quantity: str
    prep: str
    # Marked "***" in the "## Ingredients" bullet list: itself a recipe
    # elsewhere in the corpus (e.g. a sauce or dough), not a raw ingredient.
    is_component: bool = False


@dataclass
class Recipe:
    id: str
    title: str
    dish_type: str
    culture: str
    difficulty: str
    keywords: list[str]
    ingredients: list[Ingredient]
    issue: int
    month: str
    year: int
    page: int
    body: str  # everything after the frontmatter, unmodified, for rendering


def _parse_recipe(path: Path) -> Recipe:
    text = path.read_text(encoding="utf-8")
    _, frontmatter_text, body = text.split("---", 2)
    frontmatter = yaml.safe_load(frontmatter_text)
    body = body.strip()

    title_match = _TITLE_RE.search(body)
    title = title_match.group(1) if title_match else path.stem

    source_match = _SOURCE_RE.search(body)
    if not source_match:
        raise ValueError(f"Could not parse '## Source' line in {path}")
    issue, month, year, page = source_match.groups()

    ingredients = [
        Ingredient(
            full=ing.get("full", ""),
            base=ing.get("base", ""),
            unit=ing.get("unit", ""),
            quantity=ing.get("quantity", ""),
            prep=ing.get("prep", ""),
            is_component=bool(ing.get("component", False)),
        )
        for ing in frontmatter.get("ingredients") or []
    ]

    return Recipe(
        id=path.stem,
        title=title,
        dish_type=frontmatter.get("dish_type", ""),
        culture=frontmatter.get("culture", ""),
        difficulty=frontmatter.get("difficulty", ""),
        keywords=frontmatter.get("keywords") or [],
        ingredients=ingredients,
        issue=int(issue),
        month=month,
        year=int(year),
        page=int(page),
        body=body,
    )


def load_recipes(recipes_dir: Path = RECIPES_DIR) -> list[Recipe]:
    return [_parse_recipe(path) for path in sorted(recipes_dir.glob("*.md"))]
