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

**Moment 3 — unit 4 was carried out by Claude Code; here is what it checked**

- *What I asked for:* I asked Claude Code to finish the unit 4 milestones in
  this repo and push them. It wrote the MCP registration, ran the failure
  modes and both eval runs, and drafted the README sections.
- *What it got wrong, and caught:* Its first diagnosis said five 503 misses,
  all in `create_fit_card`. When it re-scored the run with a script instead of
  reading it, the real numbers were six misses split three-and-three between
  `suggest_outfit` and `create_fit_card`. It also noticed the After run had no
  503s at all, so the improvement could not be credited for the 25/25, and it
  tested the change directly with an injected 503 instead.
- *What I changed:* The README diagnosis was corrected to match the logs, and
  the "Did it help" section says the improvement is mechanism-verified but not
  proven on a real run. **I should add my own notes here about what I
  reviewed or disagreed with; this entry only records what the tool did.**

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

Produced by `run_eval.py::main` on 2026-10-13 at 18:32,
cache off, temperature 0.9, 97 model calls across 55 runs. Full file at
[results/run_2026-10-13_1832_before.md](results/run_2026-10-13_1832_before.md).

Criterion 4 maps to five scenarios (one per item) and criterion 5 to two,
so there are 11 rows below. Each scenario still gets its own target: for
criterion 4 the row target is "produces a fit card mentioning its price once,
5 of 5 tries", and the across-items "no shared opening sentence" check is
done underneath the table from Try 1 of each row. Criterion 5's "10 of 10"
is the sum of the two rows' tries.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. matching query completes | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. impossible query stops early | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. state carries through | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4a. fit card — slip dress ($30) | 5 of 5 | PASS | PASS | PASS | PASS | FAIL | MISSED (4/5) |
| 4b. fit card — platform sneakers ($48) | 5 of 5 | PASS | PASS | PASS | FAIL | FAIL | MISSED (3/5) |
| 4c. fit card — cargo pants ($27) | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4d. fit card — band tee ($19) | 5 of 5 | PASS | PASS | FAIL | PASS | PASS | MISSED (4/5) |
| 4e. fit card — denim jacket ($42) | 5 of 5 | PASS | PASS | FAIL | PASS | FAIL | MISSED (3/5) |
| 5a. price ceiling — jacket < $40 | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5b. price ceiling — tee < $20 | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

A try is scored PASS if the full loop finished and the fit card mentions the
item's price once (criteria 1, 3, 4a–4e), if the branch stopped the loop
before `suggest_outfit` (criterion 2), or if every item in `search_results`
has `price <= max_price` (criteria 5a–5b). A try is scored FAIL if any one
of those is false; in this run every FAIL came from the model returning a
503 UNAVAILABLE partway through, surfaced correctly by the
`ModelUnavailable` handler.

