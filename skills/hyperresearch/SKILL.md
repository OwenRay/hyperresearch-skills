---
name: hyperresearch
description: >-
  Deep research via the HYPERRESEARCH V8 architecture — a tier-adaptive 16-step
  pipeline (light / full) that scales from a ~30-minute light-tier answer to an
  adversarially-audited report. This entry skill is a ROUTER/orchestrator.
  It bootstraps canonical inputs (research_query, vault_tag, scaffold) and
  sequences each step skill in order. Each step's instructions live in its own
  skill file (hyperresearch-1-decompose through hyperresearch-16-readability-audit)
  and are loaded fresh via skill_view when you invoke them. Use when the user
  asks for thorough, sourced, multi-perspective research (a topic survey, a
  literature synthesis, a comparison with recommendations, or an adversarial
  deep-dive).
version: 8.0.0-hermes-port
author: jordan-gibbs (ported to Hermes by OwenRay)
license: MIT
---

# Hyperresearch V8 — multi-skill chain orchestrator (Hermes port)

You are the orchestrator. Your job in this conversation is:
1. Read this file once at the start.
2. Bootstrap canonical inputs (research_query, vault_tag, scaffold, run workspace).
3. Invoke each step skill in sequence via `skill_view(name="hyperresearch-N-...")`.
4. Between steps, do nothing except mark todos and (optionally) write notes to
   `research/runs/<vault_tag>/temp/orchestrator-notes.md`.

You do NOT do the work of any step yourself. The step skills do. You just sequence them.

## Setup (one-time environment bootstrap)

If this is the first run on a new machine, or any prerequisite is missing, run
this bootstrap before anything else. It is idempotent — skip items that pass.

