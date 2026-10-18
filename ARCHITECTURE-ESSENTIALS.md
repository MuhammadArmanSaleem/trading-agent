# Architecture essentials

- Default entry: `app.py`, a beginner Tk **virtual-money practice desk**.
- `practice.py`: durable virtual account, locally trained model, simulated receipts,
  position exits and SQLite store. No authenticated account/order execution.
- `market_data.py`: read-only Kraken OHLC/ticker requests and deterministic demos.
  Public Bitcoin prices are the only real feed. Forex/Stocks are demos.
- `research_app.py`: prior advanced historical UI, still using `engine.py`.
- `engine.py`: shared logistic model, features and original backtest engine.
- Python 3.10+, Tk, standard library; no pip, GPU or paid AI requirement.
- Network/model work runs in a worker. Tk and database commit/display run on the main
  thread. Epoch tokens discard late results after pause/switch/close actions.
- Practice model trains on known closed bars then waits for a new candle; weights
  stay frozen and persist. Current Kraken OHLC frame is never used as a closed bar.
- Practice fills use fresh receipt-time bid/ask with fee/slippage; no historical-open
  fill is invented. Snapshot checks reject stale/invalid data; no silent demo fallback.
- Pause disables entries but leaves sampled exits active while connected. Disconnection
  stops all monitoring. Reopening restores holdings and requires explicit reconnect.
- SQLite `practice.sqlite3` saves whole account/events atomically with optimistic
  revisions. Failed/stale saves are not published. Research `runs.sqlite3` stays intact.
- Historical backtests still use chronological 60/40 train/test, previous-close signals
  and next-open fills. Do not conflate this with forward-practice methodology.
- Models have no proven trading edge. Risk thresholds are not guaranteed loss caps.
- All values are virtual quote-currency units. No leverage or broker-specific sizing.
- Do not put credentials/account data in source, reports or logs.

Commands: `python app.py`, `python research_app.py`,
`python -m unittest discover -s tests -v`.

Read [ARCHITECTURE.md](ARCHITECTURE.md) for details, [PRD.md](PRD.md) for scope and
[DECISIONS.md](DECISIONS.md) for choices. Real broker execution is still unimplemented.
