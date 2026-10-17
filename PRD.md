# Product requirements — Trading Lab

Updated: 2026-10-17. Owner: Muhammad Arman Saleem.

## Audience and outcome

Build for Arman's younger brother and people who do not know the basics of trading.
Users should not need CSV files, API knowledge or model selection to try the agent.
The eventual goal is guided, autonomous trading on the user's behalf with clear
controls and understandable results. Profitability is not a promised feature.

Confirmed: separate Crypto, Forex and Stocks sections; local laptop use; continuous
operation is not required. The user delegated routine design/implementation decisions.
Broker account, live instrument/limits, eligibility and real-money activation remain
unresolved. Choosing Bitcoin for read-only price practice does not select a real broker.

## Current release

The default screen is a guided **virtual-money practice desk**. Users select a market,
price source, starting virtual money, maximum spend per trade and account-drop halt.
Start, pause entries, close holdings, export and help use plain language.

- Crypto: generated demo or read-only public Bitcoin/USD prices from Kraken.
- Forex/Stocks: clearly labeled generated demos; real feeds unavailable.
- All fills are local simulations; no broker orders or real-money mode.
- Practice balances, holdings, model, processed candle and events persist in SQLite.
- Reopen paused; no monitoring while closed; outages require reconnect.
- One monitored account at a time; close virtual holdings before changing markets.
- The original CSV/backtest app remains under Advanced research.

## Acceptance criteria

| Flow | Required behavior |
|---|---|
| First run | Create and run a demo without CSV, credentials or strategy configuration |
| Real-price practice | Fetch public Bitcoin candles/quotes automatically; no secret or account required |
| Source honesty | Demo/real prices/virtual money remain visible; never silently switch source |
| Waiting | Explain no-entry signals without forcing an artificial trade |
| Pause | Block new entries but keep sampled position exits active while connected |
| Close holdings | Confirm intent; use a fresh quote; sell virtual units and pause entries |
| Restart | Restore holdings/model/consumed signal; start paused; do not replay missed fills |
| Failure | Show provider, validation or save failure and stop processing until retry |
| Accounting | Include costs both sides; reconcile realized P/L; avoid duplicate candle entries |
| Loss halt | Exit at observed quote and stop entries; disclose threshold is not guaranteed |
| Small screen | Main content can scroll; core setup and controls remain reachable |
| Handoff | Docs separate existing capabilities, tests and incomplete integrations |

Default settings are illustrative, not financial advice. Sampled stops may miss moves
or fill beyond thresholds. A public price feed is not broker-connected paper trading.

## Milestones

1. Completed foundation: historical research engine and tests (baseline `8c8f6e7`).
2. Current change: beginner onboarding, durable local forward practice and one public
   price feed; retain existing research history and engine.
3. Next: select an eligible actual venue and integrate its paper/sandbox account with
   durable external order/fill reconciliation, sizing/session rules and recovery tests.
4. Later: independently evaluated strategy and explicit live activation, with a clear
   shutdown policy and broker-hosted protection where supported.

No deposit collection, guaranteed returns, leverage, real fund movements or fake broker
connection flows are part of this release. Actual laptop acceptance remains separate
from automated tests and developer-environment UI checks.

## Verification record

Current change: 27 tests passed (including three actual Tk flow checks in a Linux
virtual display), onboarding/dashboard visually inspected, and real Kraken data
retrieved. User-laptop/Windows acceptance and profitable real-market performance
have not been established. Tests are software correctness evidence only.
