# Decision log

This file records **what was decided and why**, so future contributors and the owner
can understand trade-offs. It is not a transcript or a private reasoning log.

Entries 001–004 retrospectively document choices made in implementation baseline
`8c8f6e7`. They are implementation choices, not claims that the user prescribed the
stack or approved live trading. Dates use YYYY-MM-DD. Append material new entries;
keep prior records and link replacements rather than silently rewriting history.

## ADR-001 — Build historical simulation before broker execution

- **Date:** 2026-10-17
- **Status:** Implemented; live execution remains unimplemented.
- **Context:** User wants an autonomous trading application with multiple market
  sections, but has no selected venue, instrument or trading rules.
- **Decision:** Deliver a clearly labeled offline testing foundation first.
- **Rationale:** It makes strategy behavior and accounting inspectable without
  inventing broker access or executing untested orders.
- **Alternatives:** Immediately choose a broker and place live orders; build only a
  nonfunctional dashboard. Neither addresses the unresolved execution requirements.
- **Consequences:** The current app is usable for research, but does not complete the
  original autonomous-trading goal. Synthetic results cannot establish profitability.
- **Evidence:** Simulator and CLI implemented; initial 10 engine tests passed.
- **Revisit when:** A specific venue and paper environment have been selected.

## ADR-002 — Use a local Python/Tk application with standard-library dependencies

- **Date:** 2026-10-17
- **Status:** Implemented; desktop user acceptance pending.
- **Context:** User prefers laptop execution and does not require continuous operation.
- **Decision:** Use Python, Tk, standard-library ML code and SQLite report history.
- **Rationale:** Small installation surface, no hosted service or paid inference API,
  and no GPU requirement for the implemented model.
- **Alternatives:** Hosted web app; separate frontend/backend; large local AI model.
- **Consequences:** UI styling is limited by Tk, Python/Tk must be installed, and no
  activity occurs when closed. Laptop specs have not been verified. The Python
  application was an implementation choice, not an explicit user stack requirement.
- **Evidence:** Python compilation and CLI run succeeded; Windows GUI not exercised.
- **Revisit when:** User needs browser/mobile access, deployment or background operation.

## ADR-003 — Compare simple ML with a transparent trend baseline

- **Date:** 2026-10-17
- **Status:** Implemented; not validated for real trading.
- **Context:** User requested AI but supplied no defined strategy or training dataset.
- **Decision:** Add local logistic regression and a 10/30-bar trend rule. Use a
  chronological train/test split and frozen model parameters during testing.
- **Rationale:** Provides actual ML functionality and a simpler comparison while
  making leakage boundaries and trading decisions inspectable.
- **Alternatives:** LLM-generated discretionary orders; pretrained opaque signals;
  label a deterministic rule as AI.
- **Consequences:** Scores are uncalibrated. A next-bar direction target does not
  optimize eventual trade profit. Neither strategy has proven market performance.
- **Evidence:** Tests cover earlier signals remaining unchanged after future-data
  alterations and runs for all three market/two-strategy combinations.
- **Revisit when:** Real data, a defined objective and independent evaluation exist.

## ADR-004 — Share a conservative generic historical fill model

- **Date:** 2026-10-17
- **Status:** Implemented with documented limitations.
- **Context:** User requested separate market sections before selecting any broker.
- **Decision:** Share long/flat, unleveraged fractional-unit accounting; charge both
  sides' costs; execute previous-close signals next open; make stops win ambiguous
  bars; model gap-down stops at the available open; prohibit same-bar gap re-entry.
- **Rationale:** Keeps initial accounting consistent and avoids favorable assumptions
  that OHLC data cannot establish.
- **Alternatives:** Assume ideal fills; build three venue-specific engines before
  selecting venues; introduce leverage and derivatives immediately.
- **Consequences:** Generic units are not FX lots or exchange sizing. Sessions,
  liquidity, funding, taxes and other real execution details are missing. Drawdown
  thresholds are not guaranteed loss caps; intrabar drawdown is not fully measured.
- **Evidence:** Tests cover fee reconciliation, next-open fills, gap stops, ambiguous
  stop/target bars and halting. See README for the complete assumptions.
- **Revisit when:** Adding a concrete instrument, broker or more detailed price data.

## ADR-005 — Use shared agent guidance and an explicit decision log

- **Date:** 2026-10-17
- **Status:** Implemented in this documentation change.
- **Context:** User supplied a screenshot of six project files and expects different
  coding agents to continue development. The screenshot's sixth label is “Empty file”;
  its intended meaning is not verifiable from the screenshot alone.
- **Decision:** Add PRD.md, ARCHITECTURE.md, ARCHITECTURE-ESSENTIALS.md, AGENTS.md,
  CLAUDE.md and this DECISIONS.md. Treat AGENTS.md as the shared rules and CLAUDE.md
  as an entry point that directs Claude to those rules.
- **Rationale:** Separate product requirements, detailed implementation, quick
  orientation, agent behavior and decision history. Give the sixth file a useful
  purpose consistent with the user's suggestion instead of leaving a blank file.
- **Alternatives:** Duplicate rules for each agent; one large undifferentiated document;
  leave an unexplained empty file.
- **Consequences:** Docs must be maintained with meaningful changes. The files guide
  agents that read them; their presence does not enforce compliance or configure every
  third-party tool automatically. README links provide a manual entry point.
- **Evidence:** File references and implemented-state descriptions checked against code.
- **Revisit when:** Guidance diverges, an agent needs a specific entry point, or the
  decision log becomes large enough to split into individual ADR files.

## Template for the next material decision

```markdown
## ADR-NNN — Short decision title

- **Date:** YYYY-MM-DD
- **Status:** Proposed | Implemented | Rejected | Superseded by ADR-NNN
- **Context:** Concrete problem and constraints; distinguish facts from assumptions.
- **Decision:** What is being adopted or proposed.
- **Rationale:** Concise engineering justification.
- **Alternatives:** Relevant options considered and why they were not selected.
- **Consequences:** Benefits, costs, risks and remaining limitations.
- **Evidence:** Actual checks/measurements, commit or PR; say if not yet verified.
- **Revisit when:** Conditions that would justify changing this choice.
```
