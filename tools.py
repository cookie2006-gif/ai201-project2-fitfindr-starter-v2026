"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings


# ── Tool 1: search_listings ───────────────────────────────────────────────────

# Words that carry no signal when matching a description against a listing.
# Keeping these out of the keyword set stops a query like "a vintage tee under
# $30" from matching every listing in the file because every listing contains
# "a" or "the" somewhere in its description.
_STOPWORDS = {
    "a", "an", "and", "the", "for", "with", "of", "in", "on", "to", "under",
    "over", "below", "above", "or", "my", "me", "i", "it", "is", "size",
    "please", "want", "looking", "need", "find", "some", "any", "that", "this",
    "like", "something", "wearable", "price", "cheap", "affordable", "max",
}


def _tokens(text: str) -> set[str]:
    """Lowercase word tokens, stopwords and short noise words removed."""
    words = re.findall(r"[a-zA-Z0-9]+", (text or "").lower())
    return {w for w in words if len(w) > 1 and w not in _STOPWORDS}


def _size_matches(requested: str, listing_size: str) -> bool:
    """
    A size match is a token match, not a substring match.

    Substring matching is the trap this function exists to avoid. "s" in "us 9"
    is True, "l" in "xl" is True, and either one causes shoes to show up when
    someone asked for a small top. Splitting both sides on slashes, spaces and
    parens and comparing the resulting tokens avoids that: "M" matches "S/M"
    and "M/L" and "M (oversized)", but not "XL" and not "US 9".
    """
    req = requested.strip().upper()
    if not req:
        return True
    listing_tokens = {t for t in re.split(r"[\s/()]+", listing_size.upper()) if t}
    return req in listing_tokens


def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    Returns a list of listing dicts, best match first. Returns an empty list
    when nothing matches — not None, not an exception. The planning loop in
    agent.py branches on exactly that empty list.
    """
    query_tokens = _tokens(description)
    results: list[tuple[int, dict]] = []

    for listing in load_listings():
        if max_price is not None and listing["price"] > max_price:
            continue
        if size and not _size_matches(size, listing["size"]):
            continue

        haystack_parts = [
            listing.get("title", ""),
            listing.get("description", ""),
            listing.get("category", ""),
            " ".join(listing.get("style_tags", []) or []),
            " ".join(listing.get("colors", []) or []),
            listing.get("brand") or "",
        ]
        listing_tokens = _tokens(" ".join(haystack_parts))
        score = len(query_tokens & listing_tokens)

        # No description keywords given means every price/size-filtered listing
        # qualifies equally — don't drop them all for a zero score.
        if not query_tokens or score > 0:
            results.append((score, listing))

    results.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in results[: config.SEARCH_RESULT_LIMIT]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    Falls back to general styling advice when the wardrobe is empty, so the
    tool returns a non-empty string in every case rather than raising.
    """
    items = (wardrobe or {}).get("items") or []

    item_summary = (
        f"- Title: {new_item.get('title')}\n"
        f"- Category: {new_item.get('category')}\n"
        f"- Colors: {', '.join(new_item.get('colors') or []) or 'unspecified'}\n"
        f"- Style tags: {', '.join(new_item.get('style_tags') or []) or 'unspecified'}\n"
        f"- Size: {new_item.get('size')}\n"
    )

    if not items:
        prompt = (
            "A shopper is considering buying this thrifted piece:\n"
            f"{item_summary}\n"
            "They haven't entered a wardrobe yet, so you don't know what they "
            "already own. In 2–3 short sentences, suggest the kind of pieces "
            "that would pair well with it (categories, colors, silhouettes). "
            "Keep it concrete — name item types, not abstract advice."
        )
        return generate(prompt).strip()

    wardrobe_lines = []
    for w in items:
        colors = ", ".join(w.get("colors") or []) or "—"
        tags = ", ".join(w.get("style_tags") or []) or "—"
        wardrobe_lines.append(
            f"- {w.get('name')} ({w.get('category')}; colors: {colors}; tags: {tags})"
        )
    wardrobe_block = "\n".join(wardrobe_lines)

    prompt = (
        "A shopper is considering buying this thrifted piece:\n"
        f"{item_summary}\n"
        "Here is what they already own:\n"
        f"{wardrobe_block}\n\n"
        "Suggest ONE or TWO complete outfits built around the new piece, "
        "naming specific wardrobe items by their name. Keep each outfit to "
        "one or two sentences. Do not invent items that are not in the list."
    )
    return generate(prompt).strip()


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    Returns a short descriptive message if the outfit text is empty or just
    whitespace, rather than calling the model on nothing.
    """
    if not outfit or not outfit.strip():
        return (
            "Can't write a fit card yet — no outfit suggestion was provided. "
            "Run suggest_outfit first."
        )

    title = new_item.get("title", "this piece")
    price = new_item.get("price")
    platform = new_item.get("platform", "a thrift app")
    tags = ", ".join(new_item.get("style_tags") or []) or "thrifted"

    prompt = (
        "Write a short social-media caption (2–4 sentences) for a thrifted "
        "find. Make it feel like a real post, not a product listing. Mention "
        "the item, its price, and the platform exactly once each. Be specific "
        "about the vibe. Light use of emoji is fine.\n\n"
        f"Item: {title}\n"
        f"Price: ${price}\n"
        f"Platform: {platform}\n"
        f"Vibe tags: {tags}\n"
        f"How I'd wear it: {outfit}\n"
    )
    return generate(prompt).strip()
