"""Desktop flow smoke checks. Skipped when Tk cannot open a display."""
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
import tkinter as tk
from app import App
from practice import Store
from market_data import demo_snapshot

class DesktopTests(unittest.TestCase):
    def setUp(self):
        try:self.root=tk.Tk()
        except tk.TclError as exc:self.skipTest('Tk display unavailable: '+str(exc))
        self.temp=tempfile.TemporaryDirectory()
        self.app=App(self.root,Store(Path(self.temp.name)/'practice.db'))
        self.root.update()

    def tearDown(self):
        if hasattr(self,'app'):
            self.app.closed=True
            self.root.after_cancel(self.app.poll_id)
            self.root.destroy()
            self.temp.cleanup()

    def pump(self,condition,seconds=4):
        deadline=time.monotonic()+seconds
        while not condition() and time.monotonic()<deadline:
            self.root.update();time.sleep(.01)
        self.assertTrue(condition(),'UI condition did not complete')
        self.root.update()

    def test_setup_start_pause_close_export_and_restore(self):
        self.app.create();self.root.update()
        self.assertIsNotNone(self.app.account)
        self.app.start()
        self.pump(lambda:bool(self.app.account.model) and not self.app.busy)
        # Deterministic model fixture for exercising the buy/close UI path.
        self.app.change(lambda a:a.model.update(w=[10]+[0]*6))
        self.app.next_fetch=0
        self.pump(lambda:self.app.account.quantity>0 and not self.app.busy)
        self.app.pause()
        self.assertEqual(self.app.account.status,'paused')
        self.assertGreater(self.app.account.quantity,0)
        with patch('app.messagebox.askyesno',return_value=True):self.app.sell()
        self.pump(lambda:self.app.account.quantity==0 and not self.app.busy)
        self.assertEqual(self.app.account.status,'paused')
        destination=str(Path(self.temp.name)/'report.json')
        with patch('app.filedialog.asksaveasfilename',return_value=destination):self.app.export()
        self.assertTrue(Path(destination).exists())
        restored=self.app.store.latest('Crypto')
        self.assertAlmostEqual(restored.cash,self.app.account.cash)
        self.assertEqual(restored.status,'paused')

    def test_pause_discards_pending_entry(self):
        self.app.create()
        self.app.change(lambda a:a.model.update(mean=[0]*6,std=[1]*6,w=[10]+[0]*6))
        release=threading.Event()
        self.app.fetcher=lambda a:(release.wait(2),demo_snapshot(a.market,a.demo_step))[1]
        self.app.start()
        self.pump(lambda:self.app.busy)
        self.app.pause();release.set()
        self.app.connected=False
        self.pump(lambda:not self.app.busy)
        self.assertEqual(self.app.account.quantity,0)
        self.assertEqual(self.app.account.status,'paused')
        self.assertFalse(any(e['kind']=='BUY' for e in self.app.account.events))

    def test_market_setup_and_small_screen_scroll(self):
        self.root.geometry('860x620');self.root.update()
        self.app.switch('Forex');self.root.update()
        self.assertEqual(self.app.mode.get(),'demo')
        self.app.create();self.root.update()
        self.assertEqual(self.app.account.market,'Forex')
        self.assertEqual(self.app.account.mode,'demo')
        self.app.switch('Stocks');self.root.update()
        self.assertIsNone(self.app.account)
        self.assertGreater(self.app.body.winfo_reqheight(),0)
        self.app.scroll.yview_moveto(1);self.root.update()

if __name__=='__main__':unittest.main()
