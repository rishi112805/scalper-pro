import pyotp
import time
import datetime
import json
import feedparser
import pandas as pd
import ta
from SmartApi import SmartConnect

# ═══════════════════════════════════════════════════
#  SCALPER PRO — REAL TRADING BOT
# ═══════════════════════════════════════════════════

CLIENT_ID   = "G57817669"
API_KEY     = "pkChF10O"
TOTP_SECRET = "GAWUC3JHMVDVI3RSYHH7K53RCQ"
PASSWORD    = "2005"

DAILY_PROFIT_TARGET = 0.30
MAX_AUTO_TRADES     = 10
PER_TRADE_TARGET    = 0.09
PER_TRADE_SL        = 0.05
MAX_DAILY_LOSS      = 1000
SCAN_INTERVAL       = 15
MIN_SIGNAL_SCORE    = 2
HIGH_VIX_THRESHOLD  = 20
CAPITAL_FILE        = "capital.txt"

INDEX_CONFIG = {
    "NIFTY": {
        "exchange": "NSE", "symbol": "Nifty 50",
        "token": "99926000", "step": 50, "lot": 65,
        "nfo": "NFO",
    },
    "BANKNIFTY": {
        "exchange": "NSE", "symbol": "Nifty Bank",
        "token": "99926009", "step": 100, "lot": 30,
        "nfo": "NFO",
    },
    "SENSEX": {
        "exchange": "BSE", "symbol": "SENSEX",
        "token": "99919000", "step": 100, "lot": 20,
        "nfo": "BFO",
    },
}

NEWS_FEEDS = [
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "https://www.moneycontrol.com/rss/marketsnews.xml",
]
BULLISH_KEYWORDS  = ["surge","rally","gain","rise","positive","growth","recovery","bull","high","record"]
BEARISH_KEYWORDS  = ["crash","fall","drop","decline","negative","loss","bear","low","recession","crisis"]
HIGH_IMPACT_WORDS = ["rbi","rate","inflation","gdp","budget","war","election","fed","crisis","emergency"]

# ═══ CAPITAL MANAGEMENT ═══════════════════════════
def load_capital():
    try:
        with open(CAPITAL_FILE, "r") as f:
            data = json.load(f)
            print("💾 Loaded capital: ₹{data['capital']:.2f}")
            return data
    except:
        print("💾 Starting fresh with ₹5,000")
        return {"capital": 5000, "total_profit": 0,
                "total_trades": 0, "start_capital": 5000,
                "last_updated": str(datetime.date.today())}

def save_capital(data):
    data["last_updated"] = str(datetime.date.today())
    with open(CAPITAL_FILE, "w") as f:
        json.dump(data, f, indent=2)

def update_capital(data, pnl):
    data["capital"]      += pnl
    data["total_profit"] += pnl
    data["total_trades"] += 1
    save_capital(data)
    print(f"\n💰 Capital Updated: ₹{data['capital']:.2f} | Total P&L: ₹{data['total_profit']:+.2f}")
    return data

# ═══ LOGIN ════════════════════════════════════════
def login():
    try:
        totp = pyotp.TOTP(TOTP_SECRET).now()
        obj  = SmartConnect(api_key=API_KEY)
        data = obj.generateSession(CLIENT_ID, PASSWORD, totp)
        if data["status"]:
            print("✅ Login Successful!")
            return obj
        print(f"❌ Login Failed: {data}")
        exit()
    except Exception as e:
        print(f"❌ {e}")
        exit()

# ═══ FUNDS ════════════════════════════════════════
def get_real_balance(obj):
    try:
        funds = obj.rmsLimit()
        if funds and funds.get("data"):
            data = funds["data"]
            net   = float(data.get("net", 0))
            used  = float(data.get("utilisedamount", 0))
            avail = float(data.get("availablecash", 0))
            print(f"💳 ANGEL ONE FUNDS:")
            print(f"   Available Cash : ₹{avail:.2f}")
            print(f"   Used Margin    : ₹{used:.2f}")
            print(f"   Net Balance    : ₹{net:.2f}")
            return avail
        return None
    except Exception as e:
        print(f"⚠️ Fund fetch error: {e}")
        return None

