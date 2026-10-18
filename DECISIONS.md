# Decision log

This file records **what was decided and why**, so future contributors and the owner
can understand trade-offs. It is not a transcript or a private reasoning log.

Entries 001–004 retrospectively document choices made in implementation baseline
`8c8f6e7`. They document implementation choices and do not imply live-trading authorization. Dates use YYYY-MM-DD. Append material new entries;
keep prior records and link replacements rather than silently rewriting history.

## ADR-001 — Build historical simulation before broker execution

- **Date:** 2026-10-17
- **Status:** Implemented; live execution remains unimplemented.
- **Context:** The product requires automated trading across multiple market
  sections; the venue, instruments and production trading rules are not yet selected.
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
- **Context:** The product targets local desktop execution without continuous operation.
- **Decision:** Use Python, Tk, standard-library ML code and SQLite report history.
- **Rationale:** Small installation surface, no hosted service or paid inference API,
  and no GPU requirement for the implemented model.
- **Alternatives:** Hosted web app; separate frontend/backend; large local AI model.
- **Consequences:** UI styling is limited by Tk, Python/Tk must be installed, and no
  activity occurs when closed. Minimum hardware requirements have not been benchmarked. The Python
  application was an implementation choice, not a fixed product requirement.
- **Evidence:** Python compilation and CLI run succeeded; Windows GUI not exercised.
- **Revisit when:** Product requirements expand to browser/mobile access, deployment or background operation.

## ADR-003 — Compare simple ML with a transparent trend baseline

- **Date:** 2026-10-17
- **Status:** Implemented; not validated for real trading.
- **Context:** AI-assisted decisions are a product requirement; a production strategy and training dataset are not yet defined.
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
- **Context:** The product requires separate market sections; no broker has been selected.
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
- **Context:** Multiple coding agents need a shared product specification,
  architecture reference, contributor instructions and decision history.
- **Decision:** Add PRD.md, ARCHITECTURE.md, ARCHITECTURE-ESSENTIALS.md, AGENTS.md,
  CLAUDE.md and this DECISIONS.md. Treat AGENTS.md as the shared rules and CLAUDE.md
  as an entry point that directs Claude to those rules.
- **Rationale:** Separate product requirements, detailed implementation, quick
  orientation, agent behavior and decision history. Maintain an explicit decision log
  so contributors can understand the rationale behind significant changes.
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

## ADR-006 — Make guided virtual practice the default experience

- **Date:** 2026-10-17
- **Status:** Implemented; extends the historical-first foundation in ADR-001.
- **Context:** The target audience includes beginners and nontechnical users.
  The research-first screen required too much trading and configuration knowledge.
- **Decision:** Replace the default screen with onboarding and a practice dashboard;
  preserve the old interface as `research_app.py`, accessible under Advanced research.
- **Rationale:** Users can try the agent without importing data or choosing a model.
  Familiar controls explain waiting, spending limits, holdings and gains/losses.
- **Alternatives:** Only restyle the research dashboard; rebuild a hosted web product.
- **Consequences:** Keeps the lightweight laptop stack and original research history.
  Entry pause and full position close are separate. No fake broker-connect button is added.
- **Evidence:** 27 tests passed including three Tk flow tests in a Linux virtual display;
  onboarding/dashboard visually inspected. Target-device Windows acceptance remains unverified.
- **Revisit when:** Real account onboarding or cross-device access is requested.

## ADR-007 — Use read-only Bitcoin data for the first forward practice feed

- **Date:** 2026-10-17
- **Status:** Implemented for local virtual fills; no broker account integration.
- **Context:** A beginner needs automatic prices, while actual broker/account choice
  remains unresolved. One concrete data adapter is more testable than nominal all-market support.
- **Decision:** Offer Kraken public BTC/USD OHLC/ticker alongside clearly separate
  offline demos. Forex/Stocks remain labeled demos. Reject feed failures without fallback.
- **Rationale:** Public reads need no secrets. Official documentation describes the
  unfinished candle and quote fields needed for closed-bar signals and receipt-time fills.
- **Alternatives:** Require CSV; collect credentials before practice; claim generic
  stock/forex execution without implementing the required providers.
- **Consequences:** This is not a broker recommendation or eligibility assertion.
  Public access depends on network/provider. Receipt time does not prove exchange quote
  freshness. Simulated fills have no liquidity or actual execution guarantees.
- **Evidence:** Actual public-data fetch succeeded; parser tests exclude the unfinished
  candle and reject stale candles/bad quotes. Official references are in architecture.
- **Revisit when:** Choosing an actual venue or additional verified market data providers.

## ADR-008 — Persist practice state and separate entry pause from shutdown

- **Date:** 2026-10-17
- **Status:** Implemented for local practice only.
- **Context:** Intermittent laptop use and retries must not silently reset holdings,
  duplicate entries or treat a closed app as if it kept monitoring the market.
- **Decision:** Atomically save whole account/event state with optimistic revisions.
  Persist weights/processed candle; restore paused. Pause new entries keeps exits active
  only while connected. Manual close fetches a fresh quote. Invalidate late worker results.
- **Rationale:** Gives understandable controls and prevents common local consistency errors.
- **Alternatives:** Memory-only balances; automatic resume; duplicate signals on every
  poll; mark positions closed during shutdown without a fresh quote.
- **Consequences:** No background monitoring or invented catch-up fills. A stale/offline
  valuation can differ from the next quote. One account is monitored at a time; open
  virtual holdings must close before switching markets. External order recovery is future work.
- **Evidence:** Tests cover restart holdings/model state, repeated candles, pause/exit,
  failed-save rollback and stale-writer rejection. Tk flow tests verified that a
  pending entry is discarded after Pause, and exercised close/export/restoration.
- **Revisit when:** Multiple concurrently monitored accounts or actual broker orders are added.
