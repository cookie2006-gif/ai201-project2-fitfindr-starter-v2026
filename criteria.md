# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, a sentence or two on **why that target** and not a stricter
one.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
`search_listings` is a plain keyword-overlap score with a short stopword list
and a tokenised size match. Phrasings like "a tee that's giving old-school
vibes" tokenise into very few content words, and if none of them appear in the
listing's title, description, style_tags, colors or brand, that query will
miss. I expect that to bite at least one time in five with casually-worded
queries, so 5 of 5 would be dishonest. 4 of 5 says the keyword tool is good
enough for the usual case while admitting the one it isn't.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
This path is deterministic. `search_listings` doesn't call the model, so there
is no run-to-run variation to blame — either the branch fires on an empty list
or it doesn't. The branch itself is one `if not session["search_results"]:` in
`agent.py::run_agent`, so there's no scoring, no prompting, nothing stochastic
in the way. Anything short of 5 of 5 would be a code bug I should fix rather
than a target I should relax.

---

## 3. State carries the found item through to the next tool

For 5 of 5 happy-path runs, the listing `id` in `session["selected_item"]`
matches the listing `id` that was passed into `suggest_outfit` on that same
run. Checked by printing both and comparing the strings — not by trusting that
they look the same in the output.

**Why this target:**
This should be 5 of 5 because the session is a plain dict and I control both
the write (step 3 of the loop) and the read (step 4). The reason it's a
criterion at all is that a state failure doesn't *look* like a state failure
in the final output — it looks like a bad outfit suggestion, and I'd blame
the prompt. The id-comparison test is the thing I'd run if the fit card ever
reads like it was written about a different item.

---

## 4. The fit card is actually different for different items

Pick 5 different listings. Run `create_fit_card` on each with the same outfit
string. The 5 resulting cards share no identical opening sentence, and each
mentions its listing's price exactly once.

**Why this target:**
A fit card calls a model with `temperature=0.9`, so the same input will vary
run to run — that's not a bug, it's the tool. What would be a bug is a
template-y opening ("Just scored this amazing find on…") that reads the same
no matter what the item is, or a prompt that forgets to anchor on the price.
"No shared opening sentence across 5 items" and "price mentioned once" are
both things I can grep for without reading five captions carefully, which is
the point — a criterion I won't bother to run isn't a criterion.

---

## 5. The price ceiling is actually respected

For 10 random queries that each include a `max_price`, every listing in
`session["search_results"]` has `price <= max_price`. 10 of 10 runs.

**Why this target:**
Filtering numbers is not something I want to be wrong about even a little —
"$30 or less" meaning "sometimes $45" is the one failure a user would
immediately notice and lose trust over. The filter is a single comparison in
`search_listings`, so 10 of 10 is the right target: anything less than that is
a bug, and I'd rather find it with this check than by a user complaining that
the agent lied about the price.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
