from flask import Flask, jsonify, render_template_string, request
import json, subprocess
from collections import defaultdict

app = Flask(__name__)

def load_demo():
    try:
        with open("demo_results.json") as f: return json.load(f)
    except: return {"capital":10000,"total_trades":0,"winning_trades":0,"losing_trades":0,"total_pnl":0,"trades":[]}

def load_capital():
    try:
        with open("capital.txt") as f: return json.load(f)
    except: return {"capital":5000,"total_profit":0,"total_trades":0}

def load_live_trades():
    try:
        with open("live_trades.json") as f: return json.load(f)
    except: return {"capital":5000,"total_trades":0,"winning_trades":0,"losing_trades":0,"total_pnl":0,"trades":[]}

def is_running(script):
    try:
        r = subprocess.run(["pgrep","-f",script], capture_output=True, text=True)
        return len(r.stdout.strip()) > 0
    except: return False

@app.route("/api/demo/summary")
def demo_summary():
    d = load_demo()
    total = d["total_trades"]; wins = d["winning_trades"]
    return jsonify({"starting_capital":10000,"current_capital":round(d["capital"],2),
        "total_pnl":round(d["total_pnl"],2),"total_trades":total,
        "winning_trades":wins,"losing_trades":d["losing_trades"],
        "accuracy":round(wins/total*100,1) if total>0 else 0,
        "demo_running":is_running("demo_scalper.py"),
        "bot_running":is_running("scalper_pro.py")})

@app.route("/api/demo/trades")
def demo_trades(): return jsonify(load_demo()["trades"])

@app.route("/api/demo/daily")
def demo_daily():
    d = load_demo()
    days = defaultdict(lambda:{"trades":0,"wins":0,"losses":0,"pnl":0})
    for t in d["trades"]:
        dt=t["date"]; days[dt]["trades"]+=1; days[dt]["pnl"]+=t["pnl"]
        if t["pnl"]>0: days[dt]["wins"]+=1
        else: days[dt]["losses"]+=1
    result=[]
    for date in sorted(days):
        dd=days[date]
        result.append({"date":date,"trades":dd["trades"],"wins":dd["wins"],
            "losses":dd["losses"],"pnl":round(dd["pnl"],2),
            "accuracy":round(dd["wins"]/dd["trades"]*100,1) if dd["trades"]>0 else 0})
    return jsonify(result)

@app.route("/api/demo/capital_growth")
def demo_capital_growth():
    d = load_demo(); h=[{"trade":0,"capital":10000,"date":"Start"}]; cap=10000
    for i,t in enumerate(d["trades"],1):
        cap+=t["pnl"]
        h.append({"trade":i,"capital":round(cap,2),"date":t["date"],"symbol":t["symbol"],"pnl":round(t["pnl"],2)})
    return jsonify(h)

@app.route("/api/live/summary")
def live_summary():
    c = load_capital(); d = load_live_trades()
    total = d["total_trades"]; wins = d["winning_trades"]
    return jsonify({"starting_capital":5000,"current_capital":round(c["capital"],2),
        "total_pnl":round(d["total_pnl"],2),"total_trades":total,
        "winning_trades":wins,"losing_trades":d["losing_trades"],
        "accuracy":round(wins/total*100,1) if total>0 else 0,
        "demo_running":is_running("demo_scalper.py"),
        "bot_running":is_running("scalper_pro.py")})

@app.route("/api/live/trades")
def live_trades_api(): return jsonify(load_live_trades()["trades"])

@app.route("/api/live/daily")
def live_daily():
    d = load_live_trades()
    days = defaultdict(lambda:{"trades":0,"wins":0,"losses":0,"pnl":0})
    for t in d["trades"]:
        dt=t["date"]; days[dt]["trades"]+=1; days[dt]["pnl"]+=t["pnl"]
        if t["pnl"]>0: days[dt]["wins"]+=1
        else: days[dt]["losses"]+=1
    result=[]
    for date in sorted(days):
        dd=days[date]
        result.append({"date":date,"trades":dd["trades"],"wins":dd["wins"],
            "losses":dd["losses"],"pnl":round(dd["pnl"],2),
            "accuracy":round(dd["wins"]/dd["trades"]*100,1) if dd["trades"]>0 else 0})
    return jsonify(result)

@app.route("/api/live/capital_growth")
def live_capital_growth():
    d = load_live_trades(); h=[{"trade":0,"capital":5000,"date":"Start"}]; cap=5000
    for i,t in enumerate(d["trades"],1):
        cap+=t["pnl"]
        h.append({"trade":i,"capital":round(cap,2),"date":t["date"],"symbol":t.get("symbol",""),"pnl":round(t["pnl"],2)})
    return jsonify(h)

@app.route("/api/live_trade")
def live_trade():
    try:
        with open("live_trade.json") as f: return jsonify(json.load(f))
    except: return jsonify({"active":False})

@app.route("/api/square_off", methods=["POST"])
def square_off():
    try:
        with open("live_trade.json") as f: trade=json.load(f)
        if not trade.get("active"): return jsonify({"success":False,"message":"No active trade"})
        trade["square_off"]=True
        with open("live_trade.json","w") as f: json.dump(trade,f,indent=2)
        return jsonify({"success":True,"message":"Square off signal sent!"})
    except Exception as e: return jsonify({"success":False,"message":str(e)})