# ═══ MARKET HOURS ═════════════════════════════════
def is_market_open():
    now   = datetime.datetime.now()
    start = now.replace(hour=9, minute=15, second=0, microsecond=0)
    end   = now.replace(hour=15, minute=30, second=0, microsecond=0)
    if now.weekday() >= 5:
        return False
    return start <= now <= end

def is_square_off_time():
    now = datetime.datetime.now()
    return now >= now.replace(hour=15, minute=15, second=0, microsecond=0)

# ═══ NEWS ═════════════════════════════════════════
def analyze_news():
    headlines = []
    bullish_count = bearish_count = 0
    high_impact = False
    for feed_url in NEWS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                headlines.append(entry.title.lower())
        except:
            pass
    for headline in headlines:
        for word in BULLISH_KEYWORDS:
            if word in headline: bullish_count += 1
        for word in BEARISH_KEYWORDS:
            if word in headline: bearish_count += 1
        for word in HIGH_IMPACT_WORDS:
            if word in headline: high_impact = True
    if bullish_count > bearish_count:
        return min(2, bullish_count), high_impact, "bullish"
    elif bearish_count > bullish_count:
        return min(2, bearish_count), high_impact, "bearish"
    return 0, high_impact, "neutral"

# ═══ VIX ══════════════════════════════════════════
def get_vix(obj):
    try:
        data = obj.ltpData("NSE", "India VIX", "99926017")
        return data["data"]["ltp"]
    except:
        return 15

# ═══ PRICES ═══════════════════════════════════════
def get_index_price(obj, index):
    cfg = INDEX_CONFIG[index]
    try:
        data = obj.ltpData(cfg["exchange"], cfg["symbol"], cfg["token"])
        return data["data"]["ltp"]
    except:
        return None

def get_option_ltp(obj, symbol, token, nfo="NFO"):
    try:
        data = obj.ltpData(nfo, symbol, token)
        return data["data"]["ltp"]
    except:
        return None

# ═══ CANDLE DATA ══════════════════════════════════
def get_candle_data(obj, index):
    cfg = INDEX_CONFIG[index]
    try:
        now = datetime.datetime.now()
        from_time = (now - datetime.timedelta(days=5)).strftime("%Y-%m-%d %H:%M")
        to_time   = now.strftime("%Y-%m-%d %H:%M")
        params = {
            "exchange": cfg["exchange"], "symboltoken": cfg["token"],
            "interval": "FIVE_MINUTE", "fromdate": from_time, "todate": to_time,
        }
        data = obj.getCandleData(params)
        if data and data.get("status") and data.get("data"):
            df = pd.DataFrame(data["data"],
                columns=["timestamp","open","high","low","close","volume"])
            df["close"]  = pd.to_numeric(df["close"])
            df["volume"] = pd.to_numeric(df["volume"])
            if len(df) < 5:
                print(f"⚠️ Not enough candle data for {index}")
                return None
            return df
        else:
            print(f"⚠️ No candle data for {index}: {data.get('message', 'unknown') if data else 'no response'}")
            return None
    except Exception as e:
        print(f"⚠️ Candle error {index}: {e}")
        return None

