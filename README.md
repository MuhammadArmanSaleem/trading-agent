# Trading Lab — practice first

A local desktop app for people who are new to trading. Create a virtual account,
press **Start practice**, and see what the bot does in plain language. No CSV files,
API keys or model configuration are needed in the main flow.

**This release uses virtual money only. It cannot trade real funds.** It includes
an actual small, locally trained ML model, but has no established profitable edge.

## Start on Windows

1. Install [Python 3.10+](https://www.python.org/downloads/windows/) with Tcl/Tk enabled.
2. Download this branch/repository as a ZIP and extract it.
3. Double-click **START-WINDOWS.bat** (or run `py -3 app.py`).
4. Choose a market, a price source and your virtual limits.
5. Click **Create practice account**, then **Start practice**.

No pip packages, GPU, paid AI subscription or trading account are needed. On
macOS/Linux use `python3 app.py`; Python must include Tk support.

## What each section supports

| Section | Offline demo | Practice with real prices | Real-money trading |
|---|---|---|---|
| Crypto | Yes, generated prices | Bitcoin / USD, read-only Kraken public data | Not available |
| Forex | Yes, generated prices | Not connected | Not available |
| Stocks | Yes, generated prices | Not connected | Not available |

The Bitcoin feed is an engineering starting point, not an investment recommendation
or a recommendation to open a Kraken account. Availability depends on network and
provider access. A blocked feed produces a visible error; it never silently switches
to demo data. No authenticated broker API is present.

## Beginner controls

| Control | What happens |
|---|---|
| Start practice / Reconnect | Prepare the local model if needed, read prices and permit new virtual trades |
| Pause new trades | Stop new entries; existing holdings and exit rules still update while connected |
| Close practice position | Fetch a fresh quote, sell all virtual holdings and leave entries paused |
| New account | Keep the old account in history; requires no open virtual position |
| Saved accounts | View and export previous practice accounts |
| Advanced research | Open the original historical-testing tools in a separate window |

The model can stay in cash; it is not forced to trade for the sake of a demonstration.
One account is monitored at a time. Close its virtual position before switching
markets. The main page shows virtual value, gains/losses, cash, open-position status,
source, last-received time and an activity log. Double-click an activity for fill details.

## Limits explained

- **Starting practice money:** virtual USD, never a deposit or real balance.
- **Maximum spend per trade:** fraction of available cash, limited to 1–25%. It is
  not a maximum-loss guarantee.
- **Account-drop halt:** observed account value falling 1–20% below its highest
  observed value closes the virtual position and disables further entries.
- **Practice position exits:** 2% price-drop stop, 4% price-rise target or model exit.
- **Estimated costs:** 0.1% fee and 0.05% extra slippage each side. Public bid/ask
  spread is included separately. These are assumptions, not the user's broker fees.

These settings are demonstration controls, not personal financial advice. Polling,
price jumps and disconnects mean a loss may exceed a configured threshold.

## Closing, sleep and internet failures

Accounts, holdings, model weights, consumed signals and events are saved transactionally
on this laptop in `~/TradingLabData/practice.sqlite3`. Reopening restores the latest
account per market with entries paused. Click **Reconnect / resume** to fetch new data.

**Nothing is monitored while the app is closed.** No exits are simulated during an
outage or while the laptop sleeps. The next observed price may jump past a limit.
Errors stop the connection and show an explanation; retry requires a user action.
The value shown while disconnected is based on the last quote and may be stale.

Updates are saved before being displayed. Conflicting writers or a failed save stop
the connection; the app never silently resets the balance. Open only one app instance
per account. Saved history and reports are local and unencrypted.

## The model and simulated fills

The model is standard-library logistic regression, not an LLM. It learns from up to
about 720 recent one-minute price bars, using trailing returns and volatility. The
uncommitted last Kraken candle is excluded. At setup, all available closed-bar labels
are used for training, then the model is frozen; entries wait for a newly closed candle.
Model weights and the latest processed candle persist, preventing repeated entries
from retries or restarts. Scores are not calibrated confidence or proven performance.

For a new signal, a virtual buy uses the newly fetched ask plus slippage; a virtual
sale uses the bid minus slippage. These are **receipt-time simulated fills**, not fills
at the past candle open, and are not exchange orders. Fees are charged on both sides.
Open-position value estimates the proceeds after exit costs. The agent polls roughly
every 20 seconds after a response; demo mode advances a synthetic minute every 3 seconds.

Quotes are marked by local receipt time (the ticker does not provide an exchange quote
timestamp). Closed-candle age, local receipt age, OHLC validity and bid/ask checks reject
obvious stale/invalid data but do not prove an exchange quote was freshly generated.
No backfilled trades are invented after downtime. Only the latest closed-bar signal
is considered on reconnect. Local protective exits run only at observed quotes.

The simulated engine does not model order-book depth, partial fills, exchange sizes,
market impact, funding, taxes or broker-specific execution. Virtual performance does
not establish real-world returns. Demo dates/prices are generated, not market history.

## Advanced tools and development

The original historical engine is preserved in `engine.py`. Launch its interface with
`python research_app.py` or the **Advanced research** button. See [RESEARCH.md](RESEARCH.md)
for CSV requirements, historical execution assumptions and the 60/40 backtest split.
That split applies to historical research, not to the forward practice model above.
Old research history stays in `~/TradingLabData/runs.sqlite3` and is not migrated or erased.

```bash
python -m unittest discover -s tests -v
python run_test.py --market Crypto --output report.json
python app.py
```

| File | Responsibility |
|---|---|
| `app.py` | Guided setup, practice dashboard, controls and background price polling |
| `practice.py` | Virtual-account state, ML decisions, sampled exits and atomic persistence |
| `market_data.py` | Read-only Kraken adapter and labeled deterministic demos |
| `research_app.py` | Original advanced historical interface |
| `engine.py` | Shared model and historical simulation engine |

## Project instructions

Read [AGENTS.md](AGENTS.md), [PRD.md](PRD.md),
[ARCHITECTURE-ESSENTIALS.md](ARCHITECTURE-ESSENTIALS.md),
[ARCHITECTURE.md](ARCHITECTURE.md) and [DECISIONS.md](DECISIONS.md).
[CLAUDE.md](CLAUDE.md) points Claude to the same shared instructions.

## What remains before real trading

Actual account eligibility and broker selection; authenticated paper/sandbox order
integration; exchange fill reconciliation, lot sizes and durable external order IDs;
independent strategy evaluation; then explicit user-authorized live activation and
broker-hosted protection for laptop downtime. No “connect account” button pretends
these unfinished integrations exist.

## Data-provider references

Implementation checked against official documentation:
[Kraken OHLC](https://docs.kraken.com/api-reference/market-data/get-ohlc-data) and
[Kraken ticker](https://docs.kraken.com/api-reference/market-data/get-ticker-information).

## Verification for this change

27 automated checks passed, including three Tk desktop flow tests in a Linux virtual
display. The desktop checks exercised setup, start, pause, closing a position, JSON
export, persisted restoration, small-screen scrolling and cancellation of a pending
entry after Pause. Onboarding and dashboard screens were visually inspected. An
actual Kraken public-data request also completed successfully.

These checks validate software behavior, not trading profitability. The Windows
launcher and appearance have not been tested on the user's laptop. Desktop tests
skip with an explicit reason when the test environment has no Tk display.
