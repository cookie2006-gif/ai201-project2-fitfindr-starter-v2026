# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

A user types a plain-language thrift request — something like
`vintage graphic tee under $30, size M` — and FitFindr runs it through three
tools in order: a keyword search over the mock listings file, a model-written
outfit suggestion that combines the top match with the user's wardrobe, and a
short caption written as if the user were posting the find themselves. If the
search comes back empty, the agent stops before calling the model and returns
a message naming what to change about the query. Everything is held together
by a session dict in [agent.py](agent.py) so each tool reads its inputs out of
state rather than being handed them as function arguments.

---

## Tool Inventory

### `search_listings`

- **What it does:** Filters the mock listings in `data/listings.json` by
  price and size, scores what's left by keyword overlap against the user's
  description, and returns the best matches first.
- **Inputs:** `description` (str), `size` (str | None), `max_price` (float | None).
- **Returns:** A `list[dict]`, up to `config.SEARCH_RESULT_LIMIT` entries, each
  with the keys `id, title, description, category, style_tags, size, condition,
  price, colors, brand, platform` — same shape as a row in `listings.json`.
  Sorted by keyword-overlap score, highest first.
- **When it has nothing:** Returns `[]`. Never `None`, never an exception. The
  planning loop branches on exactly this empty list.

### `suggest_outfit`

- **What it does:** Calls the model with the new item and the user's wardrobe
  and asks for one or two outfits built around the item, naming specific
  wardrobe pieces by name.
- **Inputs:** `new_item` (dict — a listing in the same shape `search_listings`
  returns), `wardrobe` (dict with an `items` key holding a `list[dict]`;
  `items` may be empty).
- **Returns:** A non-empty `str` — a short outfit suggestion. With a non-empty
  wardrobe it names specific pieces; with an empty wardrobe it returns general
  styling advice (categories, colors, silhouettes) instead of raising.
- **When it has nothing:** On an empty wardrobe (`items == []`) it returns a
  general styling blurb for the new item on its own. It does not return `""`
  and it does not raise.

### `create_fit_card`

- **What it does:** Calls the model to write a 2–4 sentence social-media
  caption for the find, anchored on the item, its price, its platform, and the
  outfit the previous tool produced.
- **Inputs:** `outfit` (str — the string from `suggest_outfit`), `new_item`
  (dict — same shape as a listing).
- **Returns:** A non-empty `str` — a 2–4 sentence caption. Expected to vary
  across calls because `TEMPERATURE = 0.9` and the cache is a key on the full
  prompt, so a different outfit string or a different item gives different
  words.
- **When it has nothing:** If `outfit` is empty or whitespace-only, returns a
  short descriptive message explaining the dependency, rather than calling the
  model on nothing or raising.

---

## Planning Loop

**Branch rule:** If `search_listings` returns an empty list, put a message in
`session["error"]` naming what the user could change (price ceiling, size,
keywords) and return the session — do not call `suggest_outfit`. Otherwise,
put the first search result in `session["selected_item"]` and continue through
`suggest_outfit` and `create_fit_card`, writing each tool's result back into
the session before the next one reads it.

