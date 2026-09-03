# Steps 14.5–16 (cite-check, polish, readability, verify) — live-run operational lessons

Source: full-tier run, Giethoorn koopbeslissing report (168 cite-pairs → 30 findings,
band 2.500-4.000 words, max_concurrent_children=1).

## Cite-check (14.5): false "dangling" from unindexed notes

- New notes written via write_file must carry the FULL frontmatter schema BEFORE `hpr sync`:
  `title`, `id`, `tags` (list), `created` (ISO), `vault_tag`, `type: note`, `content-type`,
  `status`, `source`, `deprecated: false`. Notes missing `title`/`created`/`type: note`
  silently DON'T get indexed → citecheck reports their wikilinks as "dangling" even though
  the file exists on disk. Fix: repair frontmatter → `hpr sync -j` → re-run
  `hpr citecheck extract <tag> -j`. Dangling count 4 → 0.
- `citecheck extract` expects the report at `research/notes/final_report_<vault_tag>.md`.
  If the report filename is shorter than the vault_tag, symlink it:
  `ln -sf final_report_<short>.md research/notes/final_report_<vault_tag>.md`.
- Findings file is `cite-check-findings.json` (bare JSON array; dict with "findings" also accepted).
  Typical yield: ~1/6 of pairs become findings (30 of 168), split ~6 critical / 10 major / 14 minor.

## Second patcher pass: orchestrator-direct (no subagent)

When the step-14 patcher already burned its iteration budget, apply cite findings YOURSELF:
one Python heredoc with a list of (old, new) tuples, print applied/missed counts.
28–30 findings ≈ one script + 1–2 follow-up patches for non-verbatim misses. Log the pass
in a `second-patcher-pass-log.md` (orchestrator notes file) for the run trace.

Finding classes to expect and their fixes:
- **Unverified contact data**: report phone numbers were the WRONG party (085-0201028 was the
  Camperbox makelaar, not BusinessParc!). Remove numbers → "nummer via de projectpagina".
- **Yield/band conflicts**: report band (~11,8% bij VVE €600) conflicted with the official tax
  note (10,4-10,9%). Replace with the note's numbers + point the wikilink at the note.
- **Claims not in the cited note**: soften to "bij bezichtiging verifiëren" / "opvragen bij de
  beheerder" or mark "(aanname)" — never delete the claim outright.
- **Fiscal/legal claims not in vault**: keep but mark "laat de accountant bevestigen" (honest,
  still useful to the reader).
- **Wrong numbers**: Hooidijkhof netto-yield 4,4% → 4,3% (cite-check caught a real error).
- **Stale quotes**: report quote missed words the source note has ("bedoeld voor werkzaamheden"
  vs "bedoeld voor het verrichten van werkzaamheden") — copy verbatim from the note.

## Verify gate: the two checks that bite after step 14

- `cite-check-resolved`: if cite-check-findings.json contains criticals, a file named
  `cite-check-patch-log.json` MUST exist — a DIFFERENT file from patch-log.json (verify greps
  for the exact name). Write it with total_findings/critical_findings/applied/skipped/conflicts/summary.
- `quote-integrity`: every "quoted span" must appear verbatim in SOME vault note. Fixes:
  - user-prompt quotes ("anders is het weggegooid geld") → create a small context note carrying
    the verbatim words (`opdrachtcontext-<topic>` note, type: note, content-type: context);
  - paraphrase quotes ("afwachten wordt vanzelf goedkoper") → italics or de-quote;
  - price-tag quotes ("vanaf €21.900" vs note's "EUR 21.900") → de-quote.
  - Re-run verify after fixes; count must drop to 0.
- Note: verify's length-in-range is 2.000-5.000 ±20% — LOOSER than the wrapper band
  (2.500-4.000). The wrapper band is the real constraint; check it with `wc -w` + your own script.

## Step 15 (polish) — subagent hang → orchestrator take-over

- The polish-auditor subagent can produce ZERO tool activity for 30+ minutes (initial reads done,
  then silence). With max_concurrent_children=1 it blocks the delegation pool: later delegations
  either queue or run synchronously. Do NOT wait indefinitely — after ~20-25 min of a frozen
  live-log (unchanged mtime), take over.
- Compression pass done by orchestrator: 60+ (old, new) replacements in ONE Python heredoc is
  the efficient shape (vs dozens of patch calls). Techniques: drop filler adverbs ("daarmee",
  "echter"), tighten ("i.p.v.", "OVB", ">10%", "was €140"), merge adjacent same-topic paragraphs,
  bold key numbers (0 word cost), delete cross-section recaps that repeat an earlier paragraph.
- **Boundary effects**: fixes can ADD words (exact-quote repairs +2, "Het label" +2) and push you
  back over the band max. Run `wc -w` after every batch; micro-trim to ≤ band max (e.g. drop
  "in het dorp").
- Log the take-over honestly: polish-log.json applied = your compression entries,
  escalations = "subagent produced no edits in N minutes; orchestrator performed pass".

## Step 16 (readability) — recommender failure → orchestrator audit

- The recommender can die on model semaphore timeouts (llama-cpp "SEMAPHORE_TIMEOUT",
  exit_reason max_iterations) — especially when the pool is blocked by an earlier hang.
- If the report already has tables/lists/bold (usually does by this point), the audit is small:
  merge-paragraphs + bold-keyterms only; most categories legitimately "not recommended".
- Write BOTH `readability-recommendations.json` (your assessment incl. not_recommended list) and
  `readability-decisions.json` (applied/skipped) — the run trace expects both artifacts.

## Curation after the run (CLAUDE.md requirement)

- Loop `hpr note list -j`, filter notes by vault_tag, `hpr note update <id> --status evergreen`
  for every run note still in review; add `--summary` to newly created notes; then
  `hpr repair -j`, `hpr sources score -j`, `hpr graph rank -j`. All 20 run-notes went review→evergreen
  in one loop, plus 3 new notes got summaries.
