# Architecture

Updated: 2026-10-17. Current beginner-practice change; proposed integrations are marked.

## Modules and boundaries

| File | Owns | Does not own |
|---|---|---|
| `app.py` | Tk onboarding/dashboard, polling, epoch cancellation, persistence handoff | Real orders or secrets |
| `practice.py` | Account state, local ML decisions, virtual fills, sampled exits, SQLite transactions | Network calls or Tk widgets |
| `market_data.py` | Public OHLC/ticker reads, snapshot validation, synthetic demo generation | Authenticated exchange endpoints |
| `research_app.py` | Original historical UI, run exports, research history | Forward execution |
| `engine.py` | Shared features/model and original historical simulator | Network, Tk or broker account state |
| `run_test.py` | Historical CLI | Practice account persistence |

## Beginner flow and concurrency

Onboarding creates a saved virtual account with market, mode, starting balance,
allocation fraction and peak-relative drop threshold. No model or CSV choice is needed.
Start saves a running state, then begins polling. A worker uses a copy of account state
to fetch a snapshot and compute a candidate update. The main thread accepts the result
only if its epoch/market still matches, saves it atomically, and then displays it.
Pause, market change, close request and shutdown invalidate pending work. In-flight
network reads are bounded by timeouts; discarded results cannot trade after a control
change. Tk is never updated from the worker.

Only one practice account is monitored at a time. Switching markets requires a flat
current account. Paused entries can still have existing positions, so monitoring and
exit checks continue until disconnected. A provider error sets attention state and
stops polling; reconnect is explicit. Closing the app stops all monitoring.

## Public market data

Only BTC/USD via Kraken public OHLC and ticker is integrated. Calls use fixed public
GET endpoints, timeouts and a response-size limit; no credential or order endpoint.
Drop the final OHLC row because Kraken documents it as the uncommitted current frame.
Require at least 150 closed rows with valid sorted ISO timestamps and positive OHLC.
Validate finite bid/ask, non-crossed quote, spread no greater than 5%, receipt age no
more than 25 seconds and closed-candle age no more than 180 seconds. A small forward
clock tolerance is allowed. Never substitute synthetic data after a provider error.

Ticker age uses local receipt time; the ticker itself lacks an exchange-generated
quote timestamp. Candle freshness and receipt checks cannot fully prove quote freshness.
The snapshot carries explicit source, symbol and synthetic flags; account validation
rejects incompatible snapshots. Polling happens about 20 seconds after completion,
not tick-by-tick. Offline demos generate deterministic accelerated minute bars.

Official references: [OHLC](https://docs.kraken.com/api-reference/market-data/get-ohlc-data)
and [ticker](https://docs.kraken.com/api-reference/market-data/get-ticker-information).

## Forward practice model and fills

Reuse the existing L2 logistic regression and trailing-return/volatility features.
On first connection train on available closed bars, with labels contained in those
bars, then mark the latest known candle consumed. First possible entry is on a later
closed candle. Weights remain frozen in the saved account. Every candle is consumed
at most once, including when paused. On reconnect only the latest candle is considered;
no missed historical fills are fabricated.

Scores ≥.55 request entry, ≤.45 request exit, otherwise hold. Scores are uncalibrated
and no market edge has been established. Buy at observed ask with .05% slippage and
.1% fee; sell at observed bid with the same assumptions. All trades are virtual and
use receipt-time quotes, not past candle opens. One fractional long position per account.

At every accepted snapshot, check account drawdown, then position stop/target, then
model action for a new candle. A protective exit cannot re-enter in the same update.
Loss halt closes at observed bid and permanently disables entries for that account.
Pause blocks entries while allowing stop/target/model exits when connected. Manual
close requires a fresh compatible snapshot and leaves entries paused. Gaps and missed
polls can exceed configured thresholds. No depth, partial fills, market impact, lot
sizes, leverage or real exchange order states are modeled.

## Storage and restart

`~/TradingLabData/practice.sqlite3` stores JSON account state, ID, market, updated UTC
and revision. State contains cash, units, cost basis, entry, fees, realized P/L, peak,
last quote/candle, model weights, demo step, status, events and recent equity points.
Use whole-state transactions: state and event changes either both commit or neither.
Optimistic revision checks block stale writers from overwriting newer state. The UI
publishes a candidate only after successful save. Conflicts/storage errors stop polling.

Restart loads the latest account per market, retaining holdings/model/consumed candle
but forcing a paused state (or halted if already halted). It never automatically resumes.
History keeps prior accounts; reports export explicit practice/source/cost metadata.
Snapshots contain no real account information. Data is local and unencrypted.

Equity history retains the latest 3,000 observations; activity keeps all events in the
saved account, while the dashboard displays the most recent 150. Long-running state
size is a future scaling concern. There is no migration of research run history.

## Advanced historical research (unchanged engine)

`research_app.py` is the former `app.py`; it retains CSV validation, synthetic examples,
60/40 chronological train/test, training-only scaling and frozen-model backtesting.
Signals use previous closed bars and fill next open with documented costs/gap rules.
Historical ambiguity resolves stop before target. Test-end liquidation allows cash
reconciliation. Historical drawdown reports close-based equity, not intrabar peaks.
See [RESEARCH.md](RESEARCH.md) for full assumptions and command-line usage.
Research GUI runs stay in `~/TradingLabData/runs.sqlite3`. CLI exports remain separate.

## Future broker execution — not implemented

Choose an eligible venue with the user, then add a distinct sandbox/account execution
adapter. It needs external order/fill IDs, reconciliation on restart, idempotency,
minimum size/session rules, stale-data handling and broker-hosted protection for downtime.
A local simulated fill must never be interpreted as evidence of a filled broker order.
Live activation and credentials must remain explicit and separate from practice setup.

## Verification

Run `python -m unittest discover -s tests -v`. Tests cover historical behavior, virtual
cash flows, sampled halts, pause semantics, source/age checks, no repeated candle
entry, model freezing, restart preservation, revision conflicts and failed-save rollback.
Exercise onboarding, dashboard, source changes, pause/close and restoration with a
real Tk display where available; state unverified platform behavior honestly.
