---
name: hyperresearch-run-ops
description: >-
  Use when running hyperresearch V8 runs.
version: 1.0.0
author: Nous Research
license: MIT
platforms: [linux]
---

# Hyperresearch Run Operations (Hermes)

The `hyperresearch` step skills (hyperresearch-1-decompose ... -16-readability-audit,
plus `hyperresearch-browser-fetch`) are a third-party V8 port (jordan-gibbs, ported
by OwenRay, MIT). They are authoritative on WHAT each step does. This skill is a
curator-owned companion that captures the OPERATIONAL lessons of actually running
them on Hermes — the gotchas, the false-positive triage, and the discipline that
gets a run cleanly across the finish line. Load it alongside the router/step skills.

Support file: `references/delegation-ops.md` — spawning subagents under the
max-1-concurrent-children cap (sequential, batch-complete message = go
signal), the draft-orchestrator leaf-contract prompt structure that worked
3/3, the filesystem output-validation loop (wc/grep/wikilink-existence),
`hpr` CLI quirks (note-show hangs on bad IDs, note-list `data` key), and
wait-time discipline for the 5-20 min sequential gaps.

Support file: `references/patcher-step-ops.md` — step 14 (patcher) live-run lessons: the
word-count blowout (3.747 → 4.966 after 24 finding hunks; recovery trims), the exact-anchor
patch discipline (8 in-a-row failures from non-verbatim old_strings), batching 5-8 hunks per
parallel block, filling patch-log.json EARLY so an iteration-limit cut-off doesn't strand the
run, and duplicate-claim merging (two findings, one hunk, both ids logged).

Support file: `references/post-patch-steps-ops.md` — steps 14.5-16 live-run lessons: the
cite-check false-dangling trap (write_file notes need FULL frontmatter — title/created/type:note
— or `hpr sync` silently skips them), the orchestrator-direct second patcher pass (30 findings
in one Python (old,new)-tuple heredoc), the verify-gate surprises (`cite-check-patch-log.json`
is a SEPARATE file from patch-log.json; quote-integrity scans quoted spans verbatim against the
vault), the polish-auditor hang → orchestrator take-over pattern (~20-25 min frozen live-log =
take over; a hung subagent blocks the whole delegation pool at max_concurrent_children=1), and
the readability-recommender semaphore-timeout fallback.

## Stuck-subagent take-over (steps 14-16)

Subagents in the tail steps (patcher, polish-auditor, readability-recommender) can hit the tool
iteration cap or freeze with a dead live-log, and with `delegation.max_concurrent_children=1`
one stuck child blocks every later delegation (they queue or run synchronously). Take-over
trigger: live-log mtime unchanged ~20-25 min (post-reads silence), or a batch-complete summary
that says "not finished". The orchestrator then performs the step directly — compression,
second patcher pass, readability audit — using ONE Python heredoc of (old, new) tuples per pass
(40-60 replacements) instead of individual patch calls, `wc -w` after every batch to guard the
wrapper band (watch boundary effects: quote repairs can ADD words), and honest escalations
entries in the step logs (patch-log/polish-log/readability-decisions) so the run trace shows
who did what. A late-arriving result from the frozen subagent must be re-validated, not trusted.

## The binding ship gate: `hpr run verify` — not `hpr lint`

- **`hpr run verify <vault_tag>` is the ONLY gate that decides shippable.** It
  runs 15 checks (report-exists, required-headings, length-in-range, citation-density,
  no-scaffold-leak, quote-integrity, retracted-citations, all artifact files,
  cite-check-resolved). Target `passed: True`, not "all steps marked done".