**The across-items check for criterion 4** — Try 1 fit cards, item by item,
produced by [tools.py::create_fit_card](tools.py#L153):

- 4a slip dress ($30.0, depop) → *"Found the absolute holy grail on depop
  for just $30.0! 😍 This 90s silk slip dress has the dreamiest floral
  print…"*
- 4b platform sneakers ($48.0, poshmark) → *"Scored these chunky white
  Platform Sneakers on poshmark for just $48.0 and I am officially in my
  90s streetwear era."*
- 4c cargo pants ($27.0, poshmark) → *"Unlocked peak 2000s streetwear
  energy with these khaki cargos for just $27.0 on Poshmark!"*
- 4d band tee ($19.0, depop) → *"Still obsessing over how perfectly
  beat-up this faded grey vintage band tee is."*
- 4e denim jacket ($42.0, poshmark) → *"Found the ultimate layering piece
  on Poshmark for just $42.0!"*

Five distinct openings, no two share a sentence; every card mentions its
own price exactly once. The "5 items, no shared opening + price once"
part of criterion 4 is MET on this set. What missed is the per-row 5-of-5
completion rate.

**Real output from one try**, Try 1 of criterion 1 — fit card produced by
[tools.py::create_fit_card](tools.py#L153), full trace from
[agent.py::run_agent](agent.py#L99):

```
Found the ultimate 2000s butterfly tee on depop for just $18.0 and I am
officially living my best early-2000s pop star life. ✨ It's giving major
mall-rat nostalgia, especially styled with baggy denim and chunky sneakers.
Absolutely obsessed with this thrifted gem! 🦋

[1] parse_query
      in:  vintage graphic tee under $30
      out: dict with keys: description, size, max_price
[2] search_listings (via MCP)
      in:  dict with keys: description, size, max_price
      out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
[3] select_item
      out: Y2K Baby Tee — Butterfly Print ($18.0, depop)
      →    first result wins
[4] suggest_outfit
      in:  dict with keys: item
      out: **Outfit 1:** Pair the Y2K Baby Tee with the baggy straight-leg jeans and chunky white sneakers for a classic,…
[5] create_fit_card
      in:  dict with keys: item
      out: Found the ultimate 2000s butterfly tee on depop for just $18.0 and I am officially living my best early-2000s …
```

---

## Verdicts and Diagnoses

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | Full three-tool run returns a fit card | 4 of 5 | **MET (5/5)** | All 5 tries of the matching-query scenario completed, each producing a non-empty `fit_card` string. The 4-of-5 target was set in Unit 3 to cover a bad-keyword run; it didn't come up here. |
| 2 | Empty search stops before `suggest_outfit` | 5 of 5 | **MET (5/5)** | All 5 tries of the impossible-query scenario set `session["error"]`, trace shows the branch step and no `suggest_outfit` step. Deterministic, as predicted. |
| 3 | State carries the found item to the next tool | 5 of 5 | **MET (5/5)** | All 5 tries selected "90s Track Jacket — Navy/White Stripe" and the outfit and card were written about it. I then checked the criterion literally: ran the real loop 5 times with the two model tools stubbed to record their input, and `selected_item["id"]` (`lst_004`) equalled the id passed to `suggest_outfit` 5 of 5 times. |
| 4 | Fit card differs per item + price mentioned once | 5 of 5 per row | **MISSED (overall 19/25)** | Row-level: 4a 4/5, 4b 3/5, 4c 5/5, 4d 4/5, 4e 3/5. The across-items check — 5 openings, no shared sentence, each card mentions its own price once — PASSED on Try 1 of the five items. What missed is the per-row completion rate, and every miss was a 503 UNAVAILABLE from the model. |
| 5 | Price ceiling respected | 10 of 10 | **MET (10/10)** | Row 5a: 5/5 tries, every search_results listing had `price <= 40`. Row 5b: 5/5 tries, every listing had `price <= 20`. Totalled: 10 observations of the price filter, 10 respected the ceiling. |

**Diagnoses**

Only one criterion missed, and the misses all have the same shape.

**Criterion 4 — six misses, one mechanism.** Across the five criterion-4
scenarios, six of 25 tries ended early with "The model couldn't be reached:
Couldn't reach the model: 503 UNAVAILABLE … 'This model is currently
experiencing high demand.'" (slip dress try 5; sneakers tries 4 and 5; band
tee try 3; denim jacket tries 3 and 5). The agent handled every one of them
correctly — `ModelUnavailable` was caught in
[agent.py:193-197](agent.py#L193-L197) and the user saw a readable message,
not a stack trace. These are not a prompt bug, a tool bug, a branch bug, or a
state bug. The failing place is the model call itself, and the miss is a
retry gap in [generate.py::generate](generate.py), not in either tool's logic.

**Step.** Three of the six died on `suggest_outfit` (step 4 — the trace stops
right after `select_item`: slip dress try 5, sneakers try 4, denim try 3) and
three died on `create_fit_card` (step 5 — the trace stops right after
`suggest_outfit`: sneakers try 5, band tee try 3, denim try 5). So it is not
one tool; it is whichever model call happened to land on a 503.

**Mechanism.** In the pre-change retry loop (`generate.py`, lines 299-341 at
commit 5f12825), the `rate_limited` flag only fired on 429, "resource
exhausted" or "rate limit". A 503 UNAVAILABLE matched none of those, so it
fell through to `raise ModelUnavailable(_explain(exc))` on the first attempt
with no retry — even though the service's own message says "Spikes in demand
are usually temporary. Please try again later." That is a retriable error
being treated as terminal.

**Pattern.** One problem, not six: every miss is the same unhandled 503 on
the same code path, spread over two tools. Slip dress, sneakers, band tee and
denim jacket were each hit at least once; cargo pants and the other criteria
(1, 2, 3, 5) were not, which says the failures track when Gemini was busy,
not anything about those queries.

**A deviation I should flag.** Criterion 4 as written in unit 3 says to run
`create_fit_card` on each of 5 items "with the same outfit string". My
scenarios instead run the whole loop per item, so each card is conditioned on
a different model-written outfit. That makes the 5-of-5 completion rate a
measure of the whole pipeline's availability, not just the fit-card prompt.
I kept the original wording unchanged in `criteria.md` and am reporting the
deviation here rather than rewriting the criterion after the fact.

**Everything I expected to miss, didn't.** The 4-of-5 target on criterion 1
was set to cover casual phrasings; the one query I tested there happened to
tokenise well. The 5-of-5 on criterion 2 is deterministic by construction
and held. Criterion 3's state check was a safeguard against a failure that
didn't materialise. And criterion 5's filter is a single `>` on a float,
which held across 10 queries. The one surprise is that criterion 4 missed
for infrastructure reasons rather than for the prompt-quality reasons I'd
written the criterion to catch.

---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path** — `python app.py ask 'vintage graphic tee under $30' --trace`,
produced by [agent.py::run_agent](agent.py#L99) with trace calls from
[trace.py::step](trace.py#L41). The MCP call is step 2.

```
[1] parse_query
      in:  vintage graphic tee under $30
      out: dict with keys: description, size, max_price
[2] search_listings (via MCP)
      in:  dict with keys: description, size, max_price
      out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
[3] select_item
      out: Y2K Baby Tee — Butterfly Print ($18.0, depop)
      →    first result wins
[4] suggest_outfit
      in:  dict with keys: item
      out: **Outfit 1:** Pair the Y2K Baby Tee with the baggy straight-leg jeans and chunky white sneakers for a classic,…
[5] create_fit_card
      in:  dict with keys: item
      out: Obsessed with this little butterfly tee I just scored on depop for only $18.00! It’s giving major Y2K nostalgi…
```

**Empty search** — `python app.py ask 'designer ballgown size XXS under $5' --trace`.
Visibly shorter: step 3 is the branch, not `select_item`, and steps 4 and 5
never run.

```
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: dict with keys: description, size, max_price
[2] search_listings (via MCP)
      in:  dict with keys: description, size, max_price
      out: [] (empty)
[3] branch
      →    search returned empty — stopping before suggest_outfit
```

**Failure-mode messages, as the user sees them**

The three handlers from this unit, triggered on purpose. Each message names
what broke and what the user can try.

- *Empty search* — handler in [agent.py:139-155](agent.py#L139-L155), set on
  `session["error"]`:

  ```
  No listings matched 'designer ballgown size XXS under $5'. Try raising the
  price above $5; loosening the size filter (you asked for XXS); using fewer
  or different keywords.
  ```

- *Empty wardrobe* — `python app.py ask 'denim jacket under $50' --empty-wardrobe`.
  Fallback in [tools.py:119-128](tools.py#L119-L128). The agent does **not**
  stop; it returns general styling advice for the item on its own:

  ```
  Pair this cropped jacket with high-waisted black wide-leg trousers or a
  floral midi skirt to balance the proportions. Layer it over a fitted white
  ribbed tank top or a graphic baby tee. Finish the look with chunky leather
  loafers or retro canvas sneakers.
  ```

- *Model unavailable* — one character of `GEMINI_API_KEY` flipped in `.env`,
  then a novel query (`'checkered flannel shirt in size L'`) so the build
  cache can't serve it. Handler in [agent.py:198-202](agent.py#L198-L202):

  ```
  The model couldn't be reached: The model rejected your API key. Check
  GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com..
  Check your GEMINI_API_KEY in .env, then try again.
  ```

  Key restored after the run.

**On the MCP move:**

The code change was small and local. `mcp_server.py` registers one tool —
`search_listings` — with a description that promises an empty-list return on
no match and names units on `max_price`. In `agent.py`, the direct
`search_listings(...)` call in `run_agent` is now `call_tool("search_listings",
{...})`, and an `MCPError` branch sits beside the existing `ModelUnavailable`
one so a server crash produces the same shape of readable session error. The
trace step is relabelled `search_listings (via MCP)` so the MCP hop is
visible in step 2 of every run.

Nothing behaved differently afterwards. I checked by calling
`search_listings(...)` directly and `call_tool("search_listings", {...})` with
the same arguments and comparing the lists: `direct == mcp`, same length, same
dicts, same key order. The list of dicts round-trips through FastMCP's JSON
unwrapping with no key or type changes, which is what the rubric's "the call
changes shape, the return value does not" is asking about.


---

## The Improvement

**What I changed:**
Three lines in [generate.py:325-340](generate.py#L325-L340). The retry loop
inside `generate()` previously only recognised 429 and "resource exhausted"
and "rate limit" as retriable. I added an `overloaded` check that triggers
on `"503"` or `"unavailable"` in the exception text, and routed that through
the same backoff path as a rate-limit push-back. The log line now reads
`[model overloaded]` instead of `[rate limit]` when the retry is for a 503
specifically, so the real cause is visible in the eval log.

**Which failure it was meant to fix:**
The five criterion-4 misses in the Before run, all of them 503 UNAVAILABLE
from Gemini on the `create_fit_card` call. The diagnosis named this as a
transient server-side load issue that the service itself tells you to
retry, and the code was treating it as terminal on the first attempt. The
change is the minimum one that makes the retry loop match what the service
is actually telling us.

### Run Log — After

Produced by `run_eval.py::main` on 2026-10-13 at 18:51, same 11 scenarios,
cache off, temperature 0.9, 100 model calls across 55 runs, run after the
`generate.py` change. Full file at
[results/run_2026-10-13_1851_after.md](results/run_2026-10-13_1851_after.md).
Same scoring rules as the Before log.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. matching query completes | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. impossible query stops early | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. state carries through | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4a. fit card — slip dress ($30) | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4b. fit card — platform sneakers ($48) | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4c. fit card — cargo pants ($27) | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4d. fit card — band tee ($19) | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4e. fit card — denim jacket ($42) | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5a. price ceiling — jacket < $40 | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5b. price ceiling — tee < $20 | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

Every fit card was checked by script, not by eye: the item's price appears
exactly once in all 25 criterion-4 cards (and in every card that exists in
the Before log), and the Try 1 cards for the five items have 5 distinct
opening sentences in both runs.

Real output from one try (criterion 4b, Try 4 — the same slot that was a 503
failure in the Before log), from
[tools.py::create_fit_card](tools.py#L153):

```
Finally scored these chunky white platform sneakers on Poshmark and I am obsessed. Total 90s streetwear energy that instantly elevates the baggy jeans and grey crewneck combo. Can't believe I grabbed them for just $48.0! 👟✨
```

**Did it help, and how do I know:**
The measured result went from 19/25 to 25/25 on criterion 4, but I can't
credit the change for that. The After run logged zero `[model overloaded]`
retries, which means no 503 happened at all: the service simply wasn't
overloaded this time, so the new code path never ran in the real eval. The
honest reading of the before/after table is "same code path, calmer service".

What I can show is the mechanism, separately. I fed the old `generate()`
(commit 5f12825) and the new one the same fake client that raises a 503 on
the first call and succeeds on the second:

```
OLD generate.py (commit 5f12825): raised ModelUnavailable after 1 call(s): Couldn't reach the model: 503 UNAVAILABLE. ...
NEW generate.py (HEAD):           returned 'recovered' after 2 call(s)
```

So the change does what the diagnosis said it should (a single transient
503 is now survived instead of ending the run), but whether it would have
lifted the real 19/25 is untested. To measure that properly I'd need to
re-run the eval during a busy period, or repeat it enough times to catch a
few 503s.

---

## What's Still Broken

No criterion is missed in the After run, but that is a weaker statement than
it sounds. Things I know are still wrong or unproven:

- **Criterion 4's pass is unproven, not earned.** See "Did it help" above.
  What I'd do: re-run the eval at a busier time (or ten tries instead of five)
  until a real 503 occurs inside a run and confirm it recovers. I stopped
  because the unit allows one change and I had already spent it; I did not
  want to keep re-running until the number looked good.
- **Persistent 503s still crash the agent.** I injected a client that always
  returns 503. After the 5 retries `generate()` raises a plain `RuntimeError`
  ("Still rate limited after 5 attempts ... your key is fine"), and
  `agent.py::run_agent` only catches `ModelUnavailable` and `MCPError`, so the
  error escapes `run_agent` entirely (confirmed by running it). The user would
  see a raw `RuntimeError`, and the wording "rate limited ... key is fine" is
  wrong for an overloaded service. Fix: have `generate()` raise
  `ModelUnavailable` when retries run out on a 503. I did not do it, because
  it is a second change and this unit allows one; the Milestone 2 handler
  therefore only covers the bad-key case, not an extended outage.
- **Criterion 1's target (4 of 5) may have been too low.** It passed 5/5, and
  I also tried the casual phrasings the target was written to worry about:
  `"a tee that's giving old-school vibes"` returns 7 results and `"something
  cozy for fall"` returns 2. I only scored one query for criterion 1, so I
  can't claim more. I'd tighten it to 5 of 5 across 5 different phrasings
  (including casual ones) next time.
- **Criterion 4 is measured at the wrong altitude.** Written as "same outfit
  string, 5 items"; scored here by running the full loop. The deviation is
  described under Diagnoses. A cleaner version calls `create_fit_card`
  directly with a fixed outfit string and takes the model-availability
  question out of the picture.
- **Criterion 5's two scenarios aren't 10 independent queries.** Search is
  deterministic, so five tries of one query return the same list five times.
  The ceiling check passed on every returned listing, but the breadth is two
  queries, not ten. More distinct queries would be the honest version.
- **MCP cost.** `mcp_client.call_tool` starts and stops the server on every
  call, which is slow but was fine for this unit.

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
