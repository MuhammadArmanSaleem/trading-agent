"""Trading Lab: local multi-market research desktop application."""
import csv
import json
import queue
import sqlite3
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime, timezone
from pathlib import Path
from engine import Config, sample, read_csv, simulate

BG, PANEL, FG, MUTED, ACCENT = '#0b1220', '#142034', '#e8eff8', '#94a6bd', '#4cdbc2'
DATA = Path.home() / 'TradingLabData'

class App:
    def __init__(self, root):
        self.root = root
        root.title('Trading Lab • Local research desk')
        root.geometry('1180x800')
        root.minsize(960,700)
        root.configure(bg=BG)
        self.busy = False
        self.q = queue.Queue()
        self.replay_id = None
        self.states = {m:dict(bars=sample(m),source='SYNTHETIC DEMO — not market data',result=None) for m in ('Crypto','Forex','Stocks')}
        self.market = tk.StringVar(value='Crypto')
        self.strategy = tk.StringVar(value='ML classifier')
        self.source = tk.StringVar()
        self.status = tk.StringVar(value='Offline research only. No exchange account, orders, or live price feed connected.')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.',background=PANEL,foreground=FG,fieldbackground=BG,font=('Segoe UI',10))
        style.configure('TButton',padding=(12,8))
        style.map('TButton',background=[('active','#263d58')])
        style.configure('Treeview',background=BG,fieldbackground=BG,foreground=FG,rowheight=26)
        style.configure('Treeview.Heading',background=PANEL,foreground=MUTED)
        style.configure('TCombobox',fieldbackground=BG)
        top = tk.Frame(root,bg=BG)
        top.pack(fill='x',padx=24,pady=(20,10))
        tk.Label(top,text='TRADING LAB',fg=ACCENT,bg=BG,font=('Segoe UI',23,'bold')).pack(side='left')
        tk.Label(top,text='HISTORICAL SIMULATOR  /  NO REAL MONEY',fg=MUTED,bg=BG,font=('Segoe UI',10,'bold')).pack(side='right')
        nav = tk.Frame(root,bg=BG)
        nav.pack(fill='x',padx=24,pady=4)
        self.market_buttons=[]
        for m in self.states:
            b = ttk.Radiobutton(nav,text=m,variable=self.market,value=m,command=self.switch)
            b.pack(side='left',padx=(0,20))
            self.market_buttons.append(b)
        ttk.Button(nav,text='Saved runs',command=self.history).pack(side='right')
        tk.Label(root,textvariable=self.source,bg=BG,fg='#f9bc67',anchor='w',font=('Segoe UI',10)).pack(fill='x',padx=24,pady=7)
        main = tk.Frame(root,bg=BG)
        main.pack(fill='both',expand=True,padx=24)
        left = tk.Frame(main,bg=PANEL,width=235)
        left.pack(side='left',fill='y',padx=(0,16))
        left.pack_propagate(False)
        tk.Label(left,text='EXPERIMENT SETTINGS',bg=PANEL,fg=MUTED,font=('Segoe UI',10,'bold')).pack(anchor='w',padx=14,pady=(14,8))
        ttk.Combobox(left,textvariable=self.strategy,values=['ML classifier','Trend rule'],state='readonly',width=23).pack(padx=14,pady=6)
        self.inputs={}
        for name,label,value in [('capital','Virtual starting balance',10000),('allocation','Position allocation (%)',20),('stop','Stop distance (%)',2),('target','Profit target (%)',4),('max_drawdown','Drawdown halt (%)',10),('fee','Fee each side (%)',.10),('slippage','Slippage each side (%)',.05)]:
            tk.Label(left,text=label,bg=PANEL,fg=MUTED).pack(anchor='w',padx=14,pady=(5,0))
            var=tk.StringVar(value=str(value))
            ttk.Entry(left,textvariable=var,width=23).pack(padx=14,pady=(0,2))
            self.inputs[name]=var
        self.run_button=ttk.Button(left,text='Train & run test',command=self.run)
        self.run_button.pack(fill='x',padx=14,pady=(14,6))
        self.import_button=ttk.Button(left,text='Import market CSV',command=self.load_csv)
        self.import_button.pack(fill='x',padx=14,pady=4)
        ttk.Button(left,text='Restore demo data',command=self.demo).pack(fill='x',padx=14,pady=4)
        ttk.Button(left,text='Export report',command=self.export).pack(fill='x',padx=14,pady=4)
        right=tk.Frame(main,bg=BG)
        right.pack(side='left',fill='both',expand=True)
        self.metrics=tk.StringVar(value='Run an experiment to see results.')
        tk.Label(right,textvariable=self.metrics,justify='left',bg=PANEL,fg=FG,font=('Segoe UI',12),anchor='w',padx=15,pady=15).pack(fill='x')
        self.chart=tk.Canvas(right,bg=PANEL,height=230,highlightthickness=0)
        self.chart.pack(fill='x',pady=10)
        self.chart.bind('<Configure>',lambda e:self.draw())
        bar=tk.Frame(right,bg=BG)
        bar.pack(fill='x')
        ttk.Button(bar,text='Replay test bars',command=self.replay).pack(side='left')
        ttk.Button(bar,text='Pause replay',command=self.pause).pack(side='left',padx=8)
        self.detail=tk.StringVar(value='60% training / 40% unseen test data. Signals execute at the next bar open.')
        tk.Label(right,textvariable=self.detail,bg=BG,fg=MUTED,anchor='w',wraplength=800,justify='left').pack(fill='x',pady=8)
        cols=('date','side','price','quantity','fee','pnl','reason')
        table_frame=tk.Frame(right,bg=BG)
        table_frame.pack(fill='both',expand=True)
        self.table=ttk.Treeview(table_frame,columns=cols,show='headings',height=8)
        widths=(95,50,85,85,65,75,330)
        for col,w in zip(cols,widths):
            self.table.heading(col,text=col.upper())
            self.table.column(col,width=w,minwidth=45,stretch=(col=='reason'))
        ys=ttk.Scrollbar(table_frame,orient='vertical',command=self.table.yview)
        xs=ttk.Scrollbar(table_frame,orient='horizontal',command=self.table.xview)
        self.table.configure(yscrollcommand=ys.set,xscrollcommand=xs.set)
        self.table.grid(row=0,column=0,sticky='nsew')
        ys.grid(row=0,column=1,sticky='ns')
        xs.grid(row=1,column=0,sticky='ew')
        table_frame.columnconfigure(0,weight=1)
        table_frame.rowconfigure(0,weight=1)
        tk.Label(root,textvariable=self.status,bg=BG,fg=MUTED,anchor='w',wraplength=1100,justify='left').pack(fill='x',padx=24,pady=12)
        self.visible=None
        self.switch()
        self.root.after(100,self.poll)

    def state(self):
        return self.states[self.market.get()]

    def switch(self):
        self.pause()
        self.visible=None
        s=self.state()
        self.source.set(f'{self.market.get()}  •  {s["source"]}  •  {len(s["bars"]):,} bars')
        self.render()

    def demo(self):
        if self.busy:return
        self.states[self.market.get()]=dict(bars=sample(self.market.get()),source='SYNTHETIC DEMO — not market data',result=None)
        self.switch()

    def load_csv(self):
        if self.busy:return
        path=filedialog.askopenfilename(filetypes=[('OHLC CSV','*.csv')])
        if not path:return
        try:
            bars=read_csv(path)
            self.states[self.market.get()]=dict(bars=bars,source='USER CSV: '+Path(path).name+' (not independently verified)',result=None)
            self.switch()
        except (ValueError,OSError,csv.Error) as exc:
            messagebox.showerror('Could not import',str(exc))

    def run(self):
        if self.busy:return
        try:
            values={k:float(v.get())/(1 if k=='capital' else 100) for k,v in self.inputs.items()}
            cfg=Config(**values,strategy=self.strategy.get())
            cfg.validate()
        except ValueError as exc:
            messagebox.showerror('Check settings',str(exc));return
        self.pause()
        self.busy=True
        self.run_button.configure(state='disabled')
        market=self.market.get()
        bars=list(self.state()['bars'])
        source=self.state()['source']
        self.status.set('Training on the first 60%, then simulating the final 40%. Please wait…')
        def worker():
            try:
                result=simulate(bars,cfg)
                result.update(market=market,source=source,created_at=datetime.now(timezone.utc).isoformat(),app_version='1.0')
                self.q.put((market,result,None))
            except Exception as exc:
                self.q.put((market,None,str(exc)))
        threading.Thread(target=worker,daemon=True).start()

    def poll(self):
        try:
            market,result,error=self.q.get_nowait()
            self.busy=False
            self.run_button.configure(state='normal')
            if error:
                messagebox.showerror('Experiment failed',error)
                self.status.set('Experiment failed. No orders were sent.')
            else:
                self.states[market]['result']=result
                self.visible=None
                save_error=None
                try:
                    DATA.mkdir(parents=True,exist_ok=True)
                    with sqlite3.connect(DATA/'runs.sqlite3') as db:
                        db.execute('CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY, created TEXT, market TEXT, source TEXT, report TEXT)')
                        db.execute('INSERT INTO runs(created,market,source,report) VALUES(?,?,?,?)',(result['created_at'],market,result['source'],json.dumps(result)))
                except (OSError,sqlite3.Error) as exc:save_error=str(exc)
                self.render()
                self.status.set(('Test complete. Saved on this laptop. ' if not save_error else 'Test complete, but saving failed: '+save_error+'. ')+ 'Results are hypothetical; no live trading or price feed is connected.')
        except queue.Empty:pass
        self.root.after(100,self.poll)

    def render(self):
        r=self.state()['result']
        self.table.delete(*self.table.get_children())
        if not r:
            self.metrics.set('Ready to test\nChoose a strategy or import historical OHLC data.')
            self.detail.set('Demo prices are generated. They cannot establish profitability in a real market.')
        else:
            self.metrics.set(f"Net P/L  {r['net_pnl']:+,.2f}  ({r['return_pct']:+.2f}%)     |     Final balance  {r['final_equity']:,.2f}\nMax drawdown  {r['max_drawdown_pct']:.2f}%     |     Closed trades  {r['closed_trades']}     |     Fees  {r['fees']:.2f}\nBuy & hold reference  {r['benchmark_return_pct']:+.2f}%     |     Risk halt: {'YES' if r['halted'] else 'No'}")
            self.detail.set(f"{r['config']['strategy']} • Train through {r['train_end']} • Test from {r['test_start']} • Results use the settings stored with this run.")
            for t in r['trades'][-3000:]:
                self.table.insert('', 'end',values=(t['date'],t['side'],f"{t['price']:.6g}",f"{t['quantity']:.6g}",f"{t['fee']:.3f}",'—' if t['pnl'] is None else f"{t['pnl']:+.2f}",t['reason']))
        self.draw()

    def draw(self):
        c=self.chart;c.delete('all')
        r=self.state()['result']
        if not r:
            c.create_text(25,35,anchor='w',text='EQUITY CURVE • run a test to begin',fill=MUTED,font=('Segoe UI',11));return
        curve=r['curve'][:self.visible] if self.visible else r['curve']
        vals=[r['config']['capital']]+[x['equity'] for x in curve]
        w,h=max(300,c.winfo_width()),c.winfo_height()
        lo,hi=min(vals),max(vals)
        span=max(hi-lo,1)
        c.create_text(18,18,anchor='w',text='TEST EQUITY • '+r['source'][:70],fill=MUTED)
        for j in range(4):
            y=45+j*(h-70)/3
            c.create_line(75,y,w-18,y,fill='#24344a')
            c.create_text(65,y,anchor='e',text=f'{hi-j*span/3:,.0f}',fill=MUTED)
        # Limit rendering work; full-resolution results remain in reports.
        step=max(1,len(vals)//1200)
        indices=list(range(0,len(vals),step))
        if indices[-1]!=len(vals)-1:indices.append(len(vals)-1)
        coords=[]
        for i in indices:coords.extend((75+i/max(1,len(vals)-1)*(w-95),45+(hi-vals[i])/span*(h-70)))
        if len(coords)>=4:c.create_line(*coords,fill=ACCENT,width=2)

    def pause(self):
        if self.replay_id:
            self.root.after_cancel(self.replay_id)
            self.replay_id=None

    def replay(self):
        if not self.state()['result'] or self.busy:return
        self.pause();self.visible=1;self.tick()

    def tick(self):
        r=self.state()['result']
        if not r:return
        point=r['curve'][self.visible-1]
        self.draw()
        self.detail.set(f"HISTORICAL REPLAY • {point['date']} • equity {point['equity']:,.2f} • previous-bar signal {point['signal']} • risk halted: {point['halted']}\nMetrics and trade table above/below show the completed run; replay is an animation, not live trading.")
        if self.visible<len(r['curve']):
            self.visible+=1
            self.replay_id=self.root.after(70,self.tick)
        else:self.replay_id=None

    def export(self):
        r=self.state()['result']
        if not r:
            messagebox.showinfo('No report','Run a test first.');return
        path=filedialog.asksaveasfilename(defaultextension='.json',initialfile=self.market.get().lower()+'-report.json',filetypes=[('Full report JSON','*.json')])
        if path:
            try:
                Path(path).write_text(json.dumps(r,indent=2),encoding='utf-8')
                messagebox.showinfo('Export complete','Saved full settings, provenance, trades and equity history.')
            except OSError as exc:messagebox.showerror('Export failed',str(exc))

    def history(self):
        try:
            if not (DATA/'runs.sqlite3').exists():
                messagebox.showinfo('Saved runs','No saved runs yet.');return
            with sqlite3.connect(DATA/'runs.sqlite3') as db:
                rows=db.execute('SELECT id,created,market,source,report FROM runs ORDER BY id DESC LIMIT 100').fetchall()
        except sqlite3.Error as exc:
            messagebox.showerror('History unavailable',str(exc));return
        win=tk.Toplevel(self.root);win.title('Saved experiments — last 100');win.geometry('900x450')
        box=tk.Listbox(win,font=('Segoe UI',10),bg=BG,fg=FG)
        box.pack(fill='both',expand=True,padx=10,pady=10)
        for ident,date,market,source,payload in rows:
            r=json.loads(payload)
            box.insert('end',f"#{ident} • {date[:19]} • {market} • {r['config']['strategy']} • {r['return_pct']:+.2f}% • {source}")
        def export_saved():
            selected=box.curselection()
            if not selected:return
            path=filedialog.asksaveasfilename(defaultextension='.json',initialfile=f'run-{rows[selected[0]][0]}.json')
            if path:
                try:Path(path).write_text(rows[selected[0]][4],encoding='utf-8')
                except OSError as exc:messagebox.showerror('Export failed',str(exc))
        ttk.Button(win,text='Export selected report',command=export_saved).pack(pady=8)

if __name__=='__main__':
    root=tk.Tk()
    App(root)
    root.mainloop()
