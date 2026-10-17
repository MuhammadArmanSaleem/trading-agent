import math
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from datetime import datetime,timedelta
from engine import Bar,Config,simulate,signals,sample,read_csv,validate_bars

def flat():
    return [Bar((datetime(2024,1,1)+timedelta(days=i)).date().isoformat(),100,100,100,100) for i in range(150)]

class EngineTests(unittest.TestCase):
    def test_fee_accounting(self):
        r=simulate(flat(),Config(allocation=1,fee=.01,slippage=0),{89:('BUY',None,'test')})
        expected=10000/1.01*.99
        self.assertAlmostEqual(r['final_equity'],expected)
        self.assertAlmostEqual(r['fees'],10000-expected)
        self.assertEqual(r['closed_trades'],1)
        self.assertAlmostEqual(sum(t['pnl'] or 0 for t in r['trades']),r['net_pnl'])

    def test_stop_before_target(self):
        b=flat();b[90]=replace(b[90],high=110,low=90)
        r=simulate(b,Config(fee=0,slippage=0),{89:('BUY',None,'test')})
        self.assertEqual(r['trades'][1]['price'],98)
        self.assertIn('Stop loss',r['trades'][1]['reason'])

    def test_gap_stop_and_no_same_bar_reentry(self):
        b=flat();b[91]=replace(b[91],open=80,high=82,low=79,close=80)
        r=simulate(b,Config(fee=0,slippage=0),{89:('BUY',None,'test'),90:('BUY',None,'test')})
        self.assertEqual(r['trades'][1]['price'],80)
        self.assertEqual(len(r['trades']),2)

    def test_drawdown_halt(self):
        b=flat();b[90]=replace(b[90],low=90,close=90)
        r=simulate(b,Config(allocation=1,stop=.5,max_drawdown=.05,fee=0,slippage=0),{i:('BUY',None,'test') for i in range(89,149)})
        self.assertTrue(r['halted'])
        self.assertEqual(len(r['trades']),2)
        self.assertAlmostEqual(r['final_equity'],9000)

    def test_no_signal_no_cost(self):
        r=simulate(flat(),Config(),{})
        self.assertEqual(r['final_equity'],10000)
        self.assertEqual(r['fees'],0)
        self.assertEqual(r['trades'],[])
        self.assertIsNone(r['win_rate_pct'])

    def test_no_future_data_leakage(self):
        b=sample('Crypto');split=int(len(b)*.6)
        s1=signals(b,split,'ML classifier')
        changed=list(b)
        for i in range(500,len(b)):
            x=b[i];changed[i]=Bar(x.date,x.open*3,x.high*3,x.low*3,x.close*3)
        s2=signals(changed,split,'ML classifier')
        self.assertEqual({i:v for i,v in s1.items() if i<500},{i:v for i,v in s2.items() if i<500})

    def test_next_open_execution(self):
        b=flat();b[90]=replace(b[90],open=105,high=105,close=105)
        r=simulate(b,Config(fee=0,slippage=0),{89:('BUY',None,'test')})
        self.assertEqual(r['trades'][0]['date'],b[90].date)
        self.assertEqual(r['trades'][0]['price'],105)

    def test_invalid_data_settings(self):
        for kwargs in [dict(capital=math.nan),dict(fee=-1),dict(allocation=2),dict(stop=0),dict(slippage=math.inf)]:
            with self.assertRaises(ValueError):Config(**kwargs).validate()
        b=flat();b[1]=replace(b[1],date=b[0].date)
        with self.assertRaises(ValueError):validate_bars(b)
        b=flat();b[1]=replace(b[1],close=math.nan)
        with self.assertRaises(ValueError):validate_bars(b)
        b=flat();b[1]=replace(b[1],low=101)
        with self.assertRaises(ValueError):validate_bars(b)

    def test_csv(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input.csv';p.write_text('date,close\n2024-01-01,100\n')
            with self.assertRaises(ValueError):read_csv(p)
            p.write_text('date,open,high,low,close\n'+'\n'.join(f'{b.date},100,100,100,100' for b in flat()))
            self.assertEqual(len(read_csv(p)),150)

    def test_all_market_strategy_combinations(self):
        for market in ('Crypto','Forex','Stocks'):
            for strategy in ('ML classifier','Trend rule'):
                r=simulate(sample(market),Config(strategy=strategy))
                self.assertEqual(r['test_rows'],240)
                self.assertTrue(math.isfinite(r['final_equity']))
                self.assertGreater(r['final_equity'],0)
                self.assertAlmostEqual(sum(t['pnl'] or 0 for t in r['trades']),r['net_pnl'])

if __name__=='__main__':unittest.main()
