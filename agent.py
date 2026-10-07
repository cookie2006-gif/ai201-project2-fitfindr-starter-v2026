"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

    python agent.py          runs both example paths below
"""

import re

import config
import trace
from tools import search_listings, suggest_outfit, create_fit_card
from generate import ModelUnavailable


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction. The session is the single source
    of truth for a run — every tool result goes in here and the next tool
    reads it back out.
    """
    return {
        "query": query,
        "parsed": {},
        "search_results": [],
        "selected_item": None,
        "wardrobe": wardrobe,
        "outfit_suggestion": None,
        "fit_card": None,
        "error": None,
    }


# ── query parsing ─────────────────────────────────────────────────────────────

# Known size vocabulary pulled from the data. Keeping this as a small set makes
# "size M" extraction a straight whole-word match rather than a guess.
_LETTER_SIZES = {"XXS", "XS", "S", "M", "L", "XL", "XXL"}

_SIZE_PATTERNS = [
    re.compile(r"\bsize\s+([a-z0-9]+)\b", re.I),
    re.compile(r"\bin\s+(?:a\s+)?size\s+([a-z0-9]+)\b", re.I),
    re.compile(r"\b(w\d{2})\b", re.I),
    re.compile(r"\b(us\s*\d+(?:\.\d)?)\b", re.I),
]

_PRICE_PATTERNS = [
    re.compile(r"under\s*\$?\s*(\d+(?:\.\d+)?)", re.I),
    re.compile(r"below\s*\$?\s*(\d+(?:\.\d+)?)", re.I),
    re.compile(r"less\s+than\s*\$?\s*(\d+(?:\.\d+)?)", re.I),
    re.compile(r"max(?:imum)?\s*\$?\s*(\d+(?:\.\d+)?)", re.I),
    re.compile(r"\$\s*(\d+(?:\.\d+)?)\s*(?:or\s+less|max)?", re.I),
]


def _parse_query(query: str) -> dict:
    """
    Pull a description, size and max_price out of the raw user query.

    Simple regex rather than another model call — the parsing is small, every
    extra model call is a dollar and a rate-limit slot, and a wrong regex is
    much easier to debug than a wrong prompt.
    """
    size: str | None = None
    for pattern in _SIZE_PATTERNS:
        match = pattern.search(query)
        if match:
            raw = match.group(1).strip().upper().replace("  ", " ")
            if raw in _LETTER_SIZES or raw.startswith(("W", "US")):
                size = raw
                break

    max_price: float | None = None
    for pattern in _PRICE_PATTERNS:
        match = pattern.search(query)
        if match:
            try:
                max_price = float(match.group(1))
                break
            except ValueError:
                pass

    # Everything else is the description. Stripping the matched phrases keeps
    # price/size words from inflating the keyword overlap score.
    description = query
    for pattern in _SIZE_PATTERNS + _PRICE_PATTERNS:
        description = pattern.sub(" ", description)
    description = re.sub(r"\s+", " ", description).strip(" ,.")

    return {"description": description, "size": size, "max_price": max_price}


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Check session["error"] first — if it isn't None, the run ended early and
    the later fields will still be None.

    Branch rule: if search_listings returns an empty list, put a message in
    session["error"] saying what the user could change and return. Otherwise
    put the first result in session["selected_item"] and continue through
    suggest_outfit and create_fit_card.
    """
    session = new_session(query, wardrobe)
    trace.start_trace()

    try:
        iterations = 0

        # Step 1 — parse the query.
        iterations += 1
        trace.check_iterations(iterations)
        session["parsed"] = _parse_query(query)
        trace.step("parse_query", inputs=query, returned=session["parsed"])

        # Step 2 — search_listings.
        iterations += 1
        trace.check_iterations(iterations)
        parsed = session["parsed"]
        session["search_results"] = search_listings(
            description=parsed["description"],
            size=parsed["size"],
            max_price=parsed["max_price"],
        )
        trace.step(
            "search_listings",
            inputs=parsed,
            returned=session["search_results"],
        )

        # ── THE BRANCH ───────────────────────────────────────────────────────
        if not session["search_results"]:
            bits = []
            if parsed["max_price"] is not None:
                bits.append(f"raising the price above ${parsed['max_price']:.0f}")
            if parsed["size"]:
                bits.append(f"loosening the size filter (you asked for {parsed['size']})")
            if parsed["description"]:
                bits.append("using fewer or different keywords")
            suggestion = "; ".join(bits) if bits else "a broader query"
            session["error"] = (
                f"No listings matched '{query}'. Try {suggestion}."
            )
            trace.step(
                "branch",
                note="search returned empty — stopping before suggest_outfit",
            )
            return session

        # Step 3 — pick the top result and stash it in the session.
        iterations += 1
        trace.check_iterations(iterations)
        session["selected_item"] = session["search_results"][0]
        trace.step(
            "select_item",
            returned=session["selected_item"],
            note="first result wins",
        )

        # Step 4 — suggest_outfit, reading the selected item back from state.
        iterations += 1
        trace.check_iterations(iterations)
        session["outfit_suggestion"] = suggest_outfit(
            session["selected_item"],
            session["wardrobe"],
        )
        trace.step(
            "suggest_outfit",
            inputs={"item": session["selected_item"].get("title")},
            returned=session["outfit_suggestion"],
        )

        # Step 5 — create_fit_card, again reading both inputs out of state.
        iterations += 1
        trace.check_iterations(iterations)
        session["fit_card"] = create_fit_card(
            session["outfit_suggestion"],
            session["selected_item"],
        )
        trace.step(
            "create_fit_card",
            inputs={"item": session["selected_item"].get("title")},
            returned=session["fit_card"],
        )

    except ModelUnavailable as exc:
        session["error"] = (
            f"The model couldn't be reached: {exc}. "
            "Check your GEMINI_API_KEY in .env, then try again."
        )

    return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
