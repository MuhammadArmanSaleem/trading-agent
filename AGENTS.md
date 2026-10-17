# Coding-agent instructions

Applies throughout this repository. Follow the user's current task and applicable
higher-priority instructions. This file coordinates development; it does not authorize
live trading, external account changes or deployment.

## Before changing code

1. Read this file, [PRD.md](PRD.md), [ARCHITECTURE-ESSENTIALS.md](ARCHITECTURE-ESSENTIALS.md)
   and relevant entries in [DECISIONS.md](DECISIONS.md).
2. Read [ARCHITECTURE.md](ARCHITECTURE.md) and the affected implementation before
   changing boundaries, execution, storage or data handling.
3. Inspect current branch, remote head and uncommitted work. Preserve other people's
   changes. Historical docs are context; inspect code when verifying current behavior.
4. State material assumptions. Do not silently select a broker, invent credentials,
   claim market access or reclassify the simulator as a completed live product.

## Development rules

- Keep changes focused on the requested outcome. Prefer the existing lightweight stack;
  justify new dependencies or framework replacements with a decision record.
- Preserve separation between engine, UI and future external adapters. Tk widgets must
  only be touched from the UI thread. Keep expensive work off that thread.
- Protect chronological data boundaries, next-bar execution and reproducible tests.
  Never tune on test outcomes and present the same interval as untouched evaluation.
- Preserve truthful labels for synthetic, historical, paper and live modes. ML scores
  are not proven confidence, and no test validates future profitability.
- Never commit credentials, private account data, local databases or personal exports.
- Future order integrations must distinguish proposed, submitted, accepted and filled
  states. Reconcile external state on restart and prevent duplicate submissions.
- The broad request to build a bot is not authorization to activate real-money trading.
  Keep credentials and any future live activation explicit and separate from testing.

## Verification

- Engine changes: run `python -m unittest discover -s tests -v` and add focused tests
  for the actual risk changed (cash flows, data leakage, timestamps, fills or halting).
- UI changes: exercise launch, modified controls and affected workflows when a display
  is available. Report untested GUI behavior plainly; compilation is not GUI testing.
- Documentation-only changes: verify file references, code descriptions and consistency;
  do not add implementation-mirroring tests just for documentation edits.
- Record commands, outcomes and material limitations in the handoff/PR. Never fabricate
  passing tests or claim a synthetic run demonstrates profitable market trading.

## Decision records and handoff

For a material architectural, dependency, strategy, persistence or execution-policy
choice, append a numbered entry to [DECISIONS.md](DECISIONS.md) in the same change.
Use its template. Explain the outcome, concise rationale, alternatives, consequences
and verification evidence. Record useful engineering summaries, not private reasoning
traces, credentials or full conversation dumps. Routine formatting needs no new entry.

Distinguish implemented choices from proposals and user requirements. Preserve prior
entries; mark them superseded and link the replacement when needed. Do not manufacture
user approval. Update PRD/architecture/README only where the change affects their scope.

Before handing off, report what changed, why, what was checked, what remains uncertain
and the next concrete dependency. Leave no fake TODO completions or empty placeholder
files disguised as implemented capabilities.

## Git and collaborating agents

For future feature work, prefer a focused branch and reviewable PR unless the user
requests another workflow. Do not force-push, overwrite unrelated edits or merge/deploy
without applicable authorization. Never treat a docs file as branch-protection enforcement.
If agents are working concurrently, agree on file ownership and reconcile the latest
head before publishing; do not assume another agent's changes are disposable.
These rules support collaboration but do not require spawning additional agents.
