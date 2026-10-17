"""Offline historical simulation. No network or brokerage execution code."""
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import csv
import math
import random
import statistics

@dataclass(frozen=True)
class Bar:
    date: str
    open: float
    high: float
    low: float
    close: float

@dataclass
class Config:
    capital: float = 10000
    allocation: float = 0.20
    stop: float = 0.02
    target: float = 0.04
    max_drawdown: float = 0.10
    fee: float = 0.001
    slippage: float = 0.0005
    strategy: str = 'ML classifier'

    def validate(self):
        values = asdict(self)
        if any(not math.isfinite(v) for v in values.values() if isinstance(v, (int, float))):
            raise ValueError('Settings must be finite numbers.')
        if not 1 <= self.capital <= 1e12:
            raise ValueError('Starting balance must be between 1 and 1 trillion.')
        for field in ('allocation', 'stop', 'target', 'max_drawdown'):
            if not 0 < getattr(self, field) <= 1:
                raise ValueError(field + ' must be greater than 0% and at most 100%.')
        if not 0 <= self.fee <= .1 or not 0 <= self.slippage <= .1:
            raise ValueError('Fees and slippage must be between 0% and 10%.')
        if self.strategy not in ('ML classifier', 'Trend rule'):
            raise ValueError('Unknown strategy.')


