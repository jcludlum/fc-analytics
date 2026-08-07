# Instructions: Generating Recipe Markdown Files

These instructions describe how to turn one row of `data/recipes.csv` into one
`data/processed/recipes/recipe_<NNNNN>.md` file. `recipe_00001.md`
("Cappelletti in Brodo") is the reference example — when in doubt, match its
conventions.

## Inputs

- **Metadata**: `data/recipes.csv` (`id`, `recipe`, `issue`, `year`, `month`, `page`).
- **Content**: `data/processed/text_clean/FC_<NNN>.txt`, where `<NNN>` is the
  `issue` column zero-padded to 3 digits. Find the recipe using the `page`
  number (search for `--- Page <page> ---`) and the recipe title.

## Output

- One file per recipe: `data/processed/recipes/recipe_<NNNNN>.md`, where
  `<NNNNN>` is the `id` column, already zero-padded to 5 digits in the CSV.

## Fidelity rule, and its one exception

All content — description, ingredients, directions — must come from the
source `text_clean` file. Do not invent content, add ingredients, or inject
background knowledge that isn't in the source text.

**Exception: confidently-inferable extraction errors.** Text extraction from
these PDFs isn't perfect — OCR and broken font encodings (especially for
fraction glyphs like ½, ¼, ¾) can produce garbled text even after manual
cleanup. If an error has an obvious, confidently-inferable fix from
immediate context, correct it in the `.md` file:

- Obvious OCR typos: `pOSSible` → `possible`.
- Garbled fraction glyphs where context makes the true value clear — but use
  real judgment about what value makes sense for *that specific instruction*,
  don't just default to matching some other fraction seen elsewhere in the
  document. (E.g. a "the corners should miss by ___ inch" gap when sealing
  dough is plausibly a small value like 1/8", not automatically whatever
  fraction happened to appear in the ingredient list.)

If no confident fix is possible — content is missing, ambiguous, or would
require guessing at unstated facts (e.g. a sentence with an apparently
dropped clause) — leave the text exactly as extracted. Do not fabricate a
plausible-sounding replacement.

