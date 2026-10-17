# Architecture essentials

Read this first for technical orientation, then the relevant code and
[ARCHITECTURE.md](ARCHITECTURE.md). This is a summary, not a second specification.

- Current product: local **historical simulator**, not an autonomous broker-connected bot.
- Stack: Python 3.10+, standard library, Tk desktop UI, SQLite history. No pip/GPU/API requirement.
- `engine.py` owns validation, ML, strategies and simulation. Keep it independent of Tk,
  network services and broker orders. `app.py` owns UI and GUI report persistence.
- Worker thread runs simulation; queue and main-thread polling update Tk widgets.
- Three market workspaces share a generic unleveraged long/flat engine. Market-specific
  execution conventions, feeds and accounts are not implemented.
- Data is explicitly synthetic or user-imported. Preserve provenance through export.
- Split chronologically: 60% train / 40% test. Fit scaling/model only on training data;
  no test labels in training. Previous-close signal → next-open execution.
- Model: logistic regression, not an LLM; scores are not calibrated confidence.
- Account for entry/exit fees and slippage. Document gap and same-bar stop/target behavior.
- Risk thresholds are simulation controls, not guaranteed losses. Reported drawdown
  excludes intrabar peaks/troughs. Buy-and-hold is not allocation-matched.
- GUI history: `~/TradingLabData/runs.sqlite3`. Completed reports persist, datasets do not.
- Closing the app stops all activity; no unattended trading exists.
- Never put credentials or real account details in this public repo or report exports.
- Significant decisions belong in [DECISIONS.md](DECISIONS.md); preserve old records
  and supersede explicitly when a choice changes.

Commands from repository root:

```bash
python app.py
python -m unittest discover -s tests -v
python run_test.py --market Crypto --output report.json
```

Unresolved: instrument, broker, real-data provider, account eligibility, real-money
limits, independent strategy evaluation and Windows GUI acceptance. See [PRD.md](PRD.md).