**Where it lives:** [agent.py::run_agent](agent.py#L92)

**How the query is parsed:** Regex, in `_parse_query` at
[agent.py:_parse_query](agent.py#L52). A short list of size patterns pulls out
letter sizes (XXS–XXL), waist sizes (`W28`) and US shoe sizes (`US 9`); a
short list of price patterns pulls out `under $30`, `below $30`, `less than
30`, `max $30` and bare `$30`. The matched phrases are stripped out of the
description so they don't inflate the keyword-overlap score. Regex over
another model call — the parsing is small, every extra model call is a dollar
and a rate-limit slot, and a wrong regex is much easier to debug than a wrong
prompt.

**What moves through the session:** `query` → `parsed`
(`description`/`size`/`max_price`) → `search_results` → `selected_item` →
`outfit_suggestion` → `fit_card`. Each tool writes its output into the
session; the next tool reads its inputs out of it. `error` is set and the run
returns early if `search_results` is empty, in which case every field after
`search_results` stays `None`.

---

## Sample Run

**One full query**

```
$ python app.py ask 'vintage graphic tee under $30, size M'
[1] parse_query
      in:  vintage graphic tee under $30, size M
      out: dict with keys: description, size, max_price
[2] search_listings
      in:  dict with keys: description, size, max_price
      out: 8 items: Y2K Baby Tee — Butterfly Print, Mesh Long-Sleeve Top — Black, 90s Silk Slip Dress — Floral, Midi Length … +5 more
[3] select_item
      out: Y2K Baby Tee — Butterfly Print ($18.0, depop)
      →    first result wins
[4] suggest_outfit
      in:  dict with keys: item
      out: **Outfit 1:** Pair the Y2K Baby Tee with the baggy straight-leg jeans and chunky white sneakers for a classic,…
[5] create_fit_card
      in:  dict with keys: item
      out: Obsessed with this little butterfly tee I just scored on depop for only $18.00! It’s giving major Y2K nostalgi…

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   **Outfit 1:** Pair the Y2K Baby Tee with the baggy straight-leg jeans and chunky white sneakers for a classic, nostalgic streetwear look.

**Outfit 2:** Style the Y2K Baby Tee tucked into the wide-leg khaki trousers, layered under the vintage black denim jacket, and accessorized with the brown leather belt and black combat boots.

  Fit card: Obsessed with this little butterfly tee I just scored on depop for only $18.00! It’s giving major Y2K nostalgia, but I love dressing it down with baggy jeans and chunky sneakers for an effortless day out. Such a good vintage find for the rotation 🦋✨

1 model calls this session, 1 served from cache, 183 prompt + 61 output tokens
```

And the empty-search branch, to show the loop takes a different path:

```
$ python app.py ask 'designer ballgown size XXS under $5'
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: dict with keys: description, size, max_price
[2] search_listings
      in:  dict with keys: description, size, max_price
      out: [] (empty)
[3] branch
      →    search returned empty — stopping before suggest_outfit

  No listings matched 'designer ballgown size XXS under $5'. Try raising the price above $5; loosening the size filter (you asked for XXS); using fewer or different keywords.

0 model calls this session
```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; r=search_listings('graphic tee', max_price=30); print(f'{len(r)} results'); [print(f'  - {x[\"id\"]} | {x[\"title\"]} | \${x[\"price\"]} | {x[\"size\"]} | {x[\"platform\"]}') for x in r[:5]]"
6 results
  - lst_002 | Y2K Baby Tee — Butterfly Print | $18.0 | S/M | depop
  - lst_006 | Graphic Tee — 2003 Tour Bootleg Style | $24.0 | L | depop
  - lst_017 | Mesh Long-Sleeve Top — Black | $15.0 | S/M | depop
  - lst_033 | Vintage Band Tee — Faded Grey | $19.0 | L | depop
  - lst_011 | Low-Rise Cargo Pants — Khaki | $27.0 | W29 | poshmark
```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[1], get_example_wardrobe()))"
**Outfit 1:** Pair the Y2K Baby Tee with the baggy straight-leg jeans and chunky white sneakers for a classic, nostalgic streetwear look.

**Outfit 2:** Style the Y2K Baby Tee tucked into the wide-leg khaki trousers, layered under the vintage black denim jacket, and accessorized with the brown leather belt and black combat boots.
```

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('baggy straight-leg jeans + chunky white sneakers', load_listings()[1]))"
Found my ultimate early 2000s daydream on depop for just $18.0! That dreamy butterfly graphic gives off the sweetest little cottagecore-meets-y2k vibe. Can’t wait to style it with my go-to baggy straight-leg jeans and chunky white sneakers. 🦋✨
```

---

## How I Used AI

**Moment 1 — attacking the spec, not writing it**

- *What I asked for:* I pasted my draft Tool Inventory into Claude and asked
  it to try to break the spec — "could someone build these from this alone,
  without asking me anything?" — rather than to write it or improve it.
- *What came back:* It flagged two gaps. First, `search_listings` said
  "returns the matches" without saying what shape a match was, so a builder
  wouldn't know whether `price` was a float or a string. Second, I had said
  `suggest_outfit` "handles the empty wardrobe" without saying what that
  meant — return `""`? raise? return a generic blurb?
- *What I changed:* I rewrote both bullets. For `search_listings` I listed
  every field in the returned dict. For `suggest_outfit` I committed to
  "general styling advice (categories, colors, silhouettes) when `items ==
  []`, not `""` and not an exception," and then wrote the tool against that
  line. The branch in the loop reads cleaner because the tool's contract is
  specific.

**Moment 2 — stress-testing the size filter**

- *What I asked for:* I showed Claude the sizes in `data/listings.json`
  (`S/M`, `M/L`, `US 9`, `W30 L30`, `XL (oversized)`) and asked what would go
  wrong if I used a plain Python `in` substring check for size matching.
- *What came back:* It pointed out `"s" in "us 9"` is `True` and `"l" in
  "xl"` is `True`, so asking for an S-size top would return the US-9 shoes
  and asking for L would return XL — a silent correctness bug that looks
  like a bad search. It suggested tokenising both sides on `/`, whitespace
  and parens and comparing the resulting sets.
- *What I changed:* I wrote `_size_matches` to do exactly that, and added
  the token-match contract into the Tool Inventory so the behaviour is
  something the next-unit grader can test for — "M matches S/M but not XL,
  US 9, or W30" is a check you can turn into a one-line assertion.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