- **`hpr run finish <vault_tag>` is the ONLY way to flip the run from
  `status: running` to `done`.** verify passing + all 16 steps `done` is NOT
  enough — the manifest stays `running` until finish runs (it re-verifies, then
  prints `SHIPPED — run status: done`). Diagnostic: `hpr run resume` returning
  `next_step: null` with `remaining_steps: []` and all steps done means finish
  is the missing action. Output gotcha: with `-j` the finish data envelope is
  nearly empty (`status: None`, `passed: None`) — the 15 check lines print to
  STDOUT as human text; parse the stdout, not the JSON envelope. User asking
  "probeer te hervatten" on a fully-done run = run finish, nothing else.
- **`hpr lint` is ADVISORY, not the ship gate.** It surfaces two classes of
  false-positive noise that you should triage and dismiss, not "fix":
  - `entity-coverage`: flags prompt-decomposition entities as "missing from the
    final report" via STRICT LITERAL substring match. Paraphrased coverage is
    legitimate — e.g. the report's "single small PCB" legitimately covers the
    decomposition's "small simple PCB board". Check each term with grep before
    acting; forcing the literal decomposition strings in hurts readability.
  - `missing-summary` warnings: curation hygiene (add summaries later), not a
    report ship-gate issue.
- **After ANY edit pass (patcher, cite-fix, polish, readability) re-run verify.**
  Expect it to newly fail quote-integrity (see below) — that is the normal
  end-state, not a surprise. Iterate de-quote -> verify until `passed: True`.

## quote-integrity: rhetorical quotes are false positives; de-quote, don't memoize

The quote-integrity check flags any quoted span not found verbatim in a vault
note. Report writers routinely wrap FRAMING language in scare quotes (e.g.
"does the economics work at a small maker's volume", "which SKU and how fast").
These are the report's own words, NOT source text.

- **The fix is to REMOVE the quotation marks** (or rephrase to drop the quotes),
  not to write a memo explaining why the quote is fine. The gate will keep
  failing until the quotation marks are gone.
- A polished/readability pass frequently introduces new scare-quote instances.
  After the final readability apply, grep the report for `"` spans and de-quote
  the rhetorical ones before the last verify.
- Command: `hpr lint --rule quote-integrity --json` lists every flagged span;
  the verify gate truncates to "first N". Use the lint rule to see all of them.
