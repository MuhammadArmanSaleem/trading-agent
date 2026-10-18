"""Beginner-first practice desk. Python + Tk; virtual money only."""
import copy
import json
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from practice import Account, Store, transact
from market_data import demo_snapshot, kraken_snapshot

BG='#0b1220'; PANEL='#152238'; FG='#edf3fa'; MUTED='#a7b6cb'; GREEN='#63e0b8'; AMBER='#ffc77a'
DATA=Path.home()/'TradingLabData'

class App:
    def __init__(self,root,store=None,fetcher=None):
        self.root=root
        self.store=store or Store(DATA/'practice.sqlite3')
        self.fetcher=fetcher or self.fetch
        self.accounts={m:self.store.latest(m) for m in ('Crypto','Forex','Stocks')}
        self.market='Crypto';self.connected=False;self.busy=False;self.epoch=0
        self.next_fetch=0;self.q=queue.Queue();self.closed=False
        root.title('Trading Lab | Practice first')
        root.geometry('1120x780');root.minsize(860,620);root.configure(bg=BG)
        root.protocol('WM_DELETE_WINDOW',self.close_app)
        style=ttk.Style(root);style.theme_use('clam')
        style.configure('.',background=PANEL,foreground=FG,font=('Segoe UI',10),fieldbackground=BG)
        style.configure('TButton',padding=(12,9))
        style.map('TButton',background=[('active','#294260'),('disabled','#1a2638')],foreground=[('disabled','#6e7f97')])
        style.configure('Treeview',background=BG,fieldbackground=BG,foreground=FG,rowheight=28)
        style.configure('Treeview.Heading',background=PANEL,foreground=MUTED)
        self.header=tk.Frame(root,bg=BG);self.header.pack(fill='x',padx=24,pady=(20,8))
        tk.Label(self.header,text='Trading Lab',bg=BG,fg=FG,font=('Segoe UI',25,'bold')).pack(side='left')
        tk.Label(self.header,text='PRACTICE ONLY  |  NO REAL MONEY',bg=BG,fg=GREEN,font=('Segoe UI',11,'bold')).pack(side='right')
        self.nav=tk.Frame(root,bg=BG);self.nav.pack(fill='x',padx=24,pady=8)
        for m in self.accounts:
            ttk.Button(self.nav,text=m,command=lambda market=m:self.switch(market)).pack(side='left',padx=(0,8))
        ttk.Button(self.nav,text='Help',command=self.help).pack(side='right',padx=4)
        ttk.Button(self.nav,text='Advanced research',command=self.research).pack(side='right',padx=4)
        ttk.Button(self.nav,text='Saved accounts',command=self.history).pack(side='right',padx=4)
        viewport=tk.Frame(root,bg=BG);viewport.pack(fill='both',expand=True,padx=24,pady=10)
        self.scroll=tk.Canvas(viewport,bg=BG,highlightthickness=0)
        scrollbar=ttk.Scrollbar(viewport,orient='vertical',command=self.scroll.yview)
        self.scroll.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right',fill='y');self.scroll.pack(side='left',fill='both',expand=True)
        self.body=tk.Frame(self.scroll,bg=BG)
        self.body_window=self.scroll.create_window((0,0),window=self.body,anchor='nw')
        self.body.bind('<Configure>',lambda e:self.scroll.configure(scrollregion=self.scroll.bbox('all')))
        self.scroll.bind('<Configure>',lambda e:self.scroll.itemconfigure(self.body_window,width=e.width))
        root.bind('<MouseWheel>',lambda e:self.scroll.yview_scroll(int(-e.delta/120),'units'))
        root.bind('<Button-4>',lambda e:self.scroll.yview_scroll(-1,'units'))
        root.bind('<Button-5>',lambda e:self.scroll.yview_scroll(1,'units'))
        self.footer=tk.StringVar(value='Virtual practice account. There is no deposit, broker connection or real-money switch.')
        tk.Label(root,textvariable=self.footer,bg=BG,fg=MUTED,wraplength=1100,anchor='w',justify='left').pack(fill='x',padx=24,pady=(4,14))
        self.build()
        self.poll_id=root.after(100,self.poll)

    @property
    def account(self):return self.accounts[self.market]

    def label(self,parent,text,size=11,color=FG,**kwargs):
        label=tk.Label(parent,text=text,font=('Segoe UI',size),bg=parent['bg'],fg=color,justify='left',anchor='w',**kwargs)
        if 'wraplength' in kwargs:
            label.bind('<Configure>',lambda e:label.configure(wraplength=max(180,e.width-6)))
        return label

    def switch(self,market):
        if market==self.market:return
        if self.account and self.account.quantity:
            messagebox.showinfo('One practice account at a time','Close the current practice position before switching markets. This prevents leaving it unmonitored.')
            return
        if self.account and self.account.status=='running' and not self.change(lambda a:a.pause()):return
        self.epoch+=1;self.connected=False;self.market=market;self.build()

    def build(self):
        for child in self.body.winfo_children():child.destroy()
        self.scroll.yview_moveto(0)
        if self.account:self.dashboard()
        else:self.onboarding()

    def onboarding(self):
        panel=tk.Frame(self.body,bg=PANEL,padx=30,pady=22)
        panel.pack(fill='both',expand=True)
        self.label(panel,f'Your {self.market.lower()} practice account',23).pack(fill='x',pady=(0,8))
        self.label(panel,'Learn what the bot does, using money you cannot lose in real life.',12,MUTED).pack(fill='x',pady=(0,20))
        self.label(panel,'1   Choose the price source',14).pack(fill='x',pady=(0,8))
        self.mode=tk.StringVar(value='demo')
        ttk.Radiobutton(panel,text='Offline demo - generated prices, no internet needed',variable=self.mode,value='demo').pack(anchor='w',pady=5)
        real=ttk.Radiobutton(panel,text='Real Bitcoin prices - virtual trades, internet required',variable=self.mode,value='prices')
        real.pack(anchor='w',pady=5)
        if self.market!='Crypto':
            real.configure(state='disabled')
            self.label(panel,'Real-price '+self.market.lower()+' practice is not connected yet. This section uses a labeled demo.',11,AMBER,wraplength=850).pack(fill='x',pady=8)
        else:
            self.label(panel,'Bitcoin is the first supported price feed, not an investment recommendation. No exchange account needed.',11,MUTED,wraplength=850).pack(fill='x',pady=8)
        self.label(panel,'2   Set your virtual limits',14).pack(fill='x',pady=(14,6))
        grid=tk.Frame(panel,bg=PANEL);grid.pack(fill='x')
        self.settings={}
        for row,(key,title,default,explain) in enumerate([
            ('capital','Starting practice money ($)','10000','Virtual US dollars, not a deposit.'),
            ('allocation','Use at most this % per trade','10','Limits spending on one position; the rest stays as virtual cash.'),
            ('loss_limit','Stop after account drops this %','5','Measured from its highest observed value. A price gap can exceed it.')]):
            self.label(grid,title,11).grid(row=row,column=0,sticky='w',pady=8,padx=(0,16))
            v=tk.StringVar(value=default);self.settings[key]=v
            ttk.Entry(grid,textvariable=v,width=12).grid(row=row,column=1,sticky='w',padx=(0,16))
            self.label(grid,explain,10,MUTED,wraplength=340).grid(row=row,column=2,sticky='w')
        self.label(panel,'3   Review before starting',14).pack(fill='x',pady=(18,6))
        self.label(panel,'The bot may wait without trading. Its small local AI model has no proven trading edge.\nPractice exits use a 2% price-drop stop and 4% rise target, plus 0.1% estimated fee and 0.05% slippage each side.\nWhen this app is closed or disconnected, it cannot monitor positions or apply exits.',11,MUTED,wraplength=950).pack(fill='x',pady=6)
        ttk.Button(panel,text='Create practice account ->',command=self.create).pack(anchor='w',pady=(18,6))

    def create(self):
        try:
            values={k:float(v.get())/(1 if k=='capital' else 100) for k,v in self.settings.items()}
            a=Account.create(self.market,self.mode.get(),**values)
            self.store.save(a)
        except Exception as exc:
            messagebox.showerror('Check practice settings',str(exc));return
        self.accounts[self.market]=a
        self.epoch+=1;self.connected=False;self.build()

    def dashboard(self):
        a=self.account
        strip=tk.Frame(self.body,bg=PANEL,padx=16,pady=12);strip.pack(fill='x')
        self.source_label=self.label(strip,'',11,AMBER);self.source_label.pack(fill='x')
        self.status_label=self.label(strip,'',20);self.status_label.pack(fill='x',pady=(6,2))
        self.reason_label=self.label(strip,'',11,MUTED,wraplength=1050);self.reason_label.pack(fill='x')
        cards=tk.Frame(self.body,bg=BG);cards.pack(fill='x',pady=12)
        self.cards={}
        for i,(key,title) in enumerate([('value','PRACTICE VALUE'),('change','TOTAL GAIN / LOSS'),('cash','AVAILABLE CASH'),('position','OPEN POSITION')]):
            frame=tk.Frame(cards,bg=PANEL,padx=14,pady=14);frame.grid(row=0,column=i,sticky='nsew',padx=(0,8 if i<3 else 0))
            cards.columnconfigure(i,weight=1,uniform='card')
            self.label(frame,title,9,MUTED).pack(fill='x')
            self.cards[key]=self.label(frame,'',20);self.cards[key].pack(fill='x',pady=(6,0))
        buttons=tk.Frame(self.body,bg=BG);buttons.pack(fill='x')
        self.start_button=ttk.Button(buttons,text='Start practice',command=self.start);self.start_button.pack(side='left',padx=(0,8))
        self.pause_button=ttk.Button(buttons,text='Pause new trades',command=self.pause);self.pause_button.pack(side='left',padx=(0,8))
        self.sell_button=ttk.Button(buttons,text='Close practice position',command=self.sell);self.sell_button.pack(side='left',padx=(0,8))
        ttk.Button(buttons,text='Export',command=self.export).pack(side='right')
        ttk.Button(buttons,text='New account',command=self.new_account).pack(side='right',padx=8)
        self.info_label=self.label(self.body,'',10,MUTED,wraplength=1080);self.info_label.pack(fill='x',pady=10)
        self.chart=tk.Canvas(self.body,bg=PANEL,height=155,highlightthickness=0);self.chart.pack(fill='x')
        self.chart.bind('<Configure>',lambda e:self.draw())
        self.label(self.body,'What the bot did',13).pack(fill='x',pady=(12,6))
        holder=tk.Frame(self.body,bg=BG);holder.pack(fill='both',expand=True)
        self.table=ttk.Treeview(holder,columns=('time','action','reason'),show='headings',height=5)
        for col,title,width in [('time','TIME (UTC)',155),('action','ACTION',85),('reason','PLAIN-LANGUAGE EXPLANATION',700)]:
            self.table.heading(col,text=title);self.table.column(col,width=width,minwidth=60,stretch=col=='reason')
        scroll=ttk.Scrollbar(holder,orient='vertical',command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)
        self.table.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y')
        self.table.bind('<Double-1>',self.event_detail)
        self.refresh()

    def refresh(self):
        if not self.account or not hasattr(self,'cards') or not self.body.winfo_children():return
        a=self.account
        if not hasattr(self,'status_label') or not self.status_label.winfo_exists():return
        label={'running':'Watching the market','paused':'New trades are paused','attention':'Your attention is needed','halted':'Stopped by your loss control'}[a.status]
        if self.busy:label='Loading prices...' if not a.model else 'Checking prices...'
        self.status_label.configure(text=label)
        self.reason_label.configure(text=a.explanation)
        self.source_label.configure(text=f"{a.market}  |  "+('SYNTHETIC DEMO - accelerated generated prices' if a.mode=='demo' else 'BTC/USD | Kraken public prices | LOCAL PAPER TRADES'))
        equity=a.equity();pnl=equity-a.initial
        self.cards['value'].configure(text=f'${equity:,.2f}')
        self.cards['change'].configure(text=f'${pnl:+,.2f}',fg=GREEN if pnl>=0 else AMBER)
        self.cards['cash'].configure(text=f'${a.cash:,.2f}')
        self.cards['position'].configure(text='Holding' if a.quantity else 'None')
        age='Not connected' if not a.last_quote_at else time.strftime('%H:%M:%S UTC',time.gmtime(a.last_quote_at))
        self.info_label.configure(text=f"{a.allocation:.0%} maximum spend per trade | {a.loss_limit:.0%} account-drop halt | Estimated fees paid ${a.fees:.2f}\nLast received: {age}. Value includes estimated exit costs; it may be stale while disconnected. Double-click an activity for details.")
        self.start_button.configure(text='Reconnect / resume' if a.model else 'Start practice',state='disabled' if a.halted or self.busy or a.status=='running' else 'normal')
        self.pause_button.configure(state='normal' if a.status=='running' else 'disabled')
        self.sell_button.configure(state='normal' if a.quantity and not self.busy else 'disabled')
        self.table.delete(*self.table.get_children())
        for i,event in enumerate(a.events[-150:]):
            self.table.insert('', 'end',iid=str(i),values=(event['time'][11:19],event['kind'],event['reason']))
        self.draw()

    def draw(self):
        if not self.account or not hasattr(self,'chart') or not self.chart.winfo_exists():return
        c=self.chart;c.delete('all');a=self.account
        vals=[a.initial]+[h['equity'] for h in a.history]
        w=max(c.winfo_width(),300);h=c.winfo_height();lo=min(vals);hi=max(vals);span=max(hi-lo,1)
        c.create_text(16,17,anchor='w',text='YOUR VIRTUAL ACCOUNT VALUE | sampled while the app is connected',fill=MUTED)
        for j in range(3):
            y=40+j*(h-60)/2
            c.create_line(78,y,w-18,y,fill='#293a52')
            c.create_text(67,y,anchor='e',text=f'{hi-j*span/2:,.0f}',fill=MUTED)
        if len(vals)<2:
            c.create_text(w/2,90,text='Start practice to begin. Waiting in cash is a valid action.',fill=FG);return
        ids=list(range(0,len(vals),max(1,len(vals)//600)))
        if ids[-1]!=len(vals)-1:ids.append(len(vals)-1)
        points=[]
        for i in ids:points.extend((78+i/(len(vals)-1)*(w-98),40+(hi-vals[i])/span*(h-60)))
        c.create_line(*points,fill=GREEN,width=2)

    def change(self,fn):
        try:self.accounts[self.market]=transact(self.store,self.account,fn)
        except Exception as exc:
            self.connected=False
            messagebox.showerror('Could not save safely',str(exc)+'\nNo new practice update was applied.');return False
        return True

    def start(self):
        if self.busy or not self.account:return
        if self.change(lambda a:a.start()):
            self.connected=True;self.next_fetch=0;self.epoch+=1;self.refresh()

    def pause(self):
        if self.change(lambda a:a.pause()):
            self.epoch+=1;self.refresh()

    def sell(self):
        if self.busy or not self.account.quantity:return
        if not messagebox.askyesno('Close virtual holdings?','Sell the full practice position using a fresh price and pause new trades?\n\nThis uses virtual money only.'):return
        self.epoch+=1;self.connected=False
        self.launch('close')

    @staticmethod
    def fetch(account):
        if account.mode=='prices':return kraken_snapshot()
        return demo_snapshot(account.market,account.demo_step)

    def launch(self,action='tick'):
        if self.busy:return
        self.busy=True
        a=copy.deepcopy(self.account);epoch=self.epoch;market=self.market
        self.refresh()
        def worker():
            try:
                snapshot=self.fetcher(a)
                if action=='close':a.close_position(snapshot)
                else:a.process(snapshot)
                if a.mode=='demo':a.demo_step+=1
                self.q.put((epoch,market,a,None,action))
            except Exception as exc:self.q.put((epoch,market,None,str(exc),action))
        threading.Thread(target=worker,daemon=True).start()

    def poll(self):
        if self.closed:return
        try:
            epoch,market,candidate,error,action=self.q.get_nowait()
            self.busy=False
            if epoch==self.epoch and market==self.market:
                if error:
                    self.connected=False
                    self.change(lambda a:a.fail(error))
                else:
                    try:
                        self.store.save(candidate)
                        self.accounts[market]=candidate
                        if candidate.halted or action=='close':self.connected=False
                    except Exception as exc:
                        self.connected=False
                        messagebox.showerror('Practice paused',str(exc)+'\nThe incoming update was not applied. Reopen the app before continuing.')
                        self.account.status='attention'
                        self.account.explanation='Saving failed. Reopen the app to reload the last saved account.'
                self.next_fetch=time.monotonic()+(3 if self.account.mode=='demo' else 20)
                self.refresh()
        except queue.Empty:pass
        if self.connected and self.account and not self.busy and time.monotonic()>=self.next_fetch:
            self.launch()
        self.poll_id=self.root.after(100,self.poll)

    def new_account(self):
        if self.busy:return
        if self.account.quantity:
            messagebox.showinfo('Close the position first','Close your virtual position before creating another account. Existing results will stay in Saved accounts.');return
        if not messagebox.askyesno('Create another practice account?','Keep this account in Saved accounts and return to setup?'):return
        if self.account.status=='running' and not self.change(lambda a:a.pause()):return
        self.epoch+=1;self.connected=False;self.accounts[self.market]=None;self.build()

    def event_detail(self,event=None):
        selected=self.table.selection()
        if not selected:return
        item=self.account.events[-150:][int(selected[0])]
        text=item['reason']
        for k in ('price','quantity','fee','pnl'):
            if item.get(k) is not None:text+=f'\n{k.title()}: {item[k]:,.6f}'
        messagebox.showinfo('Practice activity',text)

    def export(self):
        if not self.account:return
        self.write_report(self.account.report(),self.account.market.lower()+'-practice.json')

    def write_report(self,report,name):
        path=filedialog.asksaveasfilename(initialfile=name,defaultextension='.json',filetypes=[('Practice report','*.json')])
        if not path:return
        try:Path(path).write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
        except Exception as exc:messagebox.showerror('Could not export',str(exc))

    def history(self):
        try:rows=self.store.reports()
        except Exception as exc:messagebox.showerror('Could not read accounts',str(exc));return
        win=tk.Toplevel(self.root);win.title('Saved practice accounts');win.geometry('850x400')
        box=tk.Listbox(win,bg=BG,fg=FG,font=('Segoe UI',11));box.pack(fill='both',expand=True,padx=12,pady=12)
        for updated,d in rows:
            a=Account(**d)
            box.insert('end',f"{updated[:19]} | {a.market} | {'DEMO' if a.mode=='demo' else 'REAL PRICES / VIRTUAL MONEY'} | ${a.equity():,.2f}")
        def export_selected():
            if box.curselection():
                a=Account(**rows[box.curselection()[0]][1]);self.write_report(a.report(),'practice-'+a.id[:8]+'.json')
        ttk.Button(win,text='Export selected account',command=export_selected).pack(pady=8)

    def research(self):
        subprocess.Popen([sys.executable,str(Path(__file__).with_name('research_app.py'))])

    def help(self):
        messagebox.showinfo('How practice works',
            'Everything here uses virtual money. There is no deposit or connected trading account.\n\n'
            'Demo: generated prices move faster so you can learn the controls. They do not predict real results.\n\n'
            'Real prices: Bitcoin data is read from Kraken. Trades are simulated locally, not sent to Kraken. Availability can vary by network.\n\n'
            'Start: allow the model to open a practice trade when its signal appears. It may wait.\n\n'
            'Pause new trades: stop new entries. Existing positions still update; exit rules run while connected.\n\n'
            'Close practice position: sell all virtual holdings at a fresh simulated fill and pause entries.\n\n'
            'Closing the app or losing internet stops monitoring. Reopening keeps holdings and starts paused. A later price can jump past your limit.\n\n'
            'The AI is a small local model, not a proven profitable strategy. Default costs are estimates, not a broker fee quote.')

    def close_app(self):
        if self.account and self.account.quantity:
            if not messagebox.askyesno('Leave virtual holdings open?', 'Closing the app stops all monitoring. Your practice holdings will be saved but no exits run while closed.\n\nClose the app anyway?'):return
        self.epoch+=1;self.connected=False
        if self.account and self.account.status=='running':
            if not self.change(lambda a:a.pause()):return
        self.closed=True
        self.root.after_cancel(self.poll_id)
        self.root.destroy()

if __name__=='__main__':
    root=tk.Tk()
    try:App(root)
    except Exception as exc:
        messagebox.showerror('Could not open Trading Lab',str(exc)+'\nYour saved accounts were not reset.')
        root.destroy()
    else:root.mainloop()
