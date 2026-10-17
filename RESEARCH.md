# Advanced historical research

A lightweight local desktop research app for Arman's multi-market trading project.
Separate **Crypto, Forex and Stocks** workspaces; a locally trained machine-learning
classifier, a trend-rule baseline, historical simulation and saved reports.

**This research window is an offline historical simulator, not a live trading bot.** It cannot
place orders or obtain current prices. Included prices are synthetic demonstrations,
not evidence of trading profit. No broker account or paid API is required.

## Windows setup

1. Install Python 3.10 or newer from https://www.python.org/downloads/windows/.
   Keep Tcl/Tk enabled. No pip dependencies or GPU are needed.
2. Download this repository using **Code → Download ZIP**, then extract it.
3. Use **Advanced research** from the main app, or run `py -3 research_app.py` in this folder.
4. Choose a market and click **Train & run test** to try the synthetic demo.
5. Import historical OHLC CSV data to test on real prices. Set costs to match the
   intended instrument and venue before interpreting results.
6. Compare both strategies; inspect trades, replay bars and export a JSON report.

On macOS/Linux use `python3 research_app.py`. Python needs Tk (e.g. `python3-tk` on
Debian/Ubuntu). Closing the app stops computation; there are no background orders.

## Included

- Independent in-session datasets/results for Crypto, Forex and Stocks.
- CSV validation and a chronological 60% training / 40% test split.
- L2 logistic regression trained locally, plus a 10/30-bar moving-average strategy.
- Long/flat positions, allocation cap, stop loss, target and drawdown halt.
- Fees and slippage on both entry and exit; trade reasons and realized P/L.
- Equity chart, closing drawdown, buy-and-hold reference and historical replay.
- SQLite run history at `~/TradingLabData/runs.sqlite3`; full JSON report export.
- Headless runner and tests for accounting, risk controls and future-data leakage.

All sections share a **generic, unleveraged, fractional-unit simulator**. They are
not broker-specific implementations. Balance and P/L use the instrument's quote
currency, not automatically PKR/USD. Import only one symbol and interval per file.
Data selections are in-session; completed reports persist across restarts.

## CSV format

UTF-8, 150–100,000 rows, maximum 30 MB. Required headers (case insensitive):

```csv
date,open,high,low,close
2025-01-01,100,104,98,102
2025-01-02,102,105,100,103
```

This is a format example; provide at least 150 rows. Extra columns are allowed.
Timestamps must be increasing, unique ISO dates/times, with consistent timezone
format. Prices must be positive and OHLC ranges valid. Use your provider's exports.
Adjust all OHLC columns consistently for corporate actions; do not combine an
adjusted close with unadjusted open/high/low. No data service is connected in this research window; the main practice app has a separate public Bitcoin feed.

## ML and test methodology

Features are trailing log returns over 1, 3, 5, 10 and 20 bars plus 20-bar volatility.
The target is whether the next bar closes above its own open. Standardization is
fitted only on training examples, with at most the last 2,001 labeled training rows.
The first 60% is training; the last 40% is testing. Training labels end before the
test starts. Model weights remain frozen during the test. Decisions only use data
through the closed bar, and execute at the **next bar open**.

Model score ≥55% requests a long; ≤45% requests an exit; otherwise the position is
unchanged. This is real small-scale ML, not an LLM. Scores are not calibrated
confidence. The directional training target is simpler than the multi-bar trade
outcome, and predictive accuracy alone does not establish profitable trading.

The trend rule buys when the 10-bar mean exceeds the 30-bar mean; otherwise exits.
Neither strategy is validated for any real market. Defaults are demonstration
settings, not personalized investment recommendations. Repeatedly selecting settings
on the same test interval overfits it; reserve further untouched periods.

## Execution assumptions

- One long position; no shorts, leverage, margin or derivatives.
- Allocation is a fraction of cash at entry, not a guaranteed maximum loss.
- Stops/targets use the slipped entry price. Gap-down stops fill at the open when
  it is below the stop. Gap exits cannot re-enter on the same bar. Gap-up targets
  conservatively fill at the target.
- If both stop and target are touched within a bar, the stop executes first.
- Drawdown halting checks opens/closes. Reported max drawdown uses closing equity;
  intrabar drawdown may be worse. Gaps can exceed configured loss thresholds.
- Any remaining position is liquidated with costs at the end of the test.
- Buy-and-hold invests 100%, versus the strategy's chosen allocation; this reference
  is not risk-matched.
- No order book, spread curve, liquidity limits, partial fills, lot sizes, trading
  calendars, FX pip/lot conventions, swaps/funding, dividends, taxes, delistings or
  currency conversion. Slippage/fee inputs are simplified proportional costs.
- Synthetic examples contain arbitrary daily dates including weekends.
- Replay only animates a completed backtest. Metrics and trades show the whole run.
- Reports stay on your laptop, unencrypted; nothing is sent to a remote service.

## Developer commands

```bash
python run_test.py --market Crypto --strategy "ML classifier" --output report.json
python run_test.py --market Forex --csv historical.csv --strategy "Trend rule"
python -m unittest discover -s tests -v
```

| File | Purpose |
|---|---|
| research_app.py | Desktop UI, background training, charts, saved runs |
| engine.py | Data validation, model, signals, simulated fills |
| run_test.py | Command-line runner |
| tests/test_engine.py | Deterministic correctness tests |
| START-WINDOWS.bat | Windows launcher |

## Remaining work toward autonomous live trading

The main app now provides local forward practice with a public Bitcoin price feed.
The following items concern actual broker-connected execution.

Select an actual instrument and eligible broker/exchange; implement its data and
sandbox/paper execution adapter; persist positions/orders; reconcile fills after
restart; handle stale prices, disconnects, minimum sizes and duplicate orders;
then evaluate independent real data and forward paper trading. Live activation
requires an explicit decision and broker credentials configured locally. No live
order endpoint or credential fields are present in this version.

With an intermittently running laptop, a future live connector must use supported
broker-hosted protective orders and reconcile on reopening. A local stop cannot
protect an account while the computer is asleep or disconnected.

## For coding agents and contributors

Start with [AGENTS.md](AGENTS.md). These documents describe the project and keep
future agents working from shared requirements:

| Document | Purpose |
|---|---|
| [PRD.md](PRD.md) | Product goal, scope, acceptance criteria and milestones |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Current components, data flow, state and proposed evolution |
| [ARCHITECTURE-ESSENTIALS.md](ARCHITECTURE-ESSENTIALS.md) | Quick technical orientation and invariants |
| [AGENTS.md](AGENTS.md) | Shared coding, verification and handoff instructions |
| [CLAUDE.md](CLAUDE.md) | Claude entry point pointing to the shared guidance |
| [DECISIONS.md](DECISIONS.md) | Important decisions, reasons, alternatives and trade-offs |

Record material decisions with the provided template in the same change. Preserve
older records and explicitly supersede them when a decision changes. These files
guide tools that read them; they do not guarantee automatic loading by every agent.
