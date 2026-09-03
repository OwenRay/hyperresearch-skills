# Light-tier shortcut path quirks (2026-08-31 managed-AI-market run)

Light tier routes 1 → 2 → single draft (10, light path) → 15 → 16. Lessons from
the first live light run (27 sources, market assessment for a managed AI
assistant service).

## Delegation

- Both parallel fetcher batches dispatched in ONE delegate_task call did NOT run
  in parallel this time — the second call timed out at 420s but the subagent
  still started and completed fine in the background (confirmed via
  `delegate_task action='list'` + the `[ASYNC DELEGATION BATCH COMPLETE]`
  message). Don't re-dispatch on a dispatch-timeout; check the list first.
- Batch-complete summaries get head+tail-TRUNCATED in delivery ("Showing N chars
  (head) + M chars (tail)…"). The full summary is at
  `$HOME/cache/delegation/subagent-summary-0-<timestamp>.txt` — read it with
  read_file before acting on key facts (the omitted middle held 8 of 10 facts).
- Search lane that worked for fetchers: `web_extract` on
  `https://lite.duckduckgo.com/lite/?q=<urlencoded>` (fallback: duckduckgo.com/html,
  bing.com). Some targets 403 (wealthytent, toolify); skip, don't escalate.

## Verify gate on a light run

- `length-in-range` is enforced against the decomposition's `response_format`,
  NOT the tier's typical pairing: light + `structured` = 2000-5000 words ±20%.
  The first draft at 1,116 words failed. Budget the single draft at ~1,800+
  words when the decomposition says `structured`; expand from vault detail
  (local pricing landscape, concrete unit/token math, per-source numbers)
  rather than re-classifying.
- `artifact:polish-log.json` is a verify CHECK for every run — even a light run
  that never spawned a polish-auditor. Pre-create in the run dir:
  `{"applied": [], "escalations": []}`.
- quote-integrity scanning is regex-based on `"` spans (≥8 chars): it counts
  rhetorical/scare quotes, brand names and report titles ("AI agency",
  "Ambitie of aarzeling?", "AVG-compliant · EU-only data") as verbatim
  citations. Pre-scan before the final verify:
  `re.findall(r'"([^"\n]{8,})"', report)` and de-quote EVERY framing span;
  keep quotes only for genuine verbatim source text anchored in a vault note.
  13 quote spans → 8 errors on this run; zero after one sweep.
- `hpr run verify -j` truncates quote-integrity detail to "first: …" — for the
  full list, scan the report yourself with the regex above.

## Draft-authoring pattern that passed

Direct orchestrator-authored single draft (no subagent) citing `[[note-id]]`
wikilinks, built from `hpr note show <id> -j` batch dumps (parse `d['data']`,
strip `<untrusted-source>` tags with regex, print body[:1400] per note to read
the key content within context budget). Then targeted patch edits to expand
length and de-quote, re-running verify after each pass.
