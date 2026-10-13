"""
The runs your test needs. ← UNIT 4, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
the empty-search branch needs an impossible query. One about the fit card needs
the same item run more than once. Working that out is Milestone 3's first step,
and this file is where you write it down.

`run_eval.py` runs everything here five times and writes the run log — five
because your criteria are written out of five.

Three scenarios are filled in to show the shape. Add or change whatever your
own criteria need — these are a starting point, not a fixed set.
"""

SCENARIOS = [
    {
        # Criterion 1 — a query the data can match. Scored on "did the full
        # loop finish with a fit card".
        "name": "matching query completes",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 1,
    },
    {
        # Criterion 2 — a query nothing can match. The empty-search branch.
        "name": "impossible query stops early",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 2,
    },
    {
        # One of unit 4's three failure modes. Not a scored criterion; here as
        # a diagnostic so the suggest_outfit fallback is visible in the log.
        "name": "empty wardrobe fallback",
        "query": "denim jacket under $50",
        "wardrobe": "empty",
        "criterion": None,
    },
    {
        # Criterion 3 — state carries through. Normal query; what's being
        # checked is session["selected_item"]["id"] vs. the id passed into
        # suggest_outfit on that same run.
        "name": "state carries through",
        "query": "90s track jacket in size M",
        "wardrobe": "example",
        "criterion": 3,
    },
    # Criterion 4 — "5 different items share no identical opening sentence,
    # and each fit card mentions its listing's price once." Five scenarios
    # whose top search result lands on five distinct items. Scoring compares
    # Try 1 across these five rows.
    {
        "name": "fit card — slip dress",
        "query": "silk slip dress midi under $40",
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        "name": "fit card — platform sneakers",
        "query": "platform sneakers size 8",
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        "name": "fit card — cargo pants",
        "query": "low-rise cargo pants",
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        "name": "fit card — band tee",
        "query": "vintage band tee faded grey",
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        "name": "fit card — denim jacket",
        "query": "cropped denim jacket light wash",
        "wardrobe": "example",
        "criterion": 4,
    },
    # Criterion 5 — "10 random queries with max_price; every search_results
    # listing has price <= max_price, 10 of 10." Two scenarios × 5 tries each
    # yields 10 observations. (Search is deterministic so the 5 tries of each
    # scenario produce identical lists — the breadth comes from using two
    # different price caps on two different styles.)
    {
        "name": "price ceiling — jacket under $40",
        "query": "jacket under $40",
        "wardrobe": "example",
        "criterion": 5,
    },
    {
        "name": "price ceiling — tee under $20",
        "query": "tee under $20",
        "wardrobe": "example",
        "criterion": 5,
    },
]

WARDROBES = ("example", "empty")


def validate() -> list[str]:
    """Complain about anything malformed, before a long run rather than during."""
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("query", "").strip():
            problems.append(f"scenario {i} has no query")
        if scenario.get("wardrobe") not in WARDROBES:
            problems.append(
                f"scenario {i} has wardrobe {scenario.get('wardrobe')!r} — "
                f"it should be one of {WARDROBES}"
            )
    return problems