**Always report every correction or uncertainty you noticed in your
response to the user, separate from the file itself** (e.g. "I fixed X, and
flagged Y since I wasn't confident"), so they can decide whether to also
patch the upstream `text_clean/FC_NNN.txt` file. Don't edit `text_clean`
yourself unless asked — treat it as the user's canonical, hand-reviewed
source.

## File structure

```markdown
---
ingredients:
  - full: "<ingredient exactly as it appears in the source, after any compound-splitting>"
    base: "<standardized base ingredient, lowercase except proper nouns/adjectives, e.g. 'chicken broth', 'Dijon mustard'>"
    unit: "<standardized unit, lowercase, no periods: cup, tsp, tbsp, oz, lb, qt, gal, etc. Blank if not a standard measurable unit (e.g. whole eggs, bay leaves, cloves).>"
    quantity: "<amount as a fraction string, e.g. '1/4', '2'. Blank if no amount is given in the source (e.g. 'salt to taste').>"
    prep: "<preparation method, e.g. chopped, diced, peeled, grated, minced. Blank if none given.>"
    component: <true if this ingredient is itself a recipe with its own entry elsewhere in the corpus (e.g. a sauce or dough), else false>
  - full: "..."
    ...
dish_type: "<one of: appetizer, beverage, soup, salad, main dish (meat), main dish (seafood), main dish (poultry), main dish (vegetable), side dish, sauce/condiment, seasoning, dessert>"
culture: "<cuisine/culture of origin, e.g. Italian, Mexican, Japanese, American fusion>"
difficulty: "<one of: easy, moderate, challenging>"
keywords:
  - "<freeform searchable keyword or short phrase>"
---
# <Recipe Name>

<Description paragraph(s), taken directly from the source.>

## Ingredients

- <ingredient 1, same text as its `full` field>
- <ingredient 2>
...

*** = component recipe

## Directions

1. <step 1>
2. <step 2>
...

## Metadata

- Dish Type: <dish_type>
- Culture: <culture>
- Difficulty: <difficulty>

## Keywords

<keywords, comma-separated>

## Source

Fine Cooking Issue <issue> (<Month> <year>), page <page>
```

## Ingredient rules

- **One entry per distinct ingredient.** Split compound ingredients joined by
  "and"/"or" into separate entries (`"Salt and pepper"` → `salt` + `pepper`;
  `"zucchini or cucumber"` → `zucchini` + `cucumber`). Don't split
  multi-word descriptors of a single ingredient (`"boneless, skinless
  chicken breasts"` stays one entry, with `prep: "boneless, skinless"`).
- **Capitalization is consistent across the corpus.** `base` (and `full`)
  are lowercase, except proper nouns/adjectives, which keep their standard
  capitalization: nationalities/regions (`Dijon mustard`, `Italian
  parsley`, `Chinese cabbage`), brand names, etc. Use the exact same
  capitalization for the same ingredient every time it appears in any
  recipe — `Dijon mustard` and `dijon mustard` must not both occur, since
  each becomes a distinct, duplicate entry in ingredient search/filtering.
- **Flatten multi-component ingredient lists.** Recipes often split
  ingredients into sub-groups (`FOR THE FILLING:`, `FOR THE SAUCE:`, `TO
  SERVE:`, etc.). List them all under one flat `## Ingredients` list, in
  source order — no subheadings. If the same ingredient appears in more than
  one group (e.g. Parmesan used both in a filling and for serving), keep
  them as separate entries; they're added at different points.
- **Quantity** is a fraction string (`"1/4"`, `"2"`), not a decimal. Leave it
  blank if the source gives no amount at all.
- **Unit** is standardized and lowercase with no periods. Leave it blank for
  whole-item/count ingredients that don't have a conventional measurement
  unit (`"1 large egg"`, `"1 bay leaf"`, `"2 cloves garlic"`) — the item name
  goes in `base` instead.
- **Prep** captures preparation actions (chopped, diced, grated, minced,
  freshly ground, etc.), not size/grade descriptors like "large" (egg) or
  "extra-virgin" (olive oil) or "unbleached" (flour) — those stay embedded in
  `full`/`base` only.
- **Component recipes**: if an ingredient is itself a recipe with its own
  entry elsewhere in the corpus (e.g. a sauce or dough used as an
  ingredient), set `component: true` in its frontmatter entry **and** mark
  it with `***` in the `## Ingredients` bullet list (the two must agree).
- **No page/location references.** Strip parenthetical page or layout
  references to component recipes (`"(p. 21)"`, `"(see recipe at right)"`,
  `"(see recipe on opposite page)"`, `", p. 44"`, etc.) from `full`, the
  description, and the directions. The Streamlit app doesn't preserve the
  original magazine layout, so these pointers are meaningless there — the
  `***` marker (plus the recipe title itself) is what signals "this is a
  component recipe," not a page number.

## Directions rules

- Magazines often present steps as disjointed prose interrupted by sidebar
  captions (e.g. a numbered illustration walkthrough for shaping pasta,
  printed next to the main text rather than inline with it). Merge all of
  this into **one logical, sequential numbered list** describing the full
  process in cooking order. Light rewording for flow/imperative consistency
  is fine; don't add technique detail, times, or temperatures that aren't in
  the source.
- Exclude content that isn't part of making the recipe itself — equipment
  sourcing sidebars, author bios, unrelated serving suggestions for other
  dishes on the same page, etc.

## Metadata rules

- **Dish Type** must be exactly one of the fixed list above.
- **Culture** is free text naming an actual cuisine/culture, kept at the
  national/broad level (`Italian`, not `Italian (Sardinian)` or `Italian
  (Ligurian)`) so recipes from the same cuisine group together instead of
  fragmenting into one-off sub-regional variants. Sub-regional specificity
  belongs in `keywords` instead (e.g. `"Sardinian"`, `"Ligurian"`).
- **Difficulty** is easy/moderate/challenging, based on concrete factors:
  number of ingredients, number of components/sub-recipes, techniques
  required (e.g. hand-shaping stuffed pasta is harder than sautéing), and
  overall number of steps — not a gut feeling.

## Keywords rules

Freeform tags capturing defining characteristics not already covered by
Dish Type/Culture or the ingredient list itself (e.g. technique, regional
specificity, notable characteristic). Do not include the recipe author's
name, magazine sourcing/resource info, or generic filler terms.

## Source line

`Fine Cooking Issue <issue> (<Month> <year>), page <page>` — expand the
month abbreviation from the CSV to its full name (`Mar` → `March`).