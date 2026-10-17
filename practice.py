"""Persistent local paper trading. No account or order execution at a broker."""
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
import copy
import json
import math
from pathlib import Path
import sqlite3
import time
import uuid
from engine import Model, features
from market_data import FeedError

FEE=.001
SLIPPAGE=.0005

def utc(ts=None):
    return datetime.fromtimestamp(time.time() if ts is None else ts,timezone.utc).isoformat()

@dataclass
class Account:
    id: str
    market: str
    mode: str
    initial: float
    allocation: float
    loss_limit: float
    cash: float
    peak: float
    created: str
    quantity: float = 0
    cost: float = 0
    entry: float = 0
    fees: float = 0
    realized: float = 0
    last_bid: float = 0
    last_quote_at: float = 0
    last_candle: str = ''
    model: dict = field(default_factory=dict)
    demo_step: int = 0
    status: str = 'paused'
    halted: bool = False
    explanation: str = 'Ready. Start practice to prepare the model and watch prices.'
    last_score: float | None = None
    events: list = field(default_factory=list)
    history: list = field(default_factory=list)
    revision: int = 0

    @classmethod
    def create(cls,market,mode,capital=10000,allocation=.1,loss_limit=.05):
        if market not in ('Crypto','Forex','Stocks') or mode not in ('demo','prices'):
            raise ValueError('Unknown market or practice source.')
        if mode=='prices' and market!='Crypto':
            raise ValueError('Real-price practice currently supports Bitcoin only.')
        if not all(math.isfinite(x) for x in (capital,allocation,loss_limit)):
            raise ValueError('Use finite numbers for practice settings.')
        if not 100<=capital<=1000000 or not .01<=allocation<=.25 or not .01<=loss_limit<=.2:
            raise ValueError('Practice money: 100–1,000,000; per trade: 1–25%; drop limit: 1–20%.')
        return cls(str(uuid.uuid4()),market,mode,capital,allocation,loss_limit,capital,capital,utc())

    def equity(self):
        return self.cash+self.quantity*self.last_bid*(1-SLIPPAGE)*(1-FEE)

    def event(self,kind,reason,**details):
        self.events.append(dict(time=utc(),kind=kind,reason=reason,**details))

    def prepare(self,snapshot):
        snapshot.check()
        if self.model:return
        rows=snapshot.bars
        ids=range(20,len(rows)-1)
        xs=[features(rows,i) for i in ids]
        ys=[int(rows[i+1].close>rows[i+1].open) for i in ids]
        model=Model().fit(xs,ys)
        self.model=dict(mean=model.mean,std=model.std,w=model.w)
        # Training consumes all known labels. Don't trade the same last bar used at setup;
        # wait for a newly closed bar, rather than showing an in-sample entry as forward evidence.
        self.last_candle=rows[-1].date
        self.event('READY','Local model prepared. Waiting for a new price candle; no trade is required.')

    def start(self):
        if self.halted:raise ValueError('The loss limit stopped this account. Review it and create a new practice account.')
        self.status='running'
        self.explanation='Watching prices. The bot may stay in cash while waiting for its signal.'
        self.event('START','New practice trades enabled. No real money is connected.')

    def pause(self):
        self.status='paused'
        self.explanation='New trades paused. Existing practice holdings still update and exit rules run while the app is open.'
        self.event('PAUSE','New entries paused; open practice holdings are not automatically sold.')

    def fail(self,message):
        self.status='attention'
        self.explanation=message+' Trading is paused. Retry when ready; positions have not been silently closed.'
        self.event('ATTENTION',self.explanation)

    def _sell(self,bid,reason):
        if not self.quantity:return
        fill=bid*(1-SLIPPAGE)
        gross=self.quantity*fill
        fee=gross*FEE
        pnl=gross-fee-self.cost
        self.cash+=gross-fee
        self.fees+=fee
        self.realized+=pnl
        self.event('SELL',reason,price=fill,quantity=self.quantity,fee=fee,pnl=pnl)
        self.quantity=self.cost=self.entry=0

    def close_position(self,snapshot):
        self._validate_snapshot(snapshot)
        self.status='paused'
        self.last_bid=snapshot.bid
        self.last_quote_at=snapshot.received_at
        self._sell(snapshot.bid,'You closed the virtual position at a fresh quote. New trades remain paused.')
        self.explanation='Practice position closed. Your virtual balance is now cash.'
        self._mark(snapshot)

    def _validate_snapshot(self,snapshot):
        snapshot.check()
        if snapshot.synthetic!=(self.mode=='demo'):
            raise FeedError('Price source does not match this practice account.')
        expected='BTC/USD' if self.mode=='prices' else self.market+' demo'
        if snapshot.symbol!=expected:raise FeedError('Price symbol does not match this account.')

    def process(self,snapshot):
        self._validate_snapshot(snapshot)
        if not self.model:self.prepare(snapshot)
        self.last_bid=snapshot.bid
        self.last_quote_at=snapshot.received_at
        exited=False
        equity=self.equity()
        self.peak=max(self.peak,equity)
        # Check existing position exits before model actions, including while entries are paused.
        if equity<=self.peak*(1-self.loss_limit):
            self._sell(snapshot.bid,'Account value fell through its practice drop limit.')
            self.halted=True
            self.status='halted'
            self.explanation='Loss control stopped this practice account. Review the results before creating another.'
            exited=True
        elif self.quantity and snapshot.bid<=self.entry*.98:
            self._sell(snapshot.bid,'Price dropped 2% from entry; the practice stop closed the position.')
            self.explanation='A practice stop closed the position after a price drop.'
            exited=True
        elif self.quantity and snapshot.bid>=self.entry*1.04:
            self._sell(snapshot.bid,'Price rose 4% from entry; the practice target closed the position.')
            self.explanation='A practice target closed the position after a price rise.'
            exited=True
        candle=snapshot.bars[-1].date
        if candle!=self.last_candle:
            if self.last_candle and candle<self.last_candle:
                raise FeedError('Out-of-order market candle received.')
            self.last_candle=candle
            m=Model();m.mean=self.model['mean'];m.std=self.model['std'];m.w=self.model['w']
            score=m.predict(features(snapshot.bars,len(snapshot.bars)-1))
            self.last_score=score
            if not exited and not self.halted:
                if self.quantity and score<=.45:
                    self._sell(snapshot.bid,'The model changed direction, so the virtual position was closed.')
                    self.explanation='The model requested an exit. Virtual holdings were sold.'
                elif self.status=='running' and not self.quantity and score>=.55:
                    fill=snapshot.ask*(1+SLIPPAGE)
                    budget=self.cash*self.allocation
                    self.quantity=budget/(fill*(1+FEE))
                    fee=self.quantity*fill*FEE
                    self.cost=budget
                    self.entry=fill
                    self.cash-=budget
                    self.fees+=fee
                    self.explanation='Opened one practice position within your spending limit. No real order was sent.'
                    self.event('BUY',self.explanation,price=fill,quantity=self.quantity,fee=fee,pnl=None)
                elif self.status=='running':
                    self.explanation=('Holding the practice position and watching exit limits.' if self.quantity else 'Waiting in cash. The model has not requested an entry.')
        self._mark(snapshot)

    def _mark(self,snapshot):
        value=self.equity()
        self.peak=max(self.peak,value)
        self.history.append(dict(time=utc(snapshot.received_at),equity=value,price=snapshot.bid))
        self.history=self.history[-3000:]

    def report(self):
        result=asdict(self)
        result.update(schema_version=1,practice_only=True,currency='USD (virtual)',
                      source='Kraken public prices' if self.mode=='prices' else 'SYNTHETIC DEMO',
                      equity_estimate=self.equity(),fee_each_side=FEE,slippage_each_side=SLIPPAGE,
                      stop_distance=.02,target_distance=.04)
        return result