1. **CLI check.**
   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   hyperresearch --version   # or: hpr --version
   ```
   If missing, install the CLI (it is a normal PyPI package):
   ```bash
   uv tool install hyperresearch      # preferred
   # fallbacks: pipx install hyperresearch
   #             python3 -m pip install --user hyperresearch
   ```
   Verify: `hyperresearch --version` prints a version ≥ 0.10.0.

2. **Step-skill check.** The pipeline needs the 20 companion skills
   `hyperresearch-1-decompose` … `hyperresearch-16-readability-audit` (plus
   half-steps and `hyperresearch-run-ops`). Check with `skills_list` /
   `hermes skills list`. Install any missing ones from the tap:
   ```bash
   hermes skills install OwenRay/hyperresearch-skills/hyperresearch-1-decompose
   # …repeat for each missing step skill, or add the whole tap once:
   hermes skills tap add OwenRay/hyperresearch-skills
   ```

3. **Browser escalation (optional).** The `hyperresearch-browser-fetch` skill
   needs SSH access to a Mac with a debuggable Chrome (`$REMOTE_HOST`,
   `$REMOTE_USER`, an SSH key). Without it, JS-SPA / bot-walled fetches simply
   fail — degrade to abstracts and note the gap; do not block the run on it.

4. **Vault check.** `hyperresearch run status -j` should succeed (empty is fine)
   — this confirms the vault directory is writable.

If any bootstrap item fails, tell the user exactly which one and stop — do not
silently proceed with a degraded pipeline.

---

## Platform note (READ BEFORE RUNNING)

This skill was originally authored for **Claude Code**. Three constructs have
been translated to Hermes primitives:

| Upstream (Claude Code) | Hermes equivalent |
|---|---|
| `Skill(skill: "hyperresearch-N-stepname")` | `skill_view(name="hyperresearch-N-stepname")` — load the step's SKILL.md, then execute its procedure |
| `subagent_type:` / `Task(...)` spawns | `delegate_task(goal=..., context=...)` — spawn a subagent. Pass the full rendered prompt as the goal/context. |
| `$HPR` / `hyperresearch` CLI | Native. The `hyperresearch` PyPI package is installed; `hpr` / `hyperresearch` is on PATH at `~/.local/bin` (prepend to PATH if needed: `export PATH="~/.local/bin:$PATH"`). Every referenced subcommand exists (`run`, `note`, `search`, `fetch`, `citecheck`, `levers`, `vault-tag`, `profile`). |
| **Real browser (fetch escalation)** | `hpr fetch` / `web_extract` / `curl` run from the local Linux host and fail on JS SPAs, bot-walls, and 403s. For those, escalate to the **remote Mac's real Chrome** via the `hyperresearch-browser-fetch` skill: it launches headless Chrome on `$REMOTE_HOST` (user `$REMOTE_USER`, SSH key configured) and drives it over CDP through an SSH tunnel. The Mac is reachable now and a headless Chrome binds port 9223 cleanly (verified 2026-08-02). |

Step files contain the literal `<< hpr >>` token in command snippets — substitute the real binary (`hpr` or `hyperresearch`) there. If `hpr` is not on PATH, use the full path `~/.local/bin/hpr`.

The step skills were pre-rendered with the **`full` gear** numbers from
`src/hyperresearch/core/profiles.py` (source_target=55–80, depth_budget_total=40,
loci_max=6, draft_count=3, claims_cap=80–120, gap_fetch_cap=5, etc.). To change the gear,
edit those constants in the step files or ask the user for a different profile.

---

## How the chain works

Each pipeline step is its own skill. To run a step, load it with `skill_view`:

```
skill_view(name="hyperresearch-N-stepname")
```

When you load it, that step's full procedure is in your context. Execute its
procedure, hit its exit criterion, then return here to invoke the next step.

**Why this design?** Context compaction. Pre-rendering each step keeps the
orchestrator lean: only the current step's procedure is in context.

### The 16 step skills

| # | Skill name | What it does | Tiers |
|---|---|---|---|
| 1 | `hyperresearch-1-decompose` | Canonical query → scaffold + decomposition + coverage matrix + tier classification | all |
| 1.5 | `hyperresearch-1-5-chapter-partition` | Partition atomic items into 4–10 chapters; steps 2–10 loop per chapter | dissertation (skip on Hermes unless user requests) |
| 2 | `hyperresearch-2-width-sweep` | Multi-perspective search plan + parallel fetcher waves | all |
| — | `hyperresearch-browser-fetch` | **Supporting skill** — real-browser fetch escalation (remote-Mac Chrome over CDP) for JS SPAs / bot-walls / 403s that `hpr fetch` can't reach | all |
| 3 | `hyperresearch-3-contradiction-graph` | Pair contradictions across the corpus into ranked fight clusters | full |
| 4 | `hyperresearch-4-loci-analysis` | 2 loci-analysts → scored loci.json with source budgets | full |
| 5 | `hyperresearch-5-depth-investigation` | K depth-investigators in parallel → interim notes with committed positions | full |
| 6 | `hyperresearch-6-cross-locus-reconcile` | Reconcile committed positions → comparisons.md | full |
| 7 | `hyperresearch-7-source-tensions` | Extract expert disagreements → source-tensions.json | full |
| 8 | `hyperresearch-8-corpus-critic` | "What source would overturn this?" + targeted gap-fill fetch | full |
| 9 | `hyperresearch-9-evidence-digest` | Top claims + verbatim quotes → evidence-digest.md | full |
| 10 | `hyperresearch-10-triple-draft` | Per-angle source curation + 3 parallel draft-orchestrators (3 angle-specific drafts) | all |
| 11 | `hyperresearch-11-synthesize` | Synthesis plan + outline + spawn synthesizer subagent (two-pass write) → final_report.md | full |
| 12 | `hyperresearch-12-critics` | 4 adversarial critics in parallel → findings JSONs | full |
| 13 | `hyperresearch-13-gap-fetch` | Conditional fetcher wave to fill critic-identified gaps | full |
| 14 | `hyperresearch-14-patcher` | Patcher subagent applies critic findings as Edit hunks | full |
| 14.5 | `hyperresearch-14-5-cite-check` | Verify each citation supports its sentence | full |
| 15 | `hyperresearch-15-polish` | Polish-auditor (Read+Edit) hygiene + readability pass | all |
| 16 | `hyperresearch-16-readability-audit` | Readability-recommender → JSON suggestions; orchestrator applies selectively | all |

---

## Tier routing

Step 1 classifies the query into `pipeline_tier` (`light` / `full`). The tier is
written to `research/runs/<vault_tag>/prompt-decomposition.json`. After step 1,
**read that file** to learn the tier, then sequence steps:

| Tier | Steps that run | Typical time |
|------|---|---|
| `light` | 1 → 2 → 10 (single draft) → 15 → 16 | ~30 min |
| `full` | 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14 → 14.5 → 15 → 16 | ~2–4 hours |

**RESPECT THE TIER GATE.** When step 1 classifies a query as `light`, do NOT run
the skipped steps "just to be thorough." If uncertain, tier up — but never
silently upgrade every query to `full`.

---

## Bootstrap (do this once at the start)

1. **Establish the canonical research query.**
   - If the user gave an explicit research brief, use it verbatim (minus wrapper contract).
   - Otherwise, use the user's verbatim prompt as the canonical research query.
   - Extract wrapper requirements separately: required save path, citation format,
     terminal-section shape. These are binding but NOT part of the query.
   - If `research/wrapper_contract.json` exists, read it.

2. **Mint a unique vault tag.** Produce a short topical slug (3–5 lowercase
   hyphen-separated words, e.g. `efield-dft-sac`). Then:
   ```bash
   export PATH="~/.local/bin:$PATH"
   hpr vault-tag <slug> --json
   ```
   Parse the `vault_tag` field (the CLI appends a random 6-hex suffix, unique
   across all prior runs). Result e.g. `efield-dft-sac-a3f9b7` is the canonical
   vault_tag for the rest of the pipeline.

2.5. **Initialize the run workspace.**
   ```bash
   hpr run init <vault_tag> --profile <full|light> --json
   ```
   Pass `--budget <usd>` if the user set a spend ceiling. This scaffolds
   `research/runs/<vault_tag>/` (with `temp/`) and writes `run.json` — the run
   manifest. **The manifest is your durable memory**: record every step transition
   with `hpr run step <vault_tag> <N> --status running|done -j` as you go.

3. **Persist the query file.** Write the verbatim canonical query to
   `research/runs/<vault_tag>/query.md`:
   ```markdown
   ---
   vault_tag: <slug>
   created: <ISO-8601 timestamp>
   source: prompt.txt | user-prompt
   ---

   <verbatim query text, character-for-character>
   ```
   This file is the **canonical research query (GOSPEL)** — every step cites it.

4. **Classify modality** (collect / synthesize / compare / forecast) — record in
   the scaffold. Calibrates step 10's drafting style:
   - **collect**: enumerative coverage, per-entity sections with named fields
   - **synthesize**: defended thesis with evidence chains
   - **compare**: proportionate per-entity depth + a committed recommendation
   - **forecast**: predictive claims grounded in past + present, explicit time horizon

5. **Write the scaffold.** `research/runs/<vault_tag>/scaffold.md` (private
   planning doc — MUST NOT appear in the final report). Include:
   - User Prompt (VERBATIM — gospel)
   - Run config (vault_tag, query_file_path, modality, wrapper requirements)
   - Modality classification rationale
   - Tier rationale (filled in after step 1)
   - Wrapper requirements (save path, citation format, terminal sections)

6. **Seed the todo list.** Create todos for the steps using integer step numbers:
   - `Step 1 — skill_view: hyperresearch-1-decompose` ... through Step 16.
   The todo list survives context compaction; it's your durable memory of where you are.

7. **Invoke step 1:** `skill_view(name="hyperresearch-1-decompose")`.

After each step's exit criterion is met, mark its todo complete, log
`hpr run step <vault_tag> <N> --status done -j`, and move to the next.

---

## Four canonical rules (ALWAYS in force)

1. **NEVER EMIT BARE TEXT WHILE TASKS ARE RUNNING.** While subagents (via
   `delegate_task`) are in flight, keep working — do not end your turn with a
   text-only message that would terminate the run. After spawning, await results
   and continue.
2. **THE QUERY IS GOSPEL.** Every step's recover-state section tells you to
   re-read `query.md`. Do it. Drift from the canonical query is the most common
   failure mode.
3. **LOG EVERY STEP TRANSITION** via `hpr run step <vault_tag> <N> --status done -j`.
   The manifest is your recovery path if context is compacted.
4. **RESPECT TIER GATES.** Skipped steps are skipped for a reason (product
   decision, not laziness). Do not "helpfully" run them.

---

## Recovery: if you wake up uncertain where you are

Context compaction may eat parts of this conversation. If unsure what step you're on:
0. **Read the run manifest FIRST.** `hpr run resume <vault_tag> --json` (or with no
   tag for the newest run) returns the exact next step and the skill invocation to
   continue with.
1. **Check the TodoWrite list.** It carries integer step numbers and survives compaction.
2. **Check disk artifacts (fallback).** Each step writes a canonical artifact:
   - Step 1: `scaffold.md`, `prompt-decomposition.json`, `temp/coverage-matrix.md`
   - Step 2: vault notes tagged with vault_tag (`hpr note list --tag <vault_tag> --all -j`)
   - Step 3: `temp/contradiction-graph.json`, `temp/consensus-claims.json`
   - Step 4: `loci.json`
   - Step 5: notes with `type: interim`
   - Step 6: `comparisons.md`
   - Step 7: `temp/source-tensions.json`
   - Step 8: targeted gap-fill notes
   - Step 9: `temp/evidence-digest.md`
   - Step 10: `draft-a.md`, `draft-b.md`, `draft-c.md` (or `final_report_<vault_tag>.md` for light)
   - Step 11: `final_report_<vault_tag>.md`
   - Step 12: `critic-findings-*.json`
   - Step 13: gap-fill notes
   - Step 14: patched `final_report_<vault_tag>.md`, `patch-log.json`
   - Step 14.5: `cite-check-pairs.json`, `cite-check-report.json`
   - Step 15: `polish-log.json`
   - Step 16: `readability-recs.json`

---

## How to invoke subagents (Hermes mapping)

Where a step says "Spawn `<subagent_type>` subagent(s)", call:

```
delegate_task(
  role="leaf",
  goal="<the full rendered spawn prompt from the step file>",
  context="<any extra run context: vault_tag, file paths, the shim text if referenced>"
)
```

For multiple parallel subagents (e.g. 3 draft-orchestrators, 4 critics), issue
them as separate `delegate_task` calls in the same turn so they run concurrently.
Each step file contains the EXACT spawn prompt to paste into `goal`. Do not
summarize or trim it — it is the subagent's contract.

If a step references a posture **shim** file under `research/runs/<vault_tag>/shims/`,
render it first with `hpr levers render <vault_tag> -j`, then append its FULL
contents to the subagent goal. The cite-checker receives NO shim.
