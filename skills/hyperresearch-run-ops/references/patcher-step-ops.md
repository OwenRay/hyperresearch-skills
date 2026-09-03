# Patcher step (14) — live-run operational lessons

Source: full-tier run on the Giethoorn koopbeslissing report (24 critic findings, 4 critic
JSONs, wrapper band 2.500-4.000 words, pass 2 < pass 1 = 3.747).

## Word-count trajectory (the blowout and the recovery)

- Pass-1 draft: **3.747 words** (`wc -w`).
- After applying all 24 finding hunks (mandatory d1/d2/d3, depth p1-p6, width w1-w6,
  instruction i1-i6): **4.966 words** (+1.219, ~+33%).
- Recovery to the band required a dedicated compression pass: ~15 patch batches of small
  exact-string trims across every section (intro, object descriptions, yield block,
  10-jaarsmodel, tegenkant bullets, planologie, VVE, fiscaal, kernaanbeveling, beslisboom,
  actielijst). Techniques that worked:
  - Per-line word counts (`python3 -c` splitting on lines) to locate fat paragraphs.
  - Delete whole redundant paragraphs (a duplicated 80 m² explainer; a "Conclusie:" recap
    sentence that repeated the conditional advice two paragraphs up).
  - Merge duplicated claims: pandgroei-nuance appeared twice (10-jaarsmodel + boxen-sectie);
    keep one, point the other.
  - Tighten attribute lists ("airco en internet; toegangshek; sandwichpanelen Rc > 4,5,
    LED-verlichting" → "24/7-toegang, camerabeveiliging en lift").
  - In-hunk trims only — never delete finding content; polish (step 15) still audits.

**Lesson: write finding hunks LEAN from the start** (~30-50 words of new text per finding at
most), trim inside the same hunks, and run `wc -w` after every batch with a running budget.
Do not assume the final compression pass will be painless — it is most of the work.

## Patch-anchor discipline (8 failures in a row)

Every failed patch this session shared one cause: `old_string` was written from the intended
text (draft plan / memory / stale read) instead of the file's current bytes. The tool's
fuzzy matcher does NOT rescue a wrong string; the loop-warning fires after ~3 failures.

- Copy `old_string` verbatim from a fresh `read_file` taken AFTER the last edit to that file.
- Keep anchors short — long anchors get truncated in transit (your own call shows
  `...[truncated]`); a truncated parameter cannot match.
- On "Could not find a match": re-read, copy exact, apply once. Do not retry variations.
- Escalate to the Node-fs bypass (see `robust-file-edit` skill) only for escape-drift /
  multi-match / repetitive-content failures, never for a stale anchor.

## Batching and the iteration-limit cut-off

The patcher step is long: ~40-60 patch calls for 24 findings + compression. It fits the
tool-iteration budget ONLY if hunks are batched:

- 5-8 independent patches per parallel tool-call block (different text regions — safe).
- Measure (`wc -w`) after each batch, not after each hunk.
- **Fill `patch-log.json` and run the final verification EARLY** (after all finding hunks,
  before or during compression). This run got cut off by the iteration limit with
  `patch-log.json` still a stub and the word count ~700 over band; the orchestrator had to
  finish. Handoff state must state: which findings applied (all 24 here), what remains
  (patch-log fill, final wc), and the last measured count.

## Duplicate-claim merge

Two findings often fix the same spot (here: d3 exit-nuance + w4a liquiditeitsclaim; d1
huurwaarde + i4 gevoeligheid). Apply once, log BOTH ids in `applied`. A second overlapping
sentence reads as redundancy and gets flagged by the step-15 polish auditor.
