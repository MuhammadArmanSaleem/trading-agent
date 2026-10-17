# Architecture

Updated: 2026-10-17. Describes the existing implementation; future components are
explicitly marked proposed. For brief invariants see
[ARCHITECTURE-ESSENTIALS.md](ARCHITECTURE-ESSENTIALS.md).

## Current modules

| Module | Responsibility | Boundary |
|---|---|---|
| `engine.py` | Bar/config models, CSV validation, synthetic examples, features, logistic model, signals, simulation | No UI, network requests or broker orders |
| `app.py` | Tk interface, market workspaces, background simulation, chart/replay, report saving/export | Calls the engine; UI operations stay on the Tk thread |
| `run_test.py` | Headless simulation and JSON report | Shares the engine; CLI output is not automatically saved into GUI history |
| `tests/test_engine.py` | Deterministic accounting, fill, risk, data and leakage checks | No network or real account dependency |
| `START-WINDOWS.bat` | Launch via Python 3, show an error if launch fails | No installation or background service |

## Data flow

1. A market workspace starts with a deterministic synthetic OHLC series, or the user
   imports a CSV. Validate increasing unique ISO timestamps and positive OHLC ranges.
2. The UI snapshots bars, settings, market and source before starting a worker thread.
3. `simulate` uses the first 60% of bars as the training segment and the remaining
   40% as the test segment. The ML strategy fits once; the trend rule requires no fit.
4. A signal from the previous closed bar is applied at the current test bar's open.
   Fills, fees, risk exits and equity are tracked under the documented OHLC assumptions.
5. The worker queues a result; the Tk thread polls, stores and renders it. Do not call
   Tk widgets from the worker. A failed save is shown separately from a successful test.
6. Completed UI runs are stored in SQLite; users can export the full JSON report.

## Model and strategy

`features` uses five trailing log returns and 20-bar volatility. `Model` implements
L2-regularized logistic regression with training-only mean/standard-deviation scaling.
Training uses at most the last 2,001 labeled examples before the test boundary. Labels
represent the following bar's open-to-close direction. Weights are frozen in testing.
A score at least .55 buys, at most .45 sells, otherwise holds. Scores are uncalibrated.
The alternative strategy compares 10- and 30-bar closing-price means.

No external AI provider or LLM is involved. The directional target does not directly
optimize multi-bar trading returns. Full methodology and limitations are in README.

## Simulation and risk semantics

Positions are long/flat with fractional units in the instrument's quote currency.
Allocation caps the cash spent at entry, including entry fees. Both sides receive
fee and slippage adjustments. Gap-down stops use the lower open; target gaps use a
conservative target fill. If a bar touches both stop and target, the stop wins.
A gap exit cannot immediately re-enter on that bar. Remaining positions are closed
at test end. Realized trade P/L includes entry and exit fees.

Drawdown halting checks opening and closing equity; reported max drawdown is based
on closes. Gaps and intrabar moves can exceed the configured threshold. These limits
are not guarantees. The buy-and-hold reference invests all capital and is not risk-matched.

## State and persistence

- In-memory market state: bars, source label, latest result. Current settings are
  shared UI controls; each completed report retains its actual config.
- GUI history: `~/TradingLabData/runs.sqlite3`, table `runs` with `id`, `created`,
  `market`, `source`, and complete JSON `report`.
- GUI report metadata includes UTC creation time and app version. CLI reports include
  market/source but do not currently include identical creation/version metadata.
- Inputs are not automatically restored on restart. Saved runs can be exported; they
  are not reloaded into the current chart. Reports are local and unencrypted.
- Chart rendering is sampled for large series; exported curves remain complete.
  The trade table displays the last 3,000 events; exports contain every event.

## Proposed evolution — not implemented

Introduce a data-provider boundary and a broker adapter only after selecting a venue.
Keep historical simulation distinct from forward paper and live execution. Future
execution needs durable order IDs, order/fill/position state, reconciliation on startup,
retry/idempotency handling, stale-data checks, market-specific size/session rules and
failure visibility. Broker-hosted protection must address intermittent laptop operation.

Do not reuse an optimistic simulated fill as proof that a broker order succeeded.
Credentials must stay out of source, reports and logs. Document the selected adapter
and its verified limitations in a new decision record before presenting it as supported.

## Verification and changes

Run `python -m unittest discover -s tests -v` for engine changes. Add focused tests
for changed behavior, particularly costs, timing, leakage, risk exits and restarts.
For UI changes launch the app and exercise affected interactions where possible;
otherwise explicitly report that GUI behavior was not verified. Update architecture
and decision records alongside meaningful changes, without inventing test evidence.