# ═══ SIGNAL SCORING ═══════════════════════════════
def calculate_signal_score(obj, index, news_score, news_sentiment, vix):
    score = 0; signal = None; reasons = []
    ltp = get_index_price(obj, index)
    if not ltp: return 0, None, None
    df = get_candle_data(obj, index)
    if df is None or len(df) < 20: return 0, None, None

    df["rsi"]   = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    df["ema20"] = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
    df["ema9"]  = ta.trend.EMAIndicator(df["close"], window=9).ema_indicator()
    rsi   = df["rsi"].iloc[-1]
    ema20 = df["ema20"].iloc[-1]
    ema9  = df["ema9"].iloc[-1]
    price = df["close"].iloc[-1]
    avg_vol   = df["volume"].rolling(10).mean().iloc[-1]
    cur_vol   = df["volume"].iloc[-1]
    vol_spike = cur_vol > avg_vol * 1.5

    if rsi < 35:
        score += 2; signal = "CE"
        reasons.append(f"RSI={rsi:.1f} oversold (+2)")
    elif rsi > 65:
        score += 2; signal = "PE"
        reasons.append(f"RSI={rsi:.1f} overbought (+2)")
    else:
        reasons.append(f"RSI={rsi:.1f} neutral (0)")

    if ema9 > ema20 and price > ema20:
        score += 2
        if not signal: signal = "CE"
        reasons.append("EMA bullish (+2)")
    elif ema9 < ema20 and price < ema20:
        score += 2
        if not signal: signal = "PE"
        reasons.append("EMA bearish (+2)")
    else:
        reasons.append("EMA neutral (0)")

    if vol_spike:
        score += 2; reasons.append("Volume spike (+2)")

    if news_score > 0:
        if (news_sentiment == "bullish" and signal == "CE") or \
           (news_sentiment == "bearish" and signal == "PE"):
            score += news_score
            reasons.append(f"News confirms (+{news_score})")
        else:
            score -= news_score
            reasons.append(f"News contradicts (-{news_score})")

    if vix > HIGH_VIX_THRESHOLD:
        score -= 2; reasons.append(f"VIX={vix:.1f} high (-2)")

    print(f"\n📊 {index} | Score:{score}/10 | Signal:{signal} | Price:₹{ltp}")
    for r in reasons:
        print(f"   → {r}")
    return score, signal, ltp

# ═══ OPTION HELPERS ═══════════════════════════════
def get_nearest_expiry(obj, index):
    try:
        nfo = INDEX_CONFIG[index]["nfo"]
        result = obj.searchScrip(nfo, index)
        if not result or not result.get("data"):
            return None
        expiries = set()
        for item in result["data"]:
            sym = item["tradingsymbol"]
            # Must start with index name exactly
            if not sym.startswith(index): continue
            rest = sym[len(index):]
            # Must be an option (ends with CE or PE)
            if not (rest.endswith("CE") or rest.endswith("PE")): continue
            # Expiry is first 7 chars: DDMMMYY
            if len(rest) < 9: continue
            expiry_str = rest[:7]
            # Validate it looks like a date
            if not expiry_str[0].isdigit(): continue
            try:
                exp_date = datetime.datetime.strptime(expiry_str, "%d%b%y").date()
                expiries.add((exp_date, expiry_str.upper()))
            except ValueError:
                continue
        if not expiries: return None
        today = datetime.date.today()
        future = sorted([e for e in expiries if e[0] >= today])
        if not future: return None
        # Return nearest expiry within 14 days (weekly), else nearest anyway
        weekly = [e for e in future if (e[0] - today).days <= 14]
        return weekly[0][1] if weekly else future[0][1]
    except Exception as e:
        print(f"⚠️ Expiry lookup error: {e}")
        return None

def get_strike(ltp, index):
    step = INDEX_CONFIG[index]["step"]
    return round(ltp / step) * step

def lookup_token(obj, symbol, nfo="NFO"):
    try:
        result = obj.searchScrip(nfo, symbol)
        if result and result.get("data"):
            for item in result["data"]:
                if item["tradingsymbol"] == symbol:
                    return item["symboltoken"]
        return None
    except:
        return None

def get_quantity(index, premium, capital):
    lot = INDEX_CONFIG[index]["lot"]
    if premium and premium > 0:
        if premium * lot > capital:
            return 0
        lots = max(1, int(capital / (premium * lot)))
    else:
        lots = 1
    return lots * lot

