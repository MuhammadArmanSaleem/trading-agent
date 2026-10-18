"""Read-only public data. There are deliberately no authenticated/order endpoints."""
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import json
import math
import random
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from engine import Bar, validate_bars

class FeedError(ValueError):
    pass

@dataclass(frozen=True)
class Snapshot:
    bars: list
    bid: float
    ask: float
    received_at: float
    candle_end: float
    source: str
    symbol: str
    synthetic: bool = False

    def check(self, now=None):
        now = time.time() if now is None else now
        if not all(math.isfinite(v) for v in (self.bid,self.ask,self.received_at,self.candle_end)):
            raise FeedError('Price data contains invalid numbers.')
        if not 0 < self.bid <= self.ask or self.ask/self.bid > 1.05:
            raise FeedError('Price quote is invalid or the buy/sell price gap is too large.')
        if not -5 <= now-self.received_at <= 25:
            raise FeedError('Price update is too old. Check your connection and computer clock.')
        if not self.synthetic and not -5 <= now-self.candle_end <= 180:
            raise FeedError('Market candles are stale. No practice orders will be filled.')
        validate_bars(self.bars)


def public_get(endpoint, **params):
    if endpoint not in ('OHLC', 'Ticker'):
        raise FeedError('Only public price endpoints are supported.')
    url='https://api.kraken.com/0/public/'+endpoint+'?'+urlencode(params)
    request=Request(url,headers={'User-Agent':'TradingLab/2.0 (read-only public market data)','Cache-Control':'no-cache'})
    try:
        with urlopen(request,timeout=8) as response:
            raw=response.read(2_000_001)
        if len(raw)>2_000_000:
            raise FeedError('Market response is too large.')
        payload=json.loads(raw)
        if not isinstance(payload,dict) or payload.get('error'):
            raise FeedError('Market provider returned an error. Try again later.')
        if not isinstance(payload.get('result'),dict):
            raise FeedError('Market provider returned an unexpected response.')
        return payload['result']
    except FeedError:
        raise
    except Exception as exc:
        raise FeedError('Cannot reach the price provider. Check internet access and retry.') from exc


def parse_kraken(ohlc, ticker, received_at):
    """Drop the always-uncommitted last OHLC frame, even if its timestamp looks old."""
    try:
        rows=ohlc['XXBTZUSD']
        quote=ticker['XXBTZUSD']
        if not isinstance(rows,list) or len(rows)<151:
            raise FeedError('Not enough recent market history to prepare the model.')
        closed=rows[:-1]
        bars=[Bar(datetime.fromtimestamp(float(row[0]),timezone.utc).isoformat(),
                  *(float(row[j]) for j in (1,2,3,4))) for row in closed]
        snapshot=Snapshot(bars,float(quote['b'][0]),float(quote['a'][0]),received_at,
                          float(closed[-1][0])+60,'Kraken public prices','BTC/USD')
        snapshot.check(received_at)
        return snapshot
    except (KeyError,IndexError,TypeError,ValueError,OverflowError) as exc:
        if isinstance(exc,FeedError):raise
        raise FeedError('Market data format is unexpected. Practice trading is blocked.') from exc


def kraken_snapshot():
    # Reading candles before the quote avoids intentionally filling using an older quote.
    candles=public_get('OHLC',pair='XBTUSD',interval=1)
    quotes=public_get('Ticker',pair='XBTUSD')
    return parse_kraken(candles,quotes,time.time())


def demo_snapshot(market, step, now=None):
    """Synthetic minute bars; deterministic across restarts, accelerated by the UI."""
    now=time.time() if now is None else now
    initial,vol,seed={'Crypto':(40000,.008,19),'Forex':(1.1,.001,25),'Stocks':(100,.004,41)}[market]
    # Bound generation work and seed a rolling window deterministically by demo step.
    rng=random.Random(seed)
    price=initial
    bars=[]
    total=220+step
    if total>20000:raise FeedError('Demo finished. Create a fresh practice account to continue.')
    start=datetime(2024,1,1,tzinfo=timezone.utc)
    for i in range(total):
        op=price
        price=op*math.exp(rng.gauss(.0012*math.sin(i/18),vol))
        b=Bar((start+timedelta(minutes=i)).isoformat(),op,max(op,price)*(1+vol/2),min(op,price)*(1-vol/2),price)
        if i>=total-220:bars.append(b)
    snapshot=Snapshot(bars,price*.9998,price*1.0002,now,now,
                      'Generated demo prices — not a real market',market+' demo',True)
    snapshot.check(now)
    return snapshot