def validate_bars(bars):
    if not 150 <= len(bars) <= 100000:
        raise ValueError('Provide 150–100,000 OHLC rows.')
    previous = None
    for n, b in enumerate(bars, 2):
        try:
            dt = datetime.fromisoformat(b.date.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError(f'Row {n}: date must use ISO format, e.g. 2025-01-01.')
        if previous is not None:
            try:
                if dt <= previous:
                    raise ValueError(f'Row {n}: dates must be unique and increasing.')
            except TypeError:
                raise ValueError('Use one consistent timezone format for every row.')
        previous = dt
        vals = (b.open, b.high, b.low, b.close)
        if any(not math.isfinite(x) or x <= 0 for x in vals):
            raise ValueError(f'Row {n}: prices must be positive finite numbers.')
        if b.low > min(b.open, b.close) or b.high < max(b.open, b.close):
            raise ValueError(f'Row {n}: invalid OHLC range.')
    return bars


def read_csv(path):
    if __import__('os').path.getsize(path) > 30_000_000:
        raise ValueError('CSV is larger than the 30 MB limit.')
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError('CSV is empty.')
        reader.fieldnames = [x.strip().lower() for x in reader.fieldnames]
        if not {'date', 'open', 'high', 'low', 'close'}.issubset(reader.fieldnames):
            raise ValueError('CSV needs date,open,high,low,close columns.')
        bars = []
        for n, row in enumerate(reader, 2):
            if n > 100001:
                raise ValueError('CSV exceeds 100,000 rows.')
            try:
                bars.append(Bar(row['date'].strip(), *(float(row[k]) for k in ('open','high','low','close'))))
            except (ValueError, TypeError, AttributeError):
                raise ValueError(f'Row {n}: missing or non-numeric price.')
    return validate_bars(bars)


def sample(market):
    """Explicitly synthetic, deterministic examples, never market quotes."""
    rng = random.Random({'Crypto': 19, 'Forex': 25, 'Stocks': 41}[market])
    price = {'Crypto': 40000., 'Forex': 1.1, 'Stocks': 100.}[market]
    vol = {'Crypto': .025, 'Forex': .004, 'Stocks': .012}[market]
    bars = []
    for i in range(600):
        op = price * math.exp(rng.gauss(0, vol / 5))
        price = op * math.exp(rng.gauss(.0002 + .001 * math.sin(i / 38), vol))
        high = max(op, price) * (1 + rng.random() * vol)
        low = min(op, price) * (1 - rng.random() * vol)
        bars.append(Bar((datetime(2023, 1, 1)+timedelta(days=i)).date().isoformat(),op,high,low,price))
    return bars


def features(bars, i):
    c = bars[i].close
    returns = [math.log(bars[j].close / bars[j-1].close) for j in range(i-19, i+1)]
    return [math.log(c / bars[i-k].close) for k in (1, 3, 5, 10, 20)] + [statistics.pstdev(returns)]


class Model:
    """L2-regularized logistic regression; standardization fitted on training only."""
    def fit(self, xs, ys):
        self.mean = [statistics.mean(col) for col in zip(*xs)]
        self.std = [max(statistics.pstdev(col), 1e-8) for col in zip(*xs)]
        zs = [self.transform(x) for x in xs]
        self.w = [0.] * 7
        for _ in range(180):
            grad = [0.] * 7
            for z, y in zip(zs, ys):
                err = self.sigmoid(sum(a*b for a,b in zip(z,self.w))) - y
                for k in range(7):
                    grad[k] += err*z[k]
            for k in range(7):
                self.w[k] -= .08 * (grad[k]/len(zs) + (.015*self.w[k] if k else 0))
        return self

    @staticmethod
    def sigmoid(x):
        return 1 / (1 + math.exp(-max(-30, min(30, x))))

    def transform(self, x):
        return [1.] + [max(-8,min(8,(v-m)/s)) for v,m,s in zip(x,self.mean,self.std)]

    def predict(self, x):
        return self.sigmoid(sum(a*b for a,b in zip(self.transform(x), self.w)))


def signals(bars, split, strategy):
    model = None
    if strategy == 'ML classifier':
        # Training labels finish strictly before the first test bar.
        # Bound work to the last 2,000 training rows for inexpensive laptop runs.
        ids = range(max(20, split-2002), split-1)
        xs = [features(bars,i) for i in ids]
        ys = [int(bars[i+1].close > bars[i+1].open) for i in ids]
        model = Model().fit(xs, ys)
    result = {}
    for i in range(split-1, len(bars)-1):
        if model:
            p = model.predict(features(bars,i))
            action = 'BUY' if p >= .55 else 'SELL' if p <= .45 else 'HOLD'
            reason = f'ML up score {p:.1%}; buy ≥55%, sell ≤45%. Score is not calibrated confidence.'
        else:
            fast = statistics.mean(b.close for b in bars[i-9:i+1])
            slow = statistics.mean(b.close for b in bars[i-29:i+1])
            action = 'BUY' if fast > slow else 'SELL'
            p = None
            reason = f'10-bar average {fast:.6g}; 30-bar average {slow:.6g}.'
        result[i] = (action, p, reason)
    return result


def simulate(bars, cfg, supplied_signals=None):
    validate_bars(bars)
    cfg.validate()
    split = int(len(bars)*.6)
    sig = supplied_signals if supplied_signals is not None else signals(bars,split,cfg.strategy)
    cash, qty, cost, entry, peak = cfg.capital, 0., 0., 0., cfg.capital
    stop_price = target_price = 0.
    halted = False
    max_dd = fees = wins = losses = 0.
    trades, curve = [], []

    def sell(price, bar, reason):
        nonlocal cash, qty, cost, fees, wins, losses
        fill = price * (1-cfg.slippage)
        fee = qty*fill*cfg.fee
        net = qty*fill-fee
        pnl = net-cost
        cash += net
        fees += fee
        wins += pnl > 0
        losses += pnl <= 0
        trades.append(dict(date=bar.date,side='SELL',price=fill,quantity=qty,fee=fee,pnl=pnl,reason=reason))
        qty = cost = 0.

    for i in range(split,len(bars)):
        b = bars[i]
        action, score, reason = sig.get(i-1, ('HOLD',None,'No signal'))
        exited_at_open = False
        # Gap-aware stops execute at the open when the open is already below stop.
        if qty and b.open <= stop_price:
            sell(b.open,b,'Gap through stop')
            exited_at_open = True
        elif qty and b.open >= target_price:
            sell(target_price,b,'Take profit (conservative gap fill)')
            exited_at_open = True
        elif qty and action == 'SELL':
            sell(b.open,b,'Previous closed bar: '+reason)
        open_equity = cash+qty*b.open
        if open_equity <= peak*(1-cfg.max_drawdown):
            if qty:
                sell(b.open,b,'Drawdown halt at open')
            halted = True
        if not halted and not qty and not exited_at_open and action == 'BUY':
            fill = b.open*(1+cfg.slippage)
            budget = cash*cfg.allocation
            qty = budget/(fill*(1+cfg.fee))
            fee = qty*fill*cfg.fee
            cost = qty*fill+fee
            cash -= cost
            fees += fee
            entry = fill
            stop_price, target_price = entry*(1-cfg.stop), entry*(1+cfg.target)
            trades.append(dict(date=b.date,side='BUY',price=fill,quantity=qty,fee=fee,pnl=None,reason='Previous closed bar: '+reason))
        if qty:
            # OHLC cannot tell intrabar order: stop wins if both levels are hit.
            if b.low <= stop_price:
                sell(min(b.open,stop_price),b,'Stop loss (stop first if both touched)')
            elif b.high >= target_price:
                sell(target_price,b,'Take profit')
        equity = cash+qty*b.close
        peak = max(peak,equity)
        dd = 1-equity/peak
        if dd >= cfg.max_drawdown:
            if qty:
                sell(b.close,b,'Drawdown halt at bar close')
            halted = True
            equity = cash
        if i == len(bars)-1 and qty:
            sell(b.close,b,'End-of-test liquidation')
            equity = cash
        peak = max(peak,equity)
        dd = max(0.,1-equity/peak)
        max_dd = max(max_dd,dd)
        curve.append(dict(date=b.date,equity=equity,drawdown=dd,price=b.close,signal=action,score=score,halted=halted))
    # Comparable all-cash buy-and-hold reference over the same test period, costs included.
    bench_qty = cfg.capital/(bars[split].open*(1+cfg.slippage)*(1+cfg.fee))
    benchmark = bench_qty*bars[-1].close*(1-cfg.slippage)*(1-cfg.fee)
    return dict(config=asdict(cfg),train_rows=split,test_rows=len(bars)-split,
                train_end=bars[split-1].date,test_start=bars[split].date,
                final_equity=cash,net_pnl=cash-cfg.capital,return_pct=(cash/cfg.capital-1)*100,
                max_drawdown_pct=max_dd*100,fees=fees,closed_trades=int(wins+losses),
                win_rate_pct=100*wins/(wins+losses) if wins+losses else None,
                benchmark_return_pct=(benchmark/cfg.capital-1)*100,halted=halted,
                trades=trades,curve=curve)
