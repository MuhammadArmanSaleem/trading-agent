# Product requirements — Trading Lab

Updated: 2026-10-18.

## Goal and users

Trading Lab targets beginner traders and nontechnical users who need guided setup,
plain-language explanations and clear controls across Crypto, Forex and Stocks.
The long-term goal is to execute defined strategies on behalf of users with visible
results and configurable limits. Profitability is not a promised feature.
The product supports local desktop use without requiring continuous operation.
The current research release is a technical foundation; the guided beginner experience
is being developed separately.

## Confirmed constraints and unresolved choices

| Item | Status |
|---|---|
| Repository | MuhammadArmanSaleem/trading-agent |
| Markets | Separate Crypto / Forex / Stocks sections requested |
| Runtime | Local laptop; intermittent use is acceptable |
| Broker, exchange, instrument | Not selected |
| Trading strategy | Production strategy not selected |
| Existing implementation | Python/Tk desktop simulator; an implementation choice, not a fixed product requirement |
| Real funds, limits, live activation | Not configured; explicit activation required |
| Computer specs and account eligibility | Not established |

## Current release: historical research

Implemented: three dataset/result workspaces, synthetic examples, validated OHLC CSV
import, chronological training/testing, local logistic regression, trend baseline,
simulated long/flat trades, costs and risk controls, equity chart, trade table,
historical replay, local run history, JSON export and a command-line runner.

This release has **no live quotes, broker connection, live paper-account execution,
order placement or LLM integration**. Market tabs share a generic simulator, not
three venue-specific execution engines. Input datasets are in memory; completed
reports persist in SQLite. The original autonomous-trading goal is not complete.

## Current acceptance criteria

- A Python installation with Tk can launch the desktop app without pip dependencies.
- The source is visibly labeled synthetic or user-imported; generated prices cannot
  be represented as market data or evidence of profitability.
- Invalid dates, prices, OHLC ranges and unsupported sizes are rejected clearly.
- Training labels stay before the test period; trading uses only information known
  at the signal time and fills at the next open under documented assumptions.
- Reports contain settings, trades, costs, equity history and source provenance.
- P/L reconciles with trade cash flows; gaps and ambiguous OHLC fills are explicit.
- GUI runs are saved locally and remain exportable through Saved runs.
- Replay is labeled historical; it is not presented as a live trading process.

Evidence at implementation baseline `8c8f6e7`: 10 engine tests passed, Python files
compiled, and the CLI smoke run completed. Windows GUI launch, layout and interaction
have not been verified on target Windows devices. Automated tests do not establish returns.

## Delivery milestones

| Stage | Deliverable | Completion evidence |
|---|---|---|
| 1 — Current | Offline research simulator | Engine tests and CLI run complete; desktop acceptance still needed |
| 2 — Planned | One selected venue's real data and paper/sandbox adapter | Provenance, timestamp handling, stale-data failures and forward paper fills verified |
| 3 — Planned | Durable execution and restart handling | Order/position reconciliation, duplicate prevention, disconnect and restart tests |
| 4 — Planned | Explicitly enabled live mode | User-selected venue/account, configured limits, independently evaluated strategy, explicit activation |

Implement the first concrete venue before generalizing to additional markets. Keep
separate sections, but do not invent broker/account choices or imply all markets
have equivalent rules. Future connectors must address lot sizes, sessions and costs.

## Laptop operation

The present app does nothing while closed. Any future live mode must explain how
positions are handled during shutdown, sleep and network failure. Protective orders
must be broker-hosted when supported; local checks cannot run while the laptop is off.

## Non-goals for this release

Guaranteed profit, optimized strategy selection, portfolio allocation advice, leverage,
shorting, derivatives, multi-currency accounting, hosted 24/7 operation and live money
movement. These are not silently included by adding a market tab or an AI label.

## Maintenance

Update this document when scope or acceptance criteria change. Keep implementation
status factual. Record significant choices in [DECISIONS.md](DECISIONS.md), and keep
[README.md](README.md) focused on installation and user-facing operation.