@app.route("/")
def index(): return render_template_string(HTML)

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Scalper Pro Suite</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#080c14;color:#e2e8f0;min-height:100vh}
.header{background:#0d1421;border-bottom:0.5px solid #1c2a3a;padding:0 20px;height:52px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100}
.logo{display:flex;align-items:center;gap:9px;font-weight:600;font-size:14px}
.logo-icon{width:26px;height:26px;background:#3b82f6;border-radius:7px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:12px}
.hright{display:flex;align-items:center;gap:7px}
.pill{display:inline-flex;align-items:center;gap:5px;padding:4px 10px;border-radius:20px;font-size:11px;font-weight:500;border:0.5px solid}
.pill.demo-r{background:#0c1a2e;color:#60a5fa;border-color:#1e3a5f}
.pill.live-s{background:#1c0a0a;color:#f87171;border-color:#7f1d1d}
.pill.live-r{background:#052e16;color:#4ade80;border-color:#166534}
.dot{width:5px;height:5px;border-radius:50%;background:currentColor}
.rbtn{background:#111827;border:0.5px solid #243447;color:#94a3b8;padding:5px 10px;border-radius:6px;cursor:pointer;font-size:12px;font-family:inherit;display:flex;align-items:center;gap:4px}
.rbtn:hover{border-color:#3b82f6;color:#e2e8f0}
.psw{display:flex;background:#0d1421;border-bottom:0.5px solid #1c2a3a;padding:0 20px;position:sticky;top:52px;z-index:99}
.pbtn{padding:12px 20px;font-size:13px;font-weight:500;color:#64748b;cursor:pointer;border-bottom:2px solid transparent;display:flex;align-items:center;gap:7px;transition:all 0.15s;white-space:nowrap}
.pbtn:hover{color:#e2e8f0}
.pbtn.demo.act{color:#3b82f6;border-bottom-color:#3b82f6}
.pbtn.live.act{color:#22c55e;border-bottom-color:#22c55e}
.pbadge{padding:2px 6px;border-radius:10px;font-size:10px;font-weight:500}
.dbadge{background:rgba(59,130,246,0.15);color:#3b82f6}
.lbadge{background:rgba(34,197,94,0.15);color:#22c55e}
.dash{display:none}
.dash.act{display:block}
.tabs{display:flex;background:#080c14;border-bottom:0.5px solid #1c2a3a;padding:0 20px;gap:2px}
.tab{padding:9px 14px;font-size:12px;font-weight:500;color:#64748b;cursor:pointer;border-bottom:2px solid transparent;display:flex;align-items:center;gap:5px;transition:all 0.15s;white-space:nowrap}
.tab:hover{color:#e2e8f0}
.tab.ademo{color:#3b82f6;border-bottom-color:#3b82f6}
.tab.alive{color:#22c55e;border-bottom-color:#22c55e}
.tp{display:none;padding:16px 20px}
.tp.act{display:block}
.lu{font-size:11px;color:#64748b;margin-bottom:14px}
.kg{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin-bottom:14px}
.kc{background:#111827;border-radius:8px;padding:12px;position:relative;overflow:hidden}
.kc::after{content:"";position:absolute;top:0;left:0;right:0;height:2px;background:var(--kc,#3b82f6);opacity:0.8}
.kl{font-size:10px;font-weight:500;text-transform:uppercase;letter-spacing:0.6px;color:#64748b;margin-bottom:6px}
.kv{font-size:18px;font-weight:500;font-family:monospace;margin-bottom:3px}
.ks{font-size:11px;color:#475569}
.gv{color:#22c55e}.rv{color:#ef4444}.bv{color:#3b82f6}.wv{color:#f59e0b}
.lc{background:#111827;border-radius:12px;border:0.5px solid #1c2a3a;padding:16px 18px;margin-bottom:14px}
.lc.da{border-color:#3b82f6}.lc.la{border-color:#22c55e}
.ch{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
.ct{font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:0.6px;color:#64748b;display:flex;align-items:center;gap:7px}
.ab{padding:2px 7px;border-radius:20px;font-size:10px;font-weight:500}
.ab.d{background:rgba(59,130,246,0.15);color:#3b82f6;border:0.5px solid rgba(59,130,246,0.3)}
.ab.l{background:rgba(34,197,94,0.15);color:#22c55e;border:0.5px solid rgba(34,197,94,0.3)}
.sqb{border:0.5px solid #7f1d1d;background:#1c0a0a;color:#f87171;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px;font-weight:500;font-family:inherit;display:flex;align-items:center;gap:5px;transition:all 0.15s}
.sqb:hover{background:#ef4444;color:#fff;border-color:#ef4444}
.sqb:disabled{opacity:0.4;cursor:not-allowed}
.lg{display:grid;grid-template-columns:2fr 1fr 1fr 1.5fr 1fr 1fr 1fr;gap:14px;margin-bottom:12px}
.lf label{display:block;font-size:10px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;color:#64748b;margin-bottom:4px}
.lv{font-family:monospace;font-size:13px;font-weight:500;color:#e2e8f0}
.lv.sd{color:#3b82f6;font-size:11px}.lv.sl{color:#22c55e;font-size:11px}
.lv.ltp{color:#06b6d4;font-size:17px}.lv.tv{color:#22c55e}.lv.sv{color:#ef4444}
.pbl{display:flex;justify-content:space-between;font-size:10px;color:#64748b;margin-bottom:4px;font-family:monospace}
.pbb{background:#080c14;border-radius:4px;height:5px;overflow:hidden}
.pbfd{height:100%;border-radius:4px;background:linear-gradient(90deg,#3b82f6,#60a5fa)}
.pbfl{height:100%;border-radius:4px;background:linear-gradient(90deg,#22c55e,#4ade80)}
.nt{text-align:center;padding:24px;color:#64748b;font-size:12px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}
.three{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:12px}
.cc{background:#111827;border-radius:12px;border:0.5px solid #1c2a3a;padding:16px 18px}
.tc{background:#111827;border-radius:12px;border:0.5px solid #1c2a3a;padding:16px 18px;margin-bottom:14px}
table{width:100%;border-collapse:collapse;font-size:12px}
th{text-align:left;padding:7px 10px;font-size:10px;font-weight:500;text-transform:uppercase;letter-spacing:0.6px;color:#64748b;border-bottom:0.5px solid #1c2a3a}
td{padding:9px 10px;border-bottom:0.5px solid #1c2a3a;font-family:monospace;font-size:12px;color:#e2e8f0}
tr:last-child td{border-bottom:none}
tr:hover td{background:#0d1421}
.tag{display:inline-flex;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:500}
.tag.ce{background:rgba(34,197,94,0.12);color:#22c55e;border:0.5px solid rgba(34,197,94,0.3)}
.tag.pe{background:rgba(239,68,68,0.12);color:#ef4444;border:0.5px solid rgba(239,68,68,0.3)}
.tag.target{background:rgba(34,197,94,0.12);color:#22c55e;border:0.5px solid rgba(34,197,94,0.3)}
.tag.stoploss{background:rgba(239,68,68,0.12);color:#ef4444;border:0.5px solid rgba(239,68,68,0.3)}
.tag.squareoff{background:rgba(245,158,11,0.12);color:#f59e0b;border:0.5px solid rgba(245,158,11,0.3)}
.pp{color:#22c55e}.pn{color:#ef4444}
.toast{position:fixed;bottom:20px;right:20px;background:#111827;border:0.5px solid #243447;border-radius:8px;padding:12px 18px;font-size:13px;z-index:999;opacity:0;transform:translateY(8px);transition:all 0.3s;max-width:280px}
.toast.show{opacity:1;transform:translateY(0)}
.toast.ok{border-color:#22c55e}.toast.err{border-color:#ef4444}
.bc{display:flex;align-items:flex-end;gap:4px;height:130px;padding:4px 0}
.bar{border-radius:3px 3px 0 0;flex:1;transition:opacity 0.2s;cursor:pointer}
.bar:hover{opacity:0.7}
.xl{display:flex;justify-content:space-between;font-size:9px;color:#64748b;margin-top:4px}
@media(max-width:1100px){.kg{grid-template-columns:repeat(3,1fr)}.two{grid-template-columns:1fr}.lg{grid-template-columns:repeat(4,1fr)}}
@media(max-width:700px){.kg{grid-template-columns:repeat(2,1fr)}.three{grid-template-columns:1fr}.lg{grid-template-columns:repeat(2,1fr)}}
</style>
</head>
<body>
<div class="header">
  <div class="logo"><div class="logo-icon">&#x26A1;</div>Scalper Pro Suite</div>
  <div class="hright">
    <div class="pill demo-r" id="ds"><div class="dot"></div> Demo: Checking...</div>
    <div class="pill live-s" id="bs"><div class="dot"></div> Live: Checking...</div>
    <button class="rbtn" onclick="loadAll()">&#x21BB; Refresh</button>
  </div>
</div>
<div class="psw">
  <div class="pbtn demo act" id="pb-demo" onclick="showPage('demo',this)">&#x1F4CA; Demo Scalper Dashboard <span class="pbadge dbadge">PAPER TRADING</span></div>
  <div class="pbtn live" id="pb-live" onclick="showPage('live',this)">&#x1F680; Scalper Pro Dashboard <span class="pbadge lbadge">LIVE TRADING</span></div>
</div>

<!-- DEMO DASHBOARD -->
<div class="dash act" id="dash-demo">
  <div class="tabs" id="tabs-demo">
    <div class="tab ademo" onclick="showTab('demo','ov',this)">&#x1F3E0; Overview</div>
    <div class="tab" onclick="showTab('demo','an',this)">&#x1F4C8; Analytics</div>
    <div class="tab" onclick="showTab('demo','dp',this)">&#x1F4C5; Daily P&L</div>
    <div class="tab" onclick="showTab('demo','hi',this)">&#x1F4CB; Trade History</div>
  </div>
  <div class="tp act" id="demo-ov">
    <div class="lu" id="d-lu">&#x1F550; Last updated: --</div>
    <div class="kg">
      <div class="kc" style="--kc:#3b82f6"><div class="kl">Starting capital</div><div class="kv bv">Rs.10,000</div><div class="ks">Paper money</div></div>
      <div class="kc" style="--kc:#22c55e"><div class="kl">Current capital</div><div class="kv" id="d-cc">--</div><div class="ks" id="d-ccs">--</div></div>
      <div class="kc" style="--kc:#ef4444"><div class="kl">Total P&L</div><div class="kv" id="d-pnl">--</div><div class="ks" id="d-pnls">--</div></div>
      <div class="kc" style="--kc:#f59e0b"><div class="kl">Total trades</div><div class="kv wv" id="d-tt">--</div><div class="ks" id="d-wl">--</div></div>
      <div class="kc" style="--kc:#ef4444"><div class="kl">Accuracy</div><div class="kv" id="d-ac">--</div><div class="ks">Win rate</div></div>
      <div class="kc" style="--kc:#22c55e"><div class="kl">Today P&L</div><div class="kv" id="d-tp">--</div><div class="ks" id="d-ts">--</div></div>
    </div>
    <div class="lc" id="d-lc">
      <div class="ch">
        <div class="ct">&#x26A1; Live demo trade <span class="ab d" id="d-lb" style="display:none">ACTIVE</span></div>
        <button class="sqb" id="d-sqb" onclick="squareOff()" style="display:none">&#x2715; Square off</button>
      </div>
      <div id="d-lcontent"><div class="nt">&#x1F4CA; No active demo trade</div></div>
    </div>
    <div class="two">
      <div class="cc">
        <div class="ch" style="margin-bottom:10px"><div class="ct">&#x1F4C5; Recent trades</div></div>
        <table><thead><tr><th>Date</th><th>Trades</th><th>P&L</th><th>Acc</th></tr></thead>
        <tbody id="d-rec"><tr><td colspan="4" style="text-align:center;color:#64748b">Loading...</td></tr></tbody></table>
      </div>
      <div class="cc">
        <div class="ch" style="margin-bottom:10px"><div class="ct">&#x2139;&#xFE0F; Status</div></div>
        <div style="display:flex;flex-direction:column;gap:8px">
          <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:0.5px solid #1c2a3a"><span style="font-size:12px;color:#94a3b8">Demo scalper</span><span class="pill demo-r" id="d-st1" style="font-size:10px"><div class="dot"></div> Checking...</span></div>
          <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:0.5px solid #1c2a3a"><span style="font-size:12px;color:#94a3b8">WebSocket</span><span class="pill live-r" style="font-size:10px"><div class="dot"></div> Connected</span></div>
          <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:0.5px solid #1c2a3a"><span style="font-size:12px;color:#94a3b8">Mode</span><span style="font-size:12px;color:#3b82f6;font-weight:500">&#x1F4CA; Paper trading</span></div>
          <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0"><span style="font-size:12px;color:#94a3b8">Dashboard</span><span class="pill live-r" style="font-size:10px"><div class="dot"></div> Running</span></div>
        </div>
      </div>
    </div>
  </div>
  <div class="tp" id="demo-an">
    <div class="lu">&#x1F550; Demo Scalper - Analytics</div>
    <div class="two" style="margin-bottom:12px">
      <div class="cc">
        <div class="ch" style="margin-bottom:10px"><div class="ct">&#x1F4C8; Capital growth</div></div>
        <canvas id="d-cgc" height="160"></canvas>
        <div class="xl" id="d-cgl"></div>
      </div>
      <div class="cc">
        <div class="ch" style="margin-bottom:10px"><div class="ct">&#x1F3AF; Win vs loss</div></div>
        <div style="display:flex;align-items:center;justify-content:center;gap:24px;height:160px">
          <canvas id="d-wlc" width="130" height="130"></canvas>
          <div style="display:flex;flex-direction:column;gap:14px">
            <div><div style="display:flex;align-items:center;gap:6px;margin-bottom:4px"><span style="width:10px;height:10px;border-radius:2px;background:#3b82f6;display:inline-block"></span><span style="color:#94a3b8;font-size:11px">Wins</span></div><div style="font-size:28px;font-weight:500;font-family:monospace;color:#3b82f6" id="d-wc">--</div></div>
            <div><div style="display:flex;align-items:center;gap:6px;margin-bottom:4px"><span style="width:10px;height:10px;border-radius:2px;background:#ef4444;display:inline-block"></span><span style="color:#94a3b8;font-size:11px">Losses</span></div><div style="font-size:28px;font-weight:500;font-family:monospace;color:#ef4444" id="d-lc2">--</div></div>
          </div>
        </div>
      </div>
    </div>
    <div class="three">
      <div class="cc"><div class="kl" style="margin-bottom:6px">Best day</div><div class="kv gv" id="d-bd" style="font-size:18px">--</div><div class="ks" id="d-bds">--</div></div>
      <div class="cc"><div class="kl" style="margin-bottom:6px">Worst day</div><div class="kv rv" id="d-wd" style="font-size:18px">--</div><div class="ks" id="d-wds">--</div></div>
      <div class="cc"><div class="kl" style="margin-bottom:6px">Avg trade P&L</div><div class="kv" id="d-avg" style="font-size:18px">--</div><div class="ks" id="d-avgs">--</div></div>
    </div>
  </div>
  <div class="tp" id="demo-dp">
    <div class="lu">&#x1F550; Demo Scalper - Daily P&L</div>
    <div class="cc" style="margin-bottom:12px">
      <div class="ch" style="margin-bottom:10px"><div class="ct">&#x1F4CA; Daily P&L chart</div></div>
      <div class="bc" id="d-bcc"></div>
      <div class="xl" id="d-bxl"></div>
    </div>
    <div class="tc">
      <div class="ch" style="margin-bottom:10px"><div class="ct">&#x1F4C5; Day-wise breakdown</div></div>
      <table><thead><tr><th>Date</th><th>Trades</th><th>Wins</th><th>Losses</th><th>P&L</th><th>Accuracy</th></tr></thead>
      <tbody id="d-dt"><tr><td colspan="6" style="text-align:center;color:#64748b">Loading...</td></tr></tbody></table>
    </div>
  </div>
  <div class="tp" id="demo-hi">
    <div class="lu">&#x1F550; Demo Scalper - Trade History &nbsp;&#xB7;&nbsp; <span id="d-tc">0 trades</span></div>
    <div class="tc">
      <table><thead><tr><th>#</th><th>Date</th><th>Symbol</th><th>Signal</th><th>Score</th><th>Entry</th><th>Exit</th><th>P&L</th></tr></thead>
      <tbody id="d-tb"><tr><td colspan="8" style="text-align:center;color:#64748b;padding:20px">No trades yet</td></tr></tbody></table>
    </div>
  </div>
</div>

<!-- LIVE DASHBOARD -->
<div class="dash" id="dash-live">
  <div class="tabs" id="tabs-live">
    <div class="tab alive" onclick="showTab('live','ov',this)">&#x1F3E0; Overview</div>
    <div class="tab" onclick="showTab('live','an',this)">&#x1F4C8; Analytics</div>
    <div class="tab" onclick="showTab('live','dp',this)">&#x1F4C5; Daily P&L</div>
    <div class="tab" onclick="showTab('live','hi',this)">&#x1F4CB; Trade History</div>
  </div>
  <div class="tp act" id="live-ov">
    <div class="lu">&#x1F550; Scalper Pro - <span style="color:#22c55e">&#x25CF; Live trading</span></div>
    <div class="kg">
      <div class="kc" style="--kc:#22c55e"><div class="kl">Starting capital</div><div class="kv gv">Rs.5,000</div><div class="ks">Real money</div></div>
      <div class="kc" style="--kc:#22c55e"><div class="kl">Current capital</div><div class="kv" id="l-cc">--</div><div class="ks" id="l-ccs">--</div></div>
      <div class="kc" style="--kc:#f59e0b"><div class="kl">Total P&L</div><div class="kv" id="l-pnl">--</div><div class="ks" id="l-pnls">--</div></div>
      <div class="kc" style="--kc:#f59e0b"><div class="kl">Total trades</div><div class="kv wv" id="l-tt">--</div><div class="ks" id="l-wl">--</div></div>
      <div class="kc" style="--kc:#f59e0b"><div class="kl">Accuracy</div><div class="kv" id="l-ac">--</div><div class="ks">Win rate</div></div>
      <div class="kc" style="--kc:#f59e0b"><div class="kl">Today P&L</div><div class="kv" id="l-tp">--</div><div class="ks" id="l-ts">--</div></div>
    </div>
    <div class="lc" id="l-lc">
      <div class="ch">
        <div class="ct">&#x26A1; Live trade <span class="ab l" id="l-lb" style="display:none">ACTIVE</span></div>
        <button class="sqb" id="l-sqb" onclick="squareOff()" style="display:none">&#x2715; Square off now</button>
      </div>
      <div id="l-lcontent"><div class="nt">&#x1F4CA; No active live trade</div></div>
    </div>
    <div class="two">
      <div class="cc">
        <div class="ch" style="margin-bottom:10px"><div class="ct">&#x2699;&#xFE0F; Bot configuration</div></div>
        <div style="display:flex;flex-direction:column;gap:7px">
          <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:0.5px solid #1c2a3a"><span style="font-size:12px;color:#94a3b8">Max auto trades/day</span><span style="font-size:12px;font-family:monospace">10</span></div>
          <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:0.5px solid #1c2a3a"><span style="font-size:12px;color:#94a3b8">Per trade target</span><span style="font-size:12px;font-family:monospace;color:#22c55e">9%</span></div>
          <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:0.5px solid #1c2a3a"><span style="font-size:12px;color:#94a3b8">Per trade stop loss</span><span style="font-size:12px;font-family:monospace;color:#ef4444">5%</span></div>
          <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:0.5px solid #1c2a3a"><span style="font-size:12px;color:#94a3b8">Daily profit target</span><span style="font-size:12px;font-family:monospace;color:#22c55e">30%</span></div>
          <div style="display:flex;justify-content:space-between;padding:6px 0"><span style="font-size:12px;color:#94a3b8">Max daily loss</span><span style="font-size:12px;font-family:monospace;color:#ef4444">Rs.1,000</span></div>
        </div>
      </div>
      <div class="cc">
        <div class="ch" style="margin-bottom:10px"><div class="ct">&#x2139;&#xFE0F; System status</div></div>
        <div style="display:flex;flex-direction:column;gap:8px">
          <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:0.5px solid #1c2a3a"><span style="font-size:12px;color:#94a3b8">Scalper Pro bot</span><span class="pill live-s" id="l-st1" style="font-size:10px"><div class="dot"></div> Checking...</span></div>
          <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:0.5px solid #1c2a3a"><span style="font-size:12px;color:#94a3b8">Angel One API</span><span class="pill demo-r" style="font-size:10px"><div class="dot"></div> Connected</span></div>
          <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:0.5px solid #1c2a3a"><span style="font-size:12px;color:#94a3b8">Mode</span><span style="font-size:12px;color:#22c55e;font-weight:500">&#x1F680; Live trading</span></div>
          <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0"><span style="font-size:12px;color:#94a3b8">Funds</span><span style="font-size:12px;font-family:monospace;color:#f59e0b">Add funds to trade</span></div>
        </div>
      </div>
    </div>
  </div>
  <div class="tp" id="live-an">
    <div class="lu">&#x1F550; Scalper Pro - Analytics</div>
    <div class="two" style="margin-bottom:12px">
      <div class="cc">
        <div class="ch" style="margin-bottom:10px"><div class="ct">&#x1F4C8; Capital growth (live)</div></div>
        <canvas id="l-cgc" height="160"></canvas>
        <div class="xl" id="l-cgl"></div>
      </div>
      <div class="cc">
        <div class="ch" style="margin-bottom:10px"><div class="ct">&#x1F3AF; Win vs loss (live)</div></div>
        <div style="display:flex;align-items:center;justify-content:center;gap:24px;height:160px">
          <canvas id="l-wlc" width="130" height="130"></canvas>
          <div style="display:flex;flex-direction:column;gap:14px">
            <div><div style="display:flex;align-items:center;gap:6px;margin-bottom:4px"><span style="width:10px;height:10px;border-radius:2px;background:#22c55e;display:inline-block"></span><span style="color:#94a3b8;font-size:11px">Wins</span></div><div style="font-size:28px;font-weight:500;font-family:monospace;color:#22c55e" id="l-wc">--</div></div>
            <div><div style="display:flex;align-items:center;gap:6px;margin-bottom:4px"><span style="width:10px;height:10px;border-radius:2px;background:#ef4444;display:inline-block"></span><span style="color:#94a3b8;font-size:11px">Losses</span></div><div style="font-size:28px;font-weight:500;font-family:monospace;color:#ef4444" id="l-lc2">--</div></div>
          </div>
        </div>
      </div>
    </div>
    <div class="three">
      <div class="cc"><div class="kl" style="margin-bottom:6px">Best day (live)</div><div class="kv gv" id="l-bd" style="font-size:18px">--</div><div class="ks" id="l-bds">No trades yet</div></div>
      <div class="cc"><div class="kl" style="margin-bottom:6px">Worst day (live)</div><div class="kv rv" id="l-wd" style="font-size:18px">--</div><div class="ks" id="l-wds">No trades yet</div></div>
      <div class="cc"><div class="kl" style="margin-bottom:6px">Avg trade P&L</div><div class="kv" id="l-avg" style="font-size:18px">--</div><div class="ks" id="l-avgs">No trades yet</div></div>
    </div>
  </div>
  <div class="tp" id="live-dp">
    <div class="lu">&#x1F550; Scalper Pro - Daily P&L (live)</div>
    <div class="cc" style="margin-bottom:12px">
      <div class="ch" style="margin-bottom:10px"><div class="ct">&#x1F4CA; Daily P&L chart (live)</div></div>
      <div class="bc" id="l-bcc" style="justify-content:center;align-items:center"><span style="color:#64748b;font-size:12px">No live trades yet</span></div>
      <div class="xl" id="l-bxl"></div>
    </div>
    <div class="tc">
      <div class="ch" style="margin-bottom:10px"><div class="ct">&#x1F4C5; Day-wise breakdown (live)</div></div>
      <table><thead><tr><th>Date</th><th>Trades</th><th>Wins</th><th>Losses</th><th>P&L</th><th>Accuracy</th></tr></thead>
      <tbody id="l-dt"><tr><td colspan="6" style="text-align:center;color:#64748b;padding:20px">No live trades yet</td></tr></tbody></table>
    </div>
  </div>
  <div class="tp" id="live-hi">
    <div class="lu">&#x1F550; Scalper Pro - Trade History &nbsp;&#xB7;&nbsp; <span id="l-tc">0 trades</span></div>
    <div class="tc">
      <table><thead><tr><th>#</th><th>Date</th><th>Symbol</th><th>Signal</th><th>Score</th><th>Entry</th><th>Exit</th><th>P&L</th></tr></thead>
      <tbody id="l-tb"><tr><td colspan="8" style="text-align:center;color:#64748b;padding:20px">No live trades yet</td></tr></tbody></table>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>
<script>
var dCgChart,dWlChart,lCgChart,lWlChart;
function showToast(m,t){var el=document.getElementById("toast");el.textContent=m;el.className="toast "+t+" show";setTimeout(function(){el.className="toast";},3000);}
function showPage(n,el){document.querySelectorAll(".pbtn").forEach(function(b){b.classList.remove("act");});document.querySelectorAll(".dash").forEach(function(d){d.classList.remove("act");});el.classList.add("act");document.getElementById("dash-"+n).classList.add("act");}
function showTab(d,n,el){document.querySelectorAll("#tabs-"+d+" .tab").forEach(function(t){t.classList.remove("ademo","alive");});document.querySelectorAll("#dash-"+d+" .tp").forEach(function(p){p.classList.remove("act");});el.classList.add(d==="demo"?"ademo":"alive");document.getElementById(d+"-"+n).classList.add("act");}
function squareOff(){fetch("/api/square_off",{method:"POST"}).then(function(r){return r.json();}).then(function(d){showToast(d.success?"Square off sent!":"Error: "+d.message,d.success?"ok":"err");}).catch(function(){showToast("Failed","err");});}
function updateLiveTrade(){
  return fetch("/api/live_trade").then(function(r){return r.json();}).then(function(d){
    ["d","l"].forEach(function(p){
      var card=document.getElementById(p+"-lc");
      var cnt=document.getElementById(p+"-lcontent");
      var badge=document.getElementById(p+"-lb");
      var btn=document.getElementById(p+"-sqb");
      if(!d.active){
        card.className="lc";
        badge.style.display="none";
        btn.style.display="none";
        cnt.innerHTML="<div style=\'text-align:center;padding:24px;color:#64748b;font-size:12px\'>No active trade</div>";
        return;
      }
      card.className="lc "+(p==="d"?"da":"la");
      badge.style.display="inline-flex";
      btn.style.display="flex";
      var pnl=d.pnl||0;
      var pc=pnl>=0?"gv":"rv";
      var pp=(d.entry&&d.qty)?((pnl/(d.entry*d.qty))*100).toFixed(2):"0.00";
      var prog=(d.target&&d.sl)?Math.min(100,Math.max(0,((d.ltp-d.sl)/(d.target-d.sl))*100)):0;
      var sc=p==="d"?"sd":"sl";
      var pb=p==="d"?"pbfd":"pbfl";
      var rows=[
        ["Symbol","<span style=\'color:"+(p==="d"?"#3b82f6":"#22c55e")+";font-size:11px;font-family:monospace\'>"+d.symbol+"</span>"],
        ["Entry","<span style=\'font-family:monospace\'>Rs."+d.entry+"</span>"],
        ["LTP","<span style=\'font-family:monospace;font-size:17px;color:#06b6d4\'>Rs."+d.ltp+"</span>"],
        ["P&L","<span style=\'font-family:monospace;color:"+(pnl>=0?"#22c55e":"#ef4444")+"\'>"+(pnl>=0?"+":"")+"Rs."+pnl.toFixed(2)+" ("+pp+"%)</span>"],
        ["Target","<span style=\'font-family:monospace;color:#22c55e\'>Rs."+d.target+"</span>"],
        ["Stop loss","<span style=\'font-family:monospace;color:#ef4444\'>Rs."+d.sl+"</span>"],
        ["Qty","<span style=\'font-family:monospace\'>"+d.qty+"</span>"]
      ];
      var gridHTML="<div style=\'display:grid;grid-template-columns:2fr 1fr 1fr 1.5fr 1fr 1fr 1fr;gap:14px;margin-bottom:12px\'>";
      rows.forEach(function(r){
        gridHTML+="<div><div style=\'font-size:10px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;color:#64748b;margin-bottom:4px\'>"+r[0]+"</div>"+r[1]+"</div>";
      });
      gridHTML+="</div>";
      var pbHTML="<div style=\'display:flex;justify-content:space-between;font-size:10px;color:#64748b;margin-bottom:4px;font-family:monospace\'><span>SL Rs."+d.sl+"</span><span>Progress: "+prog.toFixed(0)+"%</span><span>Target Rs."+d.target+"</span></div><div style=\'background:#080c14;border-radius:4px;height:5px;overflow:hidden\'><div class=\'"+pb+"' style=\'width:"+prog+"%\'></div></div>";
      cnt.innerHTML=gridHTML+pbHTML;
    });
  });
}
function loadDemoSummary(){return fetch("/api/demo/summary").then(function(r){return r.json();}).then(function(d){document.getElementById("ds").textContent=(d.demo_running?"● Demo: Running":"● Demo: Stopped");document.getElementById("ds").className="pill "+(d.demo_running?"demo-r":"live-s");document.getElementById("bs").textContent=(d.bot_running?"● Live: Running":"● Live: Stopped");document.getElementById("bs").className="pill "+(d.bot_running?"live-r":"live-s");document.getElementById("d-st1").textContent=(d.demo_running?"● Running":"● Stopped");document.getElementById("d-st1").className="pill "+(d.demo_running?"live-r":"live-s");var ch=d.current_capital-10000,cc=document.getElementById("d-cc");cc.textContent="Rs."+d.current_capital.toLocaleString("en-IN",{minimumFractionDigits:2});cc.className="kv "+(ch>=0?"gv":"rv");document.getElementById("d-ccs").textContent=(ch>=0?"+":"")+"Rs."+ch.toFixed(0)+" from start";var pp=document.getElementById("d-pnl");pp.textContent=(d.total_pnl>=0?"+":"")+"Rs."+Math.abs(d.total_pnl).toFixed(2);pp.className="kv "+(d.total_pnl>=0?"gv":"rv");document.getElementById("d-pnls").textContent=((d.total_pnl/10000)*100).toFixed(1)+"% return";document.getElementById("d-tt").textContent=d.total_trades;document.getElementById("d-wl").textContent="W:"+d.winning_trades+" L:"+d.losing_trades;document.getElementById("d-wc").textContent=d.winning_trades;document.getElementById("d-lc2").textContent=d.losing_trades;var ac=document.getElementById("d-ac");ac.textContent=d.accuracy+"%";ac.className="kv "+(d.accuracy>=60?"gv":d.accuracy>=40?"wv":"rv");document.getElementById("d-lu").textContent="Last updated: "+new Date().toLocaleTimeString();});}
function loadLiveSummary(){return fetch("/api/live/summary").then(function(r){return r.json();}).then(function(d){document.getElementById("l-st1").textContent=(d.bot_running?"● Running":"● Stopped");document.getElementById("l-st1").className="pill "+(d.bot_running?"live-r":"live-s");var ch=d.current_capital-5000,cc=document.getElementById("l-cc");cc.textContent="Rs."+d.current_capital.toLocaleString("en-IN",{minimumFractionDigits:2});cc.className="kv "+(ch>=0?"gv":"rv");document.getElementById("l-ccs").textContent=(ch>=0?"+":"")+"Rs."+ch.toFixed(0)+" from start";var pp=document.getElementById("l-pnl");pp.textContent=(d.total_pnl>=0?"+":"")+"Rs."+Math.abs(d.total_pnl).toFixed(2);pp.className="kv "+(d.total_pnl>=0?"gv":"rv");document.getElementById("l-pnls").textContent=((d.total_pnl/5000)*100).toFixed(1)+"% return";document.getElementById("l-tt").textContent=d.total_trades;document.getElementById("l-wl").textContent="W:"+d.winning_trades+" L:"+d.losing_trades;document.getElementById("l-wc").textContent=d.winning_trades;document.getElementById("l-lc2").textContent=d.losing_trades;var ac=document.getElementById("l-ac");ac.textContent=d.accuracy+"%";ac.className="kv "+(d.accuracy>=60?"gv":d.accuracy>=40?"wv":"rv");});}
function loadDemoAnalytics(){return fetch("/api/demo/capital_growth").then(function(r){return r.json();}).then(function(d){var labels=d.map(function(x){return x.trade===0?"S":"T"+x.trade;}),values=d.map(function(x){return x.capital;});if(dCgChart)dCgChart.destroy();dCgChart=new Chart(document.getElementById("d-cgc"),{type:"line",data:{labels:labels,datasets:[{data:values,borderColor:"#3b82f6",backgroundColor:"rgba(59,130,246,0.08)",borderWidth:2,pointBackgroundColor:values.map(function(v){return v>=10000?"#22c55e":"#ef4444";}),pointRadius:3,fill:true,tension:0.4}]},options:{plugins:{legend:{display:false}},scales:{x:{ticks:{color:"#475569",font:{size:9}},grid:{color:"#0d1421"}},y:{ticks:{color:"#475569",font:{size:9}},grid:{color:"#0d1421"}}}}});document.getElementById("d-cgl").innerHTML="<span>Start</span><span>Mid</span><span>T"+d.length+"</span>";}).then(function(){return fetch("/api/demo/summary").then(function(r){return r.json();}).then(function(s){if(dWlChart)dWlChart.destroy();dWlChart=new Chart(document.getElementById("d-wlc"),{type:"doughnut",data:{labels:["Wins","Losses"],datasets:[{data:[s.winning_trades||0,s.losing_trades||0],backgroundColor:["rgba(59,130,246,0.8)","rgba(239,68,68,0.8)"],borderColor:["#3b82f6","#ef4444"],borderWidth:2,hoverOffset:4}]},options:{cutout:"65%",plugins:{legend:{display:false}}}});});});}
function loadLiveAnalytics(){return fetch("/api/live/capital_growth").then(function(r){return r.json();}).then(function(d){if(lCgChart)lCgChart.destroy();if(d.length>1){var labels=d.map(function(x){return x.trade===0?"S":"T"+x.trade;}),values=d.map(function(x){return x.capital;});lCgChart=new Chart(document.getElementById("l-cgc"),{type:"line",data:{labels:labels,datasets:[{data:values,borderColor:"#22c55e",backgroundColor:"rgba(34,197,94,0.08)",borderWidth:2,pointBackgroundColor:values.map(function(v){return v>=5000?"#22c55e":"#ef4444";}),pointRadius:3,fill:true,tension:0.4}]},options:{plugins:{legend:{display:false}},scales:{x:{ticks:{color:"#475569",font:{size:9}},grid:{color:"#0d1421"}},y:{ticks:{color:"#475569",font:{size:9}},grid:{color:"#0d1421"}}}}});}}).then(function(){return fetch("/api/live/summary").then(function(r){return r.json();}).then(function(s){if(lWlChart)lWlChart.destroy();lWlChart=new Chart(document.getElementById("l-wlc"),{type:"doughnut",data:{labels:["Wins","Losses"],datasets:[{data:[s.winning_trades||0,s.losing_trades||0],backgroundColor:["rgba(34,197,94,0.8)","rgba(239,68,68,0.8)"],borderColor:["#22c55e","#ef4444"],borderWidth:2,hoverOffset:4}]},options:{cutout:"65%",plugins:{legend:{display:false}}}});});});}
function loadDailyCommon(api,bcId,xlId,dtId,tpId,tsId,bdId,bdsId,wdId,wdsId,recId){
  return fetch(api).then(function(r){return r.json();}).then(function(d){
    var bc=document.getElementById(bcId);
    var xl=document.getElementById(xlId);
    if(!d.length){
      bc.innerHTML="<span style='color:#64748b;font-size:12px'>No data yet</span>";
      return;
    }
    var max=Math.max.apply(null,d.map(function(x){return Math.abs(x.pnl);}));
    var bars="";
    d.forEach(function(x){
      var h=Math.max(4,Math.round((Math.abs(x.pnl)/max)*120));
      var col=x.pnl>=0?"#3b82f6":"#ef4444";
      bars+="<div class='bar' style='height:"+h+"px;background:"+col+";opacity:0.85' title='"+x.date+": Rs."+x.pnl+"'></div>";
    });
    bc.innerHTML=bars;
    var xlabels="";
    d.forEach(function(x){xlabels+="<span>"+x.date.slice(5)+"</span>";});
    xl.innerHTML=xlabels;
    if(document.getElementById(dtId)){
      var rows="";
      d.slice().reverse().forEach(function(x){
        rows+="<tr>";
        rows+="<td style='color:#64748b;font-size:11px'>"+x.date+"</td>";
        rows+="<td>"+x.trades+"</td>";
        rows+="<td class='pp'>"+x.wins+"</td>";
        rows+="<td class='pn'>"+x.losses+"</td>";
        rows+="<td class='"+(x.pnl>=0?"pp":"pn")+"'>"+(x.pnl>=0?"+":"")+"Rs."+Math.abs(x.pnl).toFixed(0)+"</td>";
        rows+="<td style='color:"+(x.accuracy>=60?"#22c55e":x.accuracy>=40?"#f59e0b":"#ef4444")+"'>"+x.accuracy+"%</td>";
        rows+="</tr>";
      });
      document.getElementById(dtId).innerHTML=rows;
    }
    var today=d.find(function(x){return x.date===new Date().toISOString().slice(0,10);});
    var tEl=document.getElementById(tpId);
    if(today&&tEl){
      tEl.textContent=(today.pnl>=0?"+":"")+"Rs."+Math.abs(today.pnl).toFixed(0);
      tEl.className="kv "+(today.pnl>=0?"gv":"rv");
      document.getElementById(tsId).textContent=today.trades+" trades today";
    } else if(tEl){
      tEl.textContent="Rs.0";
      document.getElementById(tsId).textContent="No trades today";
    }
    if(d.length&&bdId&&document.getElementById(bdId)){
      var best=d.reduce(function(a,b){return a.pnl>b.pnl?a:b;},d[0]);
      var worst=d.reduce(function(a,b){return a.pnl<b.pnl?a:b;},d[0]);
      document.getElementById(bdId).textContent=(best.pnl>=0?"+":"")+"Rs."+Math.abs(best.pnl).toFixed(0);
      document.getElementById(bdsId).textContent=best.date+" - "+best.accuracy+"%";
      document.getElementById(wdId).textContent=(worst.pnl>=0?"+":"")+"Rs."+Math.abs(worst.pnl).toFixed(0);
      document.getElementById(wdsId).textContent=worst.date+" - "+worst.accuracy+"%";
    }
  });
}
function loadHistoryCommon(api,tbId,tcId,recId,symColor){
  return fetch(api).then(function(r){return r.json();}).then(function(trades){
    document.getElementById(tcId).textContent=trades.length+" trades";
    var tbody=document.getElementById(tbId);
    if(!trades.length){
      tbody.innerHTML="<tr><td colspan='8' style='text-align:center;color:#64748b;padding:20px'>No trades yet</td></tr>";
      return;
    }
    var rows="";
    trades.slice().reverse().forEach(function(t,i){
      var pnlCls=t.pnl>=0?"pp":"pn";
      var pnlStr=(t.pnl>=0?"+":"")+"Rs."+Math.abs(t.pnl||0).toFixed(2);
      rows+="<tr>";
      rows+="<td style='color:#64748b'>"+(trades.length-i)+"</td>";
      rows+="<td style='color:#64748b;font-size:11px'>"+(t.date||"")+"</td>";
      rows+="<td style='color:"+symColor+";font-size:11px'>"+(t.symbol||"")+"</td>";
      rows+="<td><span class='tag "+(t.signal||"").toLowerCase()+"'>"+(t.signal||"")+"</span></td>";
      rows+="<td style='color:#f59e0b'>"+(t.score||"-")+"/10</td>";
      rows+="<td>Rs."+(t.entry||0)+"</td>";
      rows+="<td><span class='tag "+(t.exit||"").toLowerCase()+"'>"+(t.exit||"")+"</span></td>";
      rows+="<td class='"+pnlCls+"'>"+pnlStr+"</td>";
      rows+="</tr>";
    });
    tbody.innerHTML=rows;
    if(recId&&document.getElementById(recId)){
      var recRows="";
      trades.slice(-5).reverse().forEach(function(t){
        recRows+="<tr>";
        recRows+="<td style='color:#64748b;font-size:11px'>"+(t.date||"").slice(5)+"</td>";
        recRows+="<td>1</td>";
        recRows+="<td class='"+(t.pnl>=0?"pp":"pn")+"'>"+(t.pnl>=0?"+":"")+"Rs."+Math.abs(t.pnl||0).toFixed(0)+"</td>";
        recRows+="<td>-</td>";
        recRows+="</tr>";
      });
      document.getElementById(recId).innerHTML=recRows;
    }
    var avg=trades.reduce(function(s,t){return s+(t.pnl||0);},0)/(trades.length||1);
    var avgId=tbId==="d-tb"?"d-avg":"l-avg";
    var avgsId=tbId==="d-tb"?"d-avgs":"l-avgs";
    var avgEl=document.getElementById(avgId);
    if(avgEl){
      avgEl.textContent=(avg>=0?"+":"")+"Rs."+Math.abs(avg).toFixed(2);
      avgEl.className="kv "+(avg>=0?"gv":"rv");
    }
    var avgsEl=document.getElementById(avgsId);
    if(avgsEl)avgsEl.textContent="Across "+trades.length+" trades";
  });
}
function loadAll(){Promise.all([loadDemoSummary(),loadLiveSummary(),loadDemoAnalytics(),loadLiveAnalytics(),loadDailyCommon("/api/demo/daily","d-bcc","d-bxl","d-dt","d-tp","d-ts","d-bd","d-bds","d-wd","d-wds","d-rec"),loadDailyCommon("/api/live/daily","l-bcc","l-bxl","l-dt","l-tp","l-ts","l-bd","l-bds","l-wd","l-wds",null),loadHistoryCommon("/api/demo/trades","d-tb","d-tc","d-rec","#3b82f6"),loadHistoryCommon("/api/live/trades","l-tb","l-tc",null,"#22c55e"),updateLiveTrade()]).catch(function(e){console.error("Error:",e);});}
loadAll();
setInterval(loadAll,30000);
setInterval(updateLiveTrade,5000);
</script>
</body>
</html>"""

if __name__ == "__main__":
    print("Dashboard running at http://127.0.0.1:8080")
    app.run(debug=True, port=8080, host="0.0.0.0")
