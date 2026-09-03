# hyperresearch-skills

[Hermes Agent](https://github.com/NousResearch/hermes-agent) skill tap for
**HYPERRESEARCH V8** — a tier-adaptive, 16-step deep-research pipeline that
turns a single question into a fully-sourced, adversarially-audited report.

The pipeline is orchestrated by a router skill (`hyperresearch`) that sequences
20 companion step-skills. Each step's procedure lives in its own `SKILL.md`,
loaded fresh via `skill_view` when the orchestrator invokes it.

> The underlying `hyperresearch` CLI is a separate PyPI package by
> [jordan-gibbs](https://github.com/jordan-gibbs/hyperresearch) (MIT).
> This repo packages the Hermes skill layer on top of it.

## Install — one command

```bash
hermes skills tap add OwenRay/hyperresearch-skills
hermes skills install OwenRay/hyperresearch-skills/hyperresearch
```

Then install the step skills (or ask your agent to — the entry skill's
**Setup** section does this bootstrap automatically when it detects missing
pieces):

```bash
for s in hyperresearch-1-5-chapter-partition hyperresearch-1-decompose \
         hyperresearch-2-width-sweep hyperresearch-3-contradiction-graph \
         hyperresearch-4-loci-analysis hyperresearch-5-depth-investigation \
         hyperresearch-6-cross-locus-reconcile hyperresearch-7-source-tensions \
         hyperresearch-8-corpus-critic hyperresearch-9-evidence-digest \
         hyperresearch-10-triple-draft hyperresearch-11-synthesize \
         hyperresearch-12-critics hyperresearch-13-gap-fetch \
         hyperresearch-14-5-cite-check hyperresearch-14-patcher \
         hyperresearch-15-polish hyperresearch-16-readability-audit \
         hyperresearch-browser-fetch hyperresearch-run-ops; do
  hermes skills install "OwenRay/hyperresearch-skills/$s"
done
```

## Install — single link (give it to your agent)

Paste this into any Hermes session (CLI, Discord, Telegram, …):

```
Install the hyperresearch skills from the GitHub repo OwenRay/hyperresearch-skills
using hermes skills, then set up the hyperresearch CLI per the entry skill's
Setup section, and confirm everything is ready for a research run.
```

The agent will add the tap, install all 21 skills, run
`uv tool install hyperresearch`, and verify the setup.

## Prerequisites

- [Hermes Agent](https://hermes-agent.nousresearch.com/docs/) (any recent version)
- Python 3.11+ with [uv](https://docs.astral.sh/uv/) — the entry skill's Setup
  section installs the `hyperresearch` CLI automatically if missing
- Optional: SSH access to a Mac with a debuggable Chrome instance for the
  `hyperresearch-browser-fetch` escalation (JS-SPAs, bot-walls, 403s). Without
  it the pipeline still works — gated fetches degrade to abstracts.

## Usage

```
/hyperresearch <research question>
```

Example:

```
/hyperresearch What are the trade-offs between MoE and dense transformers at the 100B scale?
```

Tier routing is automatic: short bounded questions run the light tier
(~30–40 min), argumentative deep-research questions run all 16 steps with
adversarial review.

## Skills in this tap

| Skill | Role |
|---|---|
| `hyperresearch` | Entry skill — router/orchestrator + environment bootstrap |
| `hyperresearch-1-decompose` … `hyperresearch-16-readability-audit` | The 16 pipeline steps (incl. half-steps 1.5 and 14.5) |
| `hyperresearch-run-ops` | Run-management procedures (status, resume, verify, curation) |
| `hyperresearch-browser-fetch` | Real-browser fetch escalation over CDP |

## License

MIT — see [LICENSE](LICENSE).