# ═══ POSITION CHECK ═══════════════════════════════
def is_position_open(obj, symbol):
    try:
        positions = obj.position()
        if positions and positions.get("data"):
            for pos in positions["data"]:
                if pos["tradingsymbol"] == symbol:
                    return int(pos.get("netqty", 0)) != 0
        return False
    except:
        return True

# ═══ PLACE ORDER ══════════════════════════════════
def place_order(obj, symbol, token, qty, txn_type="BUY", nfo="NFO"):
    print(f"\n🚀 {txn_type}: {symbol} | Qty:{qty} | Exchange:{nfo}")
    try:
        order = {
            "variety": "NORMAL", "tradingsymbol": symbol,
            "symboltoken": token, "transactiontype": txn_type,
            "exchange": nfo, "ordertype": "MARKET",
            "producttype": "INTRADAY", "duration": "DAY",
            "quantity": qty,
        }
        res = obj.placeOrder(order)
        if res and res.get("data"):
            print(f"✅ Order ID: {res['data']['orderid']}")
            return res["data"]["orderid"]
        print(f"⚠️ Order failed: {res}")
        return None
    except Exception as e:
        print(f"❌ Order error: {e}")
        return None

# ═══ MONITOR POSITION ═════════════════════════════
def monitor_position(obj, entry, symbol, token, qty, nfo="NFO"):
    target = entry * (1 + PER_TRADE_TARGET)
    sl     = entry * (1 - PER_TRADE_SL)
    print(f"\n👁️  Monitoring: {symbol}")
    print(f"   Entry  : ₹{entry:.2f}")
    print(f"   Target : ₹{target:.2f} (+{PER_TRADE_TARGET*100:.0f}%)")
    print(f"   SL     : ₹{sl:.2f}  (-{PER_TRADE_SL*100:.0f}%)")
    print(f"   Qty    : {qty}")

    while True:
        try:
            if is_square_off_time():
                ltp = get_option_ltp(obj, symbol, token, nfo) or entry
                pnl = (ltp - entry) * qty
                print(f"\n⏰ Square off! P&L:₹{pnl:+.2f}")
                if is_position_open(obj, symbol):
                    place_order(obj, symbol, token, qty, "SELL", nfo)
                return "SQUAREOFF", pnl

            if not is_position_open(obj, symbol):
                ltp = get_option_ltp(obj, symbol, token, nfo) or entry
                pnl = (ltp - entry) * qty
                print(f"\n📱 Position closed from app! P&L:₹{pnl:+.2f}")
                return "MANUAL_EXIT", pnl

            ltp = get_option_ltp(obj, symbol, token, nfo)
            if ltp is None:
                time.sleep(3); continue

            pnl = (ltp - entry) * qty
            print(f"   LTP:₹{ltp:.2f} | P&L:₹{pnl:+.2f}   ", end="\r")

            if ltp >= target:
                print(f"\n🎯 TARGET! ₹{ltp:.2f} | Profit:₹{pnl:+.2f}")
                if is_position_open(obj, symbol):
                    place_order(obj, symbol, token, qty, "SELL", nfo)
                return "TARGET", pnl

            if ltp <= sl:
                print(f"\n🛑 STOP LOSS! ₹{ltp:.2f} | Loss:₹{pnl:+.2f}")
                if is_position_open(obj, symbol):
                    place_order(obj, symbol, token, qty, "SELL", nfo)
                return "STOPLOSS", pnl

            time.sleep(3)
        except Exception as e:
            print(f"\n⚠️ Monitor error: {e}")
            time.sleep(3)

