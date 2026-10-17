"""Headless run: python run_test.py --market Forex --csv your-data.csv"""
import argparse
import json
from engine import Config, sample, read_csv, simulate

if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--market',choices=['Crypto','Forex','Stocks'],default='Crypto')
    p.add_argument('--csv')
    p.add_argument('--strategy',choices=['ML classifier','Trend rule'],default='ML classifier')
    p.add_argument('--output',default='report.json')
    a=p.parse_args()
    r=simulate(read_csv(a.csv) if a.csv else sample(a.market),Config(strategy=a.strategy))
    r.update(market=a.market,source=a.csv or 'SYNTHETIC DEMO — not market data')
    with open(a.output,'w',encoding='utf-8') as f:json.dump(r,f,indent=2)
    print(json.dumps({k:v for k,v in r.items() if k not in ('curve','trades')},indent=2))
