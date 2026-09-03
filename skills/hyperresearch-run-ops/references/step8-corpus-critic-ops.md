# Step 8 corpus-critic gap-fill (pre-draft, orchestrator-run)

Step 8 asks "what source, if found, would overturn the current direction?" and
fills the most dangerous gaps BEFORE drafting (cheapest intervention point —
corrections before drafting cost nothing; after drafting they require patches).
Ran cleanly 2026-08 on a real-estate / market-viability study as the
ORCHESTRATOR + ONE gap-fill fetcher (delegation cap-1). Load this alongside the
`hyperresearch-8-corpus-critic` step skill (which owns the WHAT; this owns the
operational HOW on Hermes).

## Author the gaps yourself, don't spawn a critic subagent

Write `corpus-critic-gaps.json` directly from the committed positions +
comparisons tensions. Classify each gap:

- `type: overturning` — a source that would flip a committed position. Highest
  priority (e.g. "the parcel's bestemming turns out to be wonen-only", "a rural
  coworking precedent proves the demand thin/real").
- `type: strengthening` — verifies an occupancy/rate assumption (e.g. "the
  60-70% break-even occupancy assumption" vs. the gemeente's actual 60% norm).
- `type: independent-verification` — corroborate a load-bearing single-source
  figure.

Per gap fields: `id`, `type`, `priority` (`critical`/`high`), `target_position`
(what it would change), `search_queries` (2-4 concrete queries), `source_type`,
`rationale` (tie it to the position). A gap with no rationale is not worth a fetch.

**For a real-estate / location / permit study, the single most dangerous gap is
almost always verifying the exact `bestemmingsplan` bestemming of the specific
parcel — do NOT assume the broker's listing description ("Kantoor") matches the
plan.** That check overturned an assumption this run (the 1e verdieping was
formally wonen-only; commercial use required a planologische afwijking), and it
materially changed the verdict.

## Dispatch ONE gap-fill fetcher (cap-1)

Per-gap search queries + a hard fetch cap (~8-10 new fetches total) + the
instruction to write `temp/corpus-critic-results.md` in a per-gap format:

```markdown
## <gap-id>
- searched: <what>
- found: <note ids + 1-line key finding, or 'none'>
- effect on committed position: <overturns|strengthens|no-change + why>
```

The delegation summary truncates — read the results .md file, not the summary.

## Search-engine fallback ladder (this env)

Bing / Ecosia / Mojeek are frequently blocked or polluted (support.google.com
legal-troubleshooter pages, wikipedia). **DuckDuckGo Lite via web_extract** was
the reliable path across all three gaps this run. Wikipedia 403s `hpr fetch` —
use web_extract directly.

## planviewer.nl / ruimtelijkeplannen.nl: bot-blocked HTML, but PDFs work

The plan HTML pages 403. Workaround that worked: curl the plan PDFs directly

```
curl -sL "<planviewer file URL>" -o /tmp/plan_t.pdf
```

The `_r_` / `_t_` / `_v_` variants (regels / toelichting / verbeelding) resolve
to real PDFs even when the HTML directory 403/404s. Extract with pymupdf
(`uv run --with pymupdf python -c "..."`) and grep for the parcel/street + the
bestemming wording. This run the smoking gun was the toelichting line
*"op de verdieping(en) is alleen de functie wonen toegestaan"*. Wikipedia's
Rijksbeschermd-gezicht page (web_extract) resolves the beschermd-dorpsgezicht
boundary + year + ha — distinguish what the dorpsgezicht restricts (physical
changes: gevels/kappen/bijgebouwen ≤50 m²) from what it does NOT restrict
(function) — the bestemming is usually the harder blocker.

## Triage results honestly

A `critical` overturning gap that corrects an assumption is a WIN, not a failure.
Append a "Stap 8 corpus-critic resultaten" section to comparisons.md stating:
what it overturned, which positions it strengthens, and the net effect on
confidence (the two poortwachters are now the stichting AND the gemeente/planologie).
No overturning source found = the position gains confidence — say so explicitly.

## PDF extraction path + the scanned-PDF drop decision

- Default `python3` here has NO fitz → use `uv run --with pymupdf python -c "..."`.
  curl the PDF first, then pymupdf to text, then grep.
- Scanned/image-only PDFs yield `total_text_chars = 0` / `PAGE0_CHARS = 0`.
  Before OCR, decide if the single figure is worth it: OCR-ing a 30-page scan
  for ONE benchmark number is usually NOT — substitute the real comparables
  already in the corpus and mark the figure unverified. (Distinct from the
  open-access substitution path for thin DOI/abstract pages.)