- **Genuine verbatim quotes (user-prompt words, plan-definitions) need a vault
  ANCHOR note, not de-quoting.** When the report quotes the user's own words
  ("anders is het weggegooid geld", "Geen waardeverlies, geld moet er later weer
  uitkomen") or a legal definition, create a small `opdrachtcontext-<topic>.md`
  note holding the verbatim text — FULL frontmatter (id/title/tags/created, same
  requirement as step-13 notes or `hpr sync` skips it), `hpr sync`, cite it.
- **Matches are CHARACTER-EXACT.** "EUR 21.900" ≠ "€21.900" fails; a report
  quote missing one word ("is bedoeld voor werkzaamheden" vs the note's "is
  bedoeld voor het verrichten van werkzaamheden") fails. Fix by aligning the
  report text to the note text byte-for-byte (copy the note's wording), then
  re-verify. Batch-check all spans at once: python `re.findall(r'"([^"]{8,})"')`
  over the report, membership-test each against concatenated vault text, print
  ✓/✗ per span.

## cite-check: distinguish parse artifacts from genuinely mangled ids

`hpr citecheck extract <vault_tag>` emits `dangling` pairs. Triage them by
inspecting the JSON, NOT by trusting the flag count:

- **Parse artifact (NOT a real problem):** a dangling entry whose `note_id` is
  `null`/`None` and `citation` is `?` comes from the extractor failing to split
  a sentence with MULTIPLE adjacent `[[note-id]]` citations separated by
  em-dashes/parentheses (e.g. `...[[tailscale-pricing]], ZeroTier [[zerotier-...]]`).
  The trailing markers get reported as dangling. Verify each cited id resolves
  via `hpr note show <id>` — if they all resolve, this is noise.
- **Genuine mangled id (REAL problem):** a dangling entry whose `note_id` is a
  non-null but TRUNCATED id that does NOT resolve (e.g. `[[zerotier-pricing]]`
  vs. the vault's real `zerotier-pricing-plans-find-the-right-network-plan-for-you`).
  Fix by `replace_all` of the broken `[[id]]` -> full `[[full-id]]` across the
  report, then RE-EXTRACT. A correct fix drops dangling to 0.
- **Comprehensive mechanical check:** after fixing, extract ALL distinct
  `[[note-id]]` markers from the report (`grep -oE '\[\[[a-zA-Z0-9_-]+\]\]' ... | sort -u`)
  and `hpr note show` each one. This catches every mangled id in one pass —
  but be careful to copy the FULL id (trailing `_on_raspberry_pi`-style suffixes
  are easy to truncate by hand and produce false "missing" verdicts).

## Subagent tool-lock stubs (create BEFORE dispatch)

- **Patcher (step 14) is tool-locked to Read+Edit — it CANNOT Write files.** It
  must write `patch-log.json`, so the ORCHESTRATOR pre-creates the stub:
  `{"total_findings": 0, "applied": [], "skipped": [], "conflicts": [], "orchestrator_escalated": []}`.
  Dispatch the patcher with the stub path + a quote-integrity rule in the contract
  ("never fabricate quotes; de-quote paraphrases").
- **Patcher dispatch contract (proven on 24 findings):** the goal lists every
  findings JSON path (patcher reads them itself — don't paste all findings inline),
  PLUS: the NEW gap-fetch note paths from step 13 (they are not in evidence-digest —
  without explicit paths the patcher never sees OZB/co-working data), a verbatim
  summary of each `critical` finding so they cannot be skipped silently, and a
  per-critic one-line map of which findings address what (dialectic d1-d6, depth
  p1-p6, width w1-w6, instruction i1-i6). Tell it to verify every finding against
  the canonical query and log rejects in `skipped` with reasons.
- **Tool-lock phrasing that held:** the contract opened with "JE BENT TOOL-GELOCKT:
  ALLEEN read_file en patch" and closed with the required report-back shape
  (applied/skipped/escalated per critic). Works in Dutch or English; the lock must
  name the exact tools, not just say "Read+Edit".
- **Polish-auditor (step 15) is also Read+Edit.** Pre-create `polish-log.json`
  stub (`{"applied": [], "escalations": []}`) before dispatch.
- **Readability-recommender (step 16) is Read+Write** — no stub needed; it writes
  its own JSON recommendations file.
- **Cite-checker (step 14.5) gets NO shim** per the router skill.

## Delegation discipline: cap-1 sequential spawning + file-based handoff

This environment caps `delegate_task` at ONE concurrent child. Batching 2+ tasks
in a single call fails with a ~208-char "Max 1 concurrent child" error. Applies
to every ensemble step: loci-analysts (step 4), draft-orchestrators (step 10 —
A, then B, then C), fetchers, critics (step 12).

- **Spawn strictly sequentially**: one `delegate_task` call per subagent; the
  result re-enters the conversation when it finishes — only then dispatch the next.
- **Leaf subagents write outputs to EXPLICIT files** (loci-a.json,
  temp/interim-*.md, temp/draft-*.md) rather than relying on the summary text.
  Pass the output path in the task goal; poll for existence with
  a bounded wait loop (`for i in 1..N`, sleep 10 between checks, break when the artifact file exists; N ~ 30-60).
- **Live transcripts** stream to
  `$HOME/cache/delegation/live/<delegation_id>/task-0.log` — tail this early
  to verify a subagent started correctly (right cwd, hpr PATH export) instead of
  waiting blind for completion.
- **Every subagent context needs the env bootstrap**: `cd ~ (project root)` and
  `export PATH="~/.local/bin:$PATH"` — fresh sessions don't inherit
  them, and the first `hpr note show` will fail without them.
- **Tell subagents to use ABSOLUTE `$HOME`-prefixed paths** in read_file/write_file
  calls, not relative ones. A critic reported "relative paths werkten niet; opgelost
  door $HOME-prefix" — the subagent's own cwd is not the run workspace, so
  `research/notes/...` silently misses even after the bootstrap cd.
- **Critic spawn contract (worked 4/4 on step 12):** each critic goal carries — the
  verbatim query (or query file path), pipeline position ("you are step 12, critic N/4;
  step 11 produced the final report"), inputs (draft_path, its own output_path,
  vault_tag, and the interim notes to read for depth), the register directive from
  `shims/critics.md` (register=analyze: commitment-checks), a task paragraph naming
  the focus areas (e.g. depth: 10-jaarsmodel, netto-yield-opbouw, verwarmings-
  berekening, planologie, beslisboom-compleetheid), and the exact output JSON schema
  with 3-6 findings. Post-return: parse the JSON with python3 (severity counts),
  read the FULL findings file before dispatching the next critic.
- Triple-draft (step 10): pre-write `temp/draft-angles.md` (3 distinct angles:
  strongest-thesis / steelman-contrarian / synthesis-reconciler when tensions
  exist, else breadth/depth/practitioner) + one curated must-read source list per
  angle (`temp/draft-{a,b,c}-source-list.md`, 20-50 ids, interim notes in ALL
  three). Include the verbatim query + the angle + the exact output path in each
  goal. Validate all 3 drafts exist and are non-trivial before step 11.
- **Draft citation contract:** evidence-digest.md cite-ids are often SHORTENED
  (e.g. `fundainbusiness-businessparc-meppel-project`) and do NOT exist as vault
  notes. Tell every draft subagent: verify each `[[id]]` against
  `research/notes/` on disk and cite ONLY ids that resolve — the filesystem check
  also avoids the `hpr note show` hang on bad ids.
- **Post-return draft QA (run on all 3):** word count in range (`wc -w`),
  required H2s present in order (`grep -n "^## "`), zero pipeline vocabulary
  (`grep -ci "hyperresearch\|evidence digest\|locus\|committed"` must be 0),
  and every wikilink resolves (extract with `grep -oE '\[\[[a-zA-Z0-9_-]+\]\]' |
  sort -u | tr -d '[]'`, then `[ -f research/notes/<id>.md ]` per id). One
  command battery: `scripts/verify_draft.sh` (`tr -d '[]'`, not `sed` — sed's
  empty-alternation `s/\[\[\|//g` fails to strip `]]`).
- **Wait-time pipeline:** with cap-1 spawning each draft takes ~8 min. Use the
  draft-C window to pre-build ALL step-11 inputs: read drafts A+B, resolve any
  numeric conflict against source bodies (`hpr note show -j` + regex context
  extraction from `d['data']['body']`), write synthesis-conflicts.md /
  synthesis-plan.md / synthesis-outline.md. The synthesizer then spawns the
  moment draft C lands instead of after a dead 10-minute gap.

## Orchestrator fallback when subagents fail (depth + fetch steps)

Depth-investigators and fetchers can die on SPA/browser-heavy sources (e.g.
ruimtelijkeplannen.nl planviewer, Google captcha) — iteration limits, blocked
fetches. The proven fallback in this environment:

- **The orchestrator takes over the depth work itself**: read the locus from
  loci.json, fetch via web_extract, escalate blocked searches to the Mac-Chrome
  CDP browser (see hyperresearch-browser-fetch), write `temp/interim-<topic>.md`
  with the committed position, and register it in the vault via
  `hpr note new "Interim: <topic>" --body-file <path> --tag <vault_tag> --content-type article --status review -j`.
- Mark the step done only after ALL loci have interim notes in the vault.
- This deviates from the router's "no step work yourself" by design: a stuck
  subagent costs more than the orchestrator doing the bounded work directly.

## Step 13 gap-fetch: detect, fetch, log (orchestrator-run)

Step 13 is cheap to run entirely as the orchestrator — no subagent needed. The proven loop:

1. **Detect gaps mechanically:** for each critic finding that hints at a missing topic
   (e.g. width-critic "periodieke lasten ontbreken", "co-working niet genoemd"), run
   `hpr search "<topic-term>" --tag <vault_tag>`. **Empty output = 0 notes = confirmed gap.**
   `hpr search` prints NOTHING (no JSON envelope) on zero hits — that silence IS the signal.
2. **Fetch each gap** (max ~2 per wave keeps the patcher load sane): web_extract first
   (official gemeente/GBLT pages beat COELO aggregators — COELO is navigation-heavy and
   recaptcha-walled). When Google blocks web_extract, get result URLs via Mac-Chrome CDP
   (`node drive.mjs "https://www.google.com/search?q=..."` then regex-extract hrefs,
   filtering out google/gstatic domains), then web_extract the result URLs directly.
3. **Author the note** with write_file into `research/notes/<slug>.md` — full YAML
   frontmatter (`vault_tag`, `type: source`, `content-type: article`, `status: review`,
   `source: <url>`) + body that ends with a "Relevantie" section stating how the data
   changes the report's numbers (yield-druk ~0,8-1,4%-punt etc.). Then `hpr sync` so the
   index sees it.
4. **Log the wave** to `research/runs/<vault_tag>/post-critic-fetch-log.md`: per gap —
   which finding demanded it, what was fetched, the new note id, and a "niet-fetch-worthy"
   list (findings solvable from existing vault data, with the reasoning). The patcher
   needs this to know which findings now have fresh ammunition.
5. Close with `hpr run step <vault_tag> 13 --status done -j`.

Worked pattern 2026-08: 2 gaps (OZB/waterschapslasten Meppel — official meppel.nl page
gave exact 2026 tariffs; co-working scan — flexwerkplek.nl extracted cleanly and settled
"geen co-working in Giethoorn zelf"). Both new notes were cited by the patcher with
`[[note-id]]` wikilinks.

## hpr CLI quirks (cost real time — know these)

- `hpr note list -j` returns `{"ok": true, "data": [...]}` — NOT `{"notes": [...]}`.
  Parse `d['data']`. Same shape for most list/show commands; probe once with
  `json.dumps(d)[:300]` before writing a parser (guessing the key fails twice).
- `hpr note show <id> -j` nests the note at `d['data']` TOO — body text lives at
  `d['data']['body']` (NOT `d['body']`), with title/path/summary as siblings.
  `d.get('body')` silently returns None and costs a round-trip; probe the envelope
  first (`print(list(d.keys()))`).
- `hpr note show` HANGS (no timeout) on a non-existent id — never poll it for
  verification. Check `research/notes/<id>.md` on disk first (`[ -f ... ]`),
  then show. This is also why draft/critic subagents should verify cite-ids via
  the filesystem, not via `hpr note show`.
- `hpr note new --content-type listing` is REJECTED — use `--content-type article`
  (candidate hpr bug; `--body-file` and `note update` DO work, `note rm` works).
- Evidence digest (step 9) with no claims-*.json files: fetchers that wrote
  notes directly produce no claim files. Build evidence-digest.md from the
  interim notes + run artifacts (comparisons, source-tensions, corpus-critic
  results) instead — 30+ claims for full tier is achievable from notes alone.

## Applying readability recommendations (step 16)

The recommender emits a JSON list of recommendations (type: remove-hr,
break-paragraph, split-sentence, bold-keyterms, make-table, make-list), each with
`current` and `recommended` fields. The ORCHESTRATOR applies them selectively:

- **Apply confidently:** all `remove-hr`, `make-list`, `make-table`, and
  high-priority `break-paragraph`/`bold-keyterms`.
- **Apply with judgment:** high-priority `split-sentence` (genuinely long
  paragraphs); skip medium `split-sentence` that would hurt rhythm.
- **Skip:** `make-table` where prose is fine (fewer than ~3 comparable items),
  low-value bolds.
- **Mechanical apply:** drive the `current`->`recommended` replacements via a
  small Python script (read the JSON, replace each pair, count hits). The
  `current` fields are verbatim so replacements are exact.
- After applying, watch for two side effects: (a) a make-table edit may leave a
  now-redundant framing sentence beside the new table intro — delete the
  duplicate; (b) new scare quotes may appear — de-quote before verify.

## HTML + Drive delivery (no pandoc / python-markdown on the box)

- There is no `pandoc` and no `python markdown` module by default. Generate a
  clean styled self-contained HTML with `scripts/report_to_html.py` (handles the
  report's markdown subset: `#/##/###`, `**bold**`, `*italic*`, `[[note-id]]`
  rendered as muted `[source]` chips, pipe tables, `-` lists, numbered lists,
  `---` rules). Run: `python3 report_to_html.py <in.md> <out.html>`.
- **Google Drive Rule 1 (google-workspace skill): confirm with the user BEFORE
  uploading / replacing / sharing.** Present the choice (new file vs. replace the
  prior live file) and the file list found via `drive search` before pushing.
- Drive auth + upload path: `python $HOME/.hermes/skills/productivity/google-workspace/scripts/google_api.py`.

## Pipeline-tail checklist (full tier, steps 11-16 + ship)

1. Synthesizer (step 11) writes final report in two passes, negative delta.
2. 4 critics (step 12) -> findings JSONs; spawn SEQUENTIALLY (delegation cap is 1)
   or author directly — never batch them in one call.
3. Gap-fetch (step 13) — log UNFILLED gaps so the patcher acknowledges them.
4. Patcher (step 14) — pre-create patch-log stub; apply findings; scrub
   pipeline vocabulary ("the corpus", "vault_tag", "draft A says") -> natural prose.
5. Cite-check (step 14.5) — triage dangling (artifact vs. mangled); fix + re-extract.
6. Polish (step 15) — negative char delta; re-verify.
7. Readability (step 16) — apply selectively; de-dupe table intro; de-quote.
8. `hpr run verify` -> passed: True. Then `hpr run finish`. Then curation pass
   (add note summaries, `hpr repair`, `hpr sync`).
9. Delivery: HTML -> confirm with user -> Drive upload.

## Pitfalls

- **Trusting `hpr lint` errors over `hpr run verify`.** Lint has entity-coverage
  and missing-summary false positives. The verify gate is the truth.
- **Marking a step "done" without re-running verify after edits.** Every edit
  pass can reintroduce quote-integrity failures; verify is the only way to know.
- **Truncating note-ids by hand** during the "verify all cited ids" sweep produces
  false "missing" verdicts (e.g. dropping `_on_raspberry_pi`). Copy ids verbatim.
- **Letting the patcher/polish subagents Write** — they can't. Pre-create stubs.
- **Trusting a batch-complete summary's counts over the output file.** A
  late-arriving cite-checker summary claimed 30 findings; the findings JSON held
  34. Reconcile against the file (python severity Counter), correct the
  audit-trail log (second-patcher-pass-log.md) — subagent summaries are
  self-reports, the file is truth. Re-validate ANY late result from a frozen
  subagent before trusting it (already the rule for stuck take-overs).
- **Band-boundary word counts (≤4.000 while sitting at 4.000-4.021):** after the
  big compression passes, finish with single-word micro-cuts ("scoort hier goed"
  → "scoort goed"). When a python replace misses but grep finds the text, the
  strings differ invisibly (em-dash —, unicode €, non-breaking space) —
  diagnose with `sed -n '<line>p' | od -c | head -8` and copy the exact bytes
  into the replacement tuple. Re-check `wc -w` after EVERY micro-cut; quote
  repairs and de-quote edits shift counts both ways.
- **Uploading to Drive without user confirmation.** Ask first.