class Store:
    """Whole-state and event changes commit atomically; revision prevents stale writers."""
    def __init__(self,path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS practice (id TEXT PRIMARY KEY, market TEXT, updated TEXT, revision INTEGER, state TEXT)')

    def save(self,account):
        new_revision=account.revision+1
        data=asdict(account);data['revision']=new_revision
        with sqlite3.connect(self.path,timeout=5) as db:
            if account.revision==0:
                db.execute('INSERT INTO practice VALUES (?,?,?,?,?)',(account.id,account.market,utc(),new_revision,json.dumps(data,allow_nan=False)))
            else:
                cursor=db.execute('UPDATE practice SET updated=?,revision=?,state=? WHERE id=? AND revision=?',
                                  (utc(),new_revision,json.dumps(data,allow_nan=False),account.id,account.revision))
                if cursor.rowcount!=1:raise RuntimeError('This account changed in another window. Close this window and reopen the app.')
        account.revision=new_revision

    def latest(self,market):
        with sqlite3.connect(self.path) as db:
            row=db.execute('SELECT state FROM practice WHERE market=? ORDER BY updated DESC LIMIT 1',(market,)).fetchone()
        if not row:return None
        a=Account(**json.loads(row[0]))
        a.status='halted' if a.halted else 'paused'
        a.explanation='Restored from this laptop. New trades are paused; press Start to reconnect. No trades were made while closed.'
        return a

    def reports(self):
        with sqlite3.connect(self.path) as db:
            return [(row[0],json.loads(row[1])) for row in db.execute('SELECT updated,state FROM practice ORDER BY updated DESC LIMIT 100')]


def transact(store,account,change):
    """Publish in-memory changes only after durable saving succeeds."""
    candidate=copy.deepcopy(account)
    change(candidate)
    store.save(candidate)
    return candidate
