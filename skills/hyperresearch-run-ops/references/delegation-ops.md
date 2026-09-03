# Delegation ops for hyperresearch runs (Hermes)

Operational lessons from full-gear runs on this Hermes instance (2026-08-16,
run `workspace-giethoorn-buy-69ce53`, 16/16 steps, 3 draft-orchestrators +
synthesizer + 4 critics via delegate_task).

## Sequential spawn under max-1-concurrent children
The step skills (e.g. hyperresearch-10-triple-draft, hyperresearch-12-critics)
say "spawn all in parallel in ONE message". THIS environment caps
`delegation.max_concurrent_children` at 1, so parallel fan-out silently
serializes. Do it explicitly instead of fighting the runtime:
1. Dispatch ONE `delegate_task` per subagent (loci-analyst, draft-orchestrator,
   critic, synthesizer, patcher, ...).
2. Wait for the "[ASYNC DELEGATION BATCH COMPLETE]" message — that IS your go
   signal to dispatch the next child.
3. Never stack multiple dispatches in one message: extras are dropped/queued
   and you lose the completion signal.

Measured: draft-orchestrators took ~7-18 min each; 3 drafts ≈ 35 min
sequential; critics ~7-10 min each. Budget the run accordingly.

## Draft-orchestrator leaf contract (worked 3/3)
The prompt structure that produced uniformly good, self-verifying drafts:
- **Context field:** vault_tag, "stap N <rol>", workdir, CLI PATH export
  (`export PATH="~/.local/bin:$PATH"`), "geen nieuwe fetches, geen
  vault-survey — alleen de MUST-READ-lijst", output language (Nederlands).
- **Goal field:** pipeline position; verbatim research query (gospel); THE
  ANGLE with the specific position to defend and the concrete arguments to
  work out; exact input file paths; the MUST-READ note-ID list with
  "lees ELKE note via `hpr note show <id> -j`"; literal H2 headings in order;
  word-count band (2000-5000, mik ~3000); wikilink citation style with
  "gebruik ALLEEN échte note-IDs, verifieer ze; verzin niets"; "neem cijfers
  letterlijk over uit evidence-digest.md"; output path via write_file; and
  self-verification gates (bestanden bestaan / H2's letterlijk in volgorde /
  woordenaantal in band / 0 hits op verboden vocabulaire / alle wikilinks echt).
- Lesson from draft A: the evidence-digest's abbreviated cite-IDs were NOT
  valid note IDs — the subagent caught it and cited real IDs itself. Always
  pre-empt this in the prompt: children WILL emit plausible-but-fake [[ids]]
  from shorthand unless told to verify.

## Validate outputs on disk, not via the summary
After each subagent returns, run the same gates yourself (seconds each):
```bash
wc -w <output> && grep -n "^## " <output>
grep -o "\[\[[a-z0-9-]*\]\]" <output> | sort -u | tr -d '[]' > /tmp/wl.txt
while read id; do [ -f "research/notes/$id.md" ] || echo "ONBEKEND: $id"; done < /tmp/wl.txt
grep -ci "hyperresearch\|evidence digest\|locus\|committed" <output>   # expect 0
```
Batch-complete summaries get TRUNCATED in the delivery message
("[SUMMARY TRUNCATED]" / head+tail). The file on disk is authoritative —
read/grep it directly. Live transcripts:
`$HOME/cache/delegation/live/deleg_<id>/task-0.log` (tail -5 to spot-check
progress while a child runs).

## hpr CLI quirks (this instance)
- `hpr note show <id> -j` HANGS (timeout) on non-existent IDs — check
  `test -f research/notes/<id>.md` instead.
- `hpr note new` batch registration printed `"timestamp": ... } 0 notes`
  (parsing artifact) while the notes WERE created — confirm with
  `hpr note list --tag <tag> -j`, never trust the counter.
- `hpr note list -j` returns `{"data": [...]}` — index `d['data']` in python.
- `--content-type listing` is unsupported; only `article`.

## Wait-time discipline
Sequential subagent runs leave 5-20 min gaps. Use them: load the NEXT step
skill, write the next step's artifacts (synthesis plan / outline / conflicts,
orchestrator-notes for the critics), read the finished drafts for the step-11
conflict-check. The run finishes roughly 1.5-2× faster than idle-waiting.

## Cross-draft conflict resolution (step 11.2)
When drafts disagree on a number (e.g. Kulturhus 110 vs 109 m²), the SOURCE
NOTE decides: `hpr note show <id> -j` and locate the figure. Record verdicts
in `temp/synthesis-conflicts.md`; the synthesizer prompt then carries them as
"bindend" commitments so pass 2 can't re-introduce the wrong figure.