# ═══ MAIN BOT ═════════════════════════════════════
def run_bot():
    cap_data     = load_capital()
    trades_today = daily_pnl = daily_loss = 0

    print("=" * 55)
    print("🤖  SCALPER PRO — ANGEL ONE LIVE TRADING")
    print("=" * 55)
    obj = login()
    indices = list(INDEX_CONFIG.keys())

    # Fetch real balance from Angel One
    real_balance = get_real_balance(obj)
    
    if real_balance is not None and real_balance > 0:
        print(f"✅ Using REAL Angel One balance: ₹{real_balance:.2f}")
        cap_data["capital"] = real_balance
        save_capital(cap_data)
    else:
        print(f"⚠️ Could not fetch real balance. Using saved: ₹{cap_data['capital']:.2f}")
        print(f" Capital: ₹{cap_data['capital']:.2f}")
        obj = login()
        indices = list(INDEX_CONFIG.keys())
    # Fetch real balance from Angel One
    real_balance = get_real_balance(obj)
    if real_balance is not None and real_balance > 0:
        print(f"✅ Using REAL Angel One balance: ₹{real_balance:.2f}")
        cap_data["capital"] = real_balance
        save_capital(cap_data)
    else:
        print(f"⚠️ Could not fetch real balance. Using saved: ₹{cap_data['capital']:.2f}")
    print(f" Capital      : ₹{cap_data['capital']:.2f}")
    print(f"   Daily Target : 30% = ₹{cap_data['capital']*DAILY_PROFIT_TARGET:.2f}")
    print(f"   Per Trade    : Target {PER_TRADE_TARGET*100:.0f}% | SL {PER_TRADE_SL*100:.0f}%")
    print(f"   Max Trades   : {MAX_AUTO_TRADES} auto + manual")
    print(f"   Max Loss     : ₹{MAX_DAILY_LOSS}")
    print("=" * 55)

    while True:
        if not is_market_open():
            now = datetime.datetime.now()
            if now.hour < 9 or (now.hour == 9 and now.minute < 15):
                print(f"\n⏰ Market opens at 9:15 AM. Waiting...")
            else:
                print(f"\n⏰ Market closed.")
                print(f"   Final P&L : ₹{daily_pnl:+.2f}")
                print(f"   Capital   : ₹{cap_data['capital']:.2f}")
                while not is_market_open():
                    time.sleep(60)
                trades_today = daily_pnl = daily_loss = 0
                cap_data = load_capital()
                print(f"\n🌅 New day! Capital: ₹{cap_data['capital']:.2f}")
            time.sleep(60)
            continue

        if cap_data["capital"] < 2000:
            print(f"\n🛑 Capital ₹{cap_data['capital']:.2f} too low. Bot stopped.")
            break

        if daily_loss >= MAX_DAILY_LOSS:
            print(f"\n🛑 Max daily loss hit (₹{daily_loss:.2f}). Stopped for today.")
            while not is_market_open():
                time.sleep(60)
            trades_today = daily_pnl = daily_loss = 0
            continue

        daily_target = cap_data["capital"] * DAILY_PROFIT_TARGET
        if daily_pnl >= daily_target:
            print(f"\n🎯 DAILY TARGET HIT! Profit: ₹{daily_pnl:.2f}")
            print(f"   Capital: ₹{cap_data['capital']:.2f}")
            try:
                cmd = input("   Type 'trade' for 1 more or 'stop' to exit: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break
            if cmd == "stop":
                print("👋 Great trading day!")
                break
            elif cmd == "trade":
                print("✅ Taking 1 more trade...")
            else:
                time.sleep(30); continue

        elif trades_today >= MAX_AUTO_TRADES:
            try:
                cmd = input(f"\n⏸️  {MAX_AUTO_TRADES} auto trades done. 'trade' or 'stop': ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break
            if cmd == "stop":
                print("👋 Bot stopped.")
                break
            elif cmd == "trade":
                trades_today = MAX_AUTO_TRADES - 1
            else:
                print("❓ Type 'trade' or 'stop'.")
                continue

        # Dashboard
        print(f"\n{'='*50}")
        print(f"💰 Capital: ₹{cap_data['capital']:.2f} | Daily P&L: ₹{daily_pnl:+.2f} | Trades: {trades_today}/{MAX_AUTO_TRADES}")
        print(f"{'='*50}")

        print("\n📰 Checking news...")
        news_score, high_impact, news_sentiment = analyze_news()
        vix = get_vix(obj)

        best_score = 0
        best_signal = best_index = best_ltp = None

        for index in indices:
            score, signal, ltp = calculate_signal_score(
                obj, index, news_score, news_sentiment, vix)
            if signal and score > best_score:
                best_score = score; best_signal = signal
                best_index = index; best_ltp = ltp

        if not best_signal or best_score < MIN_SIGNAL_SCORE:
            print(f"\n⏳ Score {best_score}/10 — below min {MIN_SIGNAL_SCORE}. Waiting {SCAN_INTERVAL}s...")
            time.sleep(SCAN_INTERVAL)
            continue

        nfo    = INDEX_CONFIG[best_index]["nfo"]
        expiry = get_nearest_expiry(obj, best_index)
        if not expiry:
            print("⚠️ Could not determine expiry. Skipping.")
            time.sleep(30); continue

        strike = get_strike(best_ltp, best_index)
        symbol = f"{best_index}{expiry}{int(strike)}{best_signal}"
        token  = lookup_token(obj, symbol, nfo)

        print(f"\n{'='*55}")
        print(f"🎯 LIVE TRADE SIGNAL!")
        print(f"   Index    : {best_index}")
        print(f"   Signal   : {best_signal}")
        print(f"   Symbol   : {symbol}")
        print(f"   Score    : {best_score}/10")
        print(f"   Exchange : {nfo}")
        print(f"   Trade #  : {trades_today + 1}")
        print(f"{'='*55}")

        if not token:
            print("⚠️ Token not found. Skipping.")
            time.sleep(30); continue

        entry = get_option_ltp(obj, symbol, token, nfo)
        if not entry:
            print("⚠️ Could not get premium. Skipping.")
            time.sleep(30); continue

        min_cost = entry * INDEX_CONFIG[best_index]["lot"]
        if min_cost > cap_data["capital"]:
            print(f"⚠️ Too expensive! 1 lot=₹{min_cost:.0f}, capital=₹{cap_data['capital']:.0f}. Skipping.")
            time.sleep(30); continue

        qty = get_quantity(best_index, entry, cap_data["capital"])
        if qty == 0:
            print("⚠️ Cannot afford. Skipping.")
            time.sleep(30); continue

        print(f"   Premium  : ₹{entry:.2f}")
        print(f"   Quantity : {qty}")
        print(f"   Capital  : ₹{entry * qty:.2f}")

        order_id = place_order(obj, symbol, token, qty, "BUY", nfo)
        if not order_id:
            print("⚠️ Order failed. Skipping.")
            time.sleep(30); continue

        trades_today += 1
        reason, pnl = monitor_position(obj, entry, symbol, token, qty, nfo)

        cap_data  = update_capital(cap_data, pnl)
        daily_pnl += pnl
        if pnl < 0:
            daily_loss += abs(pnl)

        print(f"\n📋 Trade #{trades_today} Summary")
        print(f"   Exit   : {reason}")
        print(f"   P&L    : ₹{pnl:+.2f}")
        print(f"   Daily  : ₹{daily_pnl:+.2f}")
        print(f"   Capital: ₹{cap_data['capital']:.2f}")
        print("-" * 40)
        time.sleep(10)

    print(f"\n{'='*55}")
    print(f"✅ SESSION ENDED")
    print(f"   Trades   : {trades_today}")
    print(f"   Daily P&L: ₹{daily_pnl:+.2f}")
    print(f"   Capital  : ₹{cap_data['capital']:.2f}")
    print(f"{'='*55}")

if __name__ == "__main__":
    run_bot()
