import copy
import math
import tempfile
import time
import unittest
from pathlib import Path
from dataclasses import replace, asdict
from unittest.mock import patch
from market_data import Snapshot,FeedError,demo_snapshot,parse_kraken
from practice import Account,Store,transact,FEE,SLIPPAGE


def prepared():
    a=Account.create('Crypto','demo')
    a.model={'mean':[0]*6,'std':[1]*6,'w':[10]+[0]*6}
    a.start()
    return a

class PracticeTests(unittest.TestCase):
    def test_buy_costs_and_same_candle_idempotency(self):
        a=prepared();s=demo_snapshot('Crypto',0)
        a.process(s)
        self.assertAlmostEqual(a.cash,9000)
        self.assertEqual(len([e for e in a.events if e['kind']=='BUY']),1)
        a.process(s)
        self.assertEqual(len([e for e in a.events if e['kind']=='BUY']),1)
        self.assertLess(a.equity(),a.initial)

    def test_pause_blocks_entries_but_preserves_exits(self):
        a=prepared();a.pause();a.process(demo_snapshot('Crypto',0))
        self.assertEqual(a.quantity,0)
        a.start();a.process(demo_snapshot('Crypto',1));self.assertGreater(a.quantity,0)
        a.pause()
        s=demo_snapshot('Crypto',2);s=replace(s,bid=a.entry*.95,ask=a.entry*.9501)
        a.process(s)
        self.assertEqual(a.quantity,0)
        self.assertEqual(a.status,'paused')

    def test_manual_close_reconciles_pnl_and_stays_paused(self):
        a=prepared();s=demo_snapshot('Crypto',0);a.process(s)
        a.close_position(s)
        self.assertEqual(a.quantity,0)
        self.assertEqual(a.status,'paused')
        self.assertAlmostEqual(a.cash-a.initial,a.realized)
        self.assertAlmostEqual(sum(e.get('fee',0) for e in a.events),a.fees)

    def test_halt_cannot_restart_or_reenter(self):
        a=prepared();a.allocation=.25;a.process(demo_snapshot('Crypto',0))
        s=replace(demo_snapshot('Crypto',1),bid=a.entry*.5,ask=a.entry*.5001)
        a.process(s)
        self.assertTrue(a.halted)
        self.assertEqual(a.quantity,0)
        self.assertEqual(a.status,'halted')
        with self.assertRaises(ValueError):a.start()
        a.process(demo_snapshot('Crypto',2))
        self.assertEqual(a.quantity,0)

    def test_restart_preserves_holdings_model_and_consumed_signal(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/'state.db');a=prepared();a.process(demo_snapshot('Crypto',0));store.save(a)
            b=store.latest('Crypto')
            self.assertEqual(b.quantity,a.quantity)
            self.assertEqual(b.cash,a.cash)
            self.assertEqual(b.model,a.model)
            self.assertEqual(b.last_candle,a.last_candle)
            self.assertEqual(b.status,'paused')

    def test_stale_tick_and_wrong_source_never_committed(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/'state.db');a=prepared();store.save(a)
            old=asdict(a)
            s=replace(demo_snapshot('Crypto',0),received_at=time.time()-100)
            with self.assertRaises(FeedError):transact(store,a,lambda x:x.process(s))
            self.assertEqual(asdict(a),old)
            self.assertEqual(store.latest('Crypto').quantity,0)
            s=replace(demo_snapshot('Crypto',0),synthetic=False)
            with self.assertRaises(FeedError):transact(store,a,lambda x:x.process(s))

    def test_save_failure_does_not_publish_trade(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/'state.db');a=prepared();store.save(a)
            with patch.object(store,'save',side_effect=OSError('Disk full')):
                with self.assertRaises(OSError):transact(store,a,lambda x:x.process(demo_snapshot('Crypto',0)))
            self.assertEqual(a.quantity,0)
            self.assertEqual(store.latest('Crypto').quantity,0)

    def test_optimistic_revision_blocks_second_writer(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/'state.db');a=prepared();store.save(a);b=copy.deepcopy(a)
            store.save(a)
            with self.assertRaises(RuntimeError):store.save(b)

    def test_forward_setup_waits_for_new_candle(self):
        a=Account.create('Crypto','demo');a.start()
        a.process(demo_snapshot('Crypto',0))
        self.assertEqual(a.quantity,0)
        self.assertTrue(a.model)
        self.assertEqual(a.last_candle,demo_snapshot('Crypto',0).bars[-1].date)

    def test_no_future_demo_data_enters_model_fit(self):
        a=Account.create('Crypto','demo');a.start();a.process(demo_snapshot('Crypto',0))
        weights=copy.deepcopy(a.model)
        a.process(demo_snapshot('Crypto',1))
        self.assertEqual(a.model,weights)

    def test_settings_and_market_limits(self):
        for args in [('Forex','prices'),('Stocks','prices'),('No','demo')]:
            with self.assertRaises(ValueError):Account.create(*args)
        for kwargs in [dict(capital=math.nan),dict(allocation=.8),dict(loss_limit=0),dict(capital=10)]:
            with self.assertRaises(ValueError):Account.create('Crypto','demo',**kwargs)

class FeedTests(unittest.TestCase):
    def fixture(self):
        now=math.floor(time.time()/60)*60+20
        start=now-now%60-160*60
        rows=[[start+i*60,'100','101','99','100','100','1',1] for i in range(161)]
        return {'XXBTZUSD':rows,'last':rows[-1][0]},{'XXBTZUSD':{'b':['100'],'a':['100.1']}},now

    def test_discards_unfinished_last_candle(self):
        o,t,now=self.fixture();o['XXBTZUSD'][-1][4]='999999'
        s=parse_kraken(o,t,now)
        self.assertEqual(len(s.bars),160)
        self.assertEqual(s.bars[-1].close,100)
        self.assertFalse(s.synthetic)

    def test_rejects_stale_candles_and_bad_quotes(self):
        o,t,now=self.fixture()
        with self.assertRaises(FeedError):parse_kraken(o,t,now+500)
        for bid in ('nan','-1','102'):
            t['XXBTZUSD']['b']=[bid]
            with self.assertRaises(FeedError):parse_kraken(o,t,now)

    def test_all_demos_valid_and_deterministic(self):
        for market in ('Crypto','Forex','Stocks'):
            a=demo_snapshot(market,7);a.check()
            b=demo_snapshot(market,7)
            self.assertEqual(a.bars,b.bars)
            self.assertEqual(a.bid,b.bid)

if __name__=='__main__':unittest.main()
