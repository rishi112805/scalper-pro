import pyotp
import time
import datetime
import json
import feedparser
import pandas as pd
import ta
import threading
from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2

# ─── LIVE PRICE STORE (WebSocket) ───────────────────
live_prices = {
    "NIFTY":     None,
    "BANKNIFTY": None,
    "SENSEX":    None,
}
WS_TOKEN_MAP = {
    "99926000": "NIFTY",
    "99926009": "BANKNIFTY",
    "99919000": "SENSEX",
}
sws_instance = None

# ═══════════════════════════════════════════════════
#  DEMO SCALPER PRO — REAL SIGNALS, FAKE MONEY
# ═══════════════════════════════════════════════════

CLIENT_ID   = "G57817669"
API_KEY     = "pkChF10O"
TOTP_SECRET = "GAWUC3JHMVDVI3RSYHH7K53RCQ"
PASSWORD    = "2005"

# ─── CONFIG ─────────────────────────────────────────
DEMO_CAPITAL        = 10000.0
DAILY_PROFIT_TARGET = 0.30
MAX_AUTO_TRADES     = 10
PER_TRADE_TARGET    = 0.09
PER_TRADE_SL        = 0.05
MAX_DAILY_LOSS      = 1000
SCAN_INTERVAL       = 15
MIN_SIGNAL_SCORE    = 2
HIGH_VIX_THRESHOLD  = 20
DEMO_FILE           = "demo_results.json"

# ─── INDEX CONFIG ───────────────────────────────────
INDEX_CONFIG = {
    "NIFTY": {
        "exchange":   "NSE",
        "symbol":     "Nifty 50",
        "token":      "99926000",
        "step":       50,
        "lot":        65,
        "expiry_day": 3,
        "nfo":        "NFO",
    },
    "BANKNIFTY": {
        "exchange":   "NSE",
        "symbol":     "Nifty Bank",
        "token":      "99926009",
        "step":       100,
        "lot":        30,
        "expiry_day": 2,
        "nfo":        "NFO",
    },
    "SENSEX": {
        "exchange":   "BSE",
        "symbol":     "SENSEX",
        "token":      "99919000",
        "step":       100,
        "lot":        20,
        "expiry_day": 4,
        "nfo":        "BFO",
    },
}

# ─── NEWS ───────────────────────────────────────────
NEWS_FEEDS = [
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "https://www.moneycontrol.com/rss/marketsnews.xml",
]
BULLISH_KEYWORDS  = ["surge","rally","gain","rise","positive","growth","recovery","bull","high","record"]
BEARISH_KEYWORDS  = ["crash","fall","drop","decline","negative","loss","bear","low","recession","crisis"]
HIGH_IMPACT_WORDS = ["rbi","rate","inflation","gdp","budget","war","election","fed","crisis","emergency"]

# ═══════════════════════════════════════════════════
#  DEMO RESULTS TRACKING
# ═══════════════════════════════════════════════════
def load_demo_results():
    try:
        with open(DEMO_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "capital":        DEMO_CAPITAL,
            "total_trades":   0,
            "winning_trades": 0,
            "losing_trades":  0,
            "total_pnl":      0,
            "trades":         []
        }

def save_demo_results(data):
    with open(DEMO_FILE, "w") as f:
        json.dump(data, f, indent=2)

def save_live_trade(trade=None):
    try:
        with open('live_trade.json', 'w') as f:
            if trade:
                json.dump(trade, f, indent=2)
            else:
                json.dump({'active': False}, f, indent=2)
    except:
        pass

def print_accuracy(results):
    total   = results['total_trades']
    wins    = results['winning_trades']
    losses  = results['losing_trades']
    accuracy = (wins / total * 100) if total > 0 else 0

    print(f"\n{'═'*50}")
    print(f"📊 DEMO ACCURACY REPORT")
    print(f"{'═'*50}")
    print(f"   Total Trades  : {total}")
    print(f"   ✅ Wins       : {wins}")
    print(f"   ❌ Losses     : {losses}")
    print(f"   🎯 Accuracy   : {accuracy:.1f}%")
    print(f"   💰 Total P&L  : ₹{results['total_pnl']:+.2f} (FAKE)")
    print(f"   💼 Capital    : ₹{results['capital']:.2f} (FAKE)")
    print(f"{'═'*50}")

# ═══════════════════════════════════════════════════
#  LOGIN
# ═══════════════════════════════════════════════════
def login():
    try:
        totp = pyotp.TOTP(TOTP_SECRET).now()
        obj  = SmartConnect(api_key=API_KEY)
        data = obj.generateSession(CLIENT_ID, PASSWORD, totp)
        if data["status"]:
            print("✅ Login Successful!")
            jwt_token  = data["data"]["jwtToken"]
            feed_token = data["data"]["feedToken"]
            ws_thread  = threading.Thread(
                target=start_websocket,
                args=(jwt_token, feed_token),
                daemon=True
            )
            ws_thread.start()
            print("⚡ WebSocket price feed starting...")
            time.sleep(3)
            return obj
        exit()
    except Exception as e:
        print(f"❌ {e}")
        exit()

# ═══════════════════════════════════════════════════

# ─── WEBSOCKET SETUP ──────────────────────────────────
def ws_on_open(wsapp):
    global sws_instance
    print("🔌 WebSocket Connected! Subscribing...")
    token_list = [
        {"exchangeType": 1, "tokens": ["99926000", "99926009"]},
        {"exchangeType": 3, "tokens": ["99919000"]},
    ]
    sws_instance.subscribe("feed_1", 3, token_list)

def ws_on_data(wsapp, message):
    try:
        data  = json.loads(message)
        token = str(data.get("tk", ""))
        ltp   = data.get("ltp")
        if token in WS_TOKEN_MAP and ltp:
            live_prices[WS_TOKEN_MAP[token]] = float(ltp)
    except:
        pass

def ws_on_error(wsapp, error):
    print(f"\n⚠️ WebSocket Error: {error}")

def ws_on_close(wsapp):
    print("\n🔌 WebSocket Closed")

def start_websocket(jwt_token, feed_token):
    global sws_instance
    sws_instance = SmartWebSocketV2(
        auth_token=jwt_token,
        api_key=API_KEY,
        client_code=CLIENT_ID,
        feed_token=feed_token
    )
    sws_instance.on_open  = ws_on_open
    sws_instance.on_data  = ws_on_data
    sws_instance.on_error = ws_on_error
    sws_instance.on_close = ws_on_close
    sws_instance.connect()

def get_ws_price(index):
    price = live_prices.get(index)
    return price

#  MARKET HOURS
# ═══════════════════════════════════════════════════
def is_market_open():
    now   = datetime.datetime.now()
    start = now.replace(hour=9,  minute=15, second=0, microsecond=0)
    end   = now.replace(hour=15, minute=30, second=0, microsecond=0)
    if now.weekday() >= 5:
        return False
    return start <= now <= end

def is_square_off_time():
    now = datetime.datetime.now()
    return now >= now.replace(hour=15, minute=15, second=0, microsecond=0)

# ═══════════════════════════════════════════════════
#  NEWS
# ═══════════════════════════════════════════════════
def analyze_news():
    headlines     = []
    bullish_count = 0
    bearish_count = 0
    high_impact   = False

    for feed_url in NEWS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                headlines.append(entry.title.lower())
        except:
            pass

    for headline in headlines:
        for word in BULLISH_KEYWORDS:
            if word in headline:
                bullish_count += 1
        for word in BEARISH_KEYWORDS:
            if word in headline:
                bearish_count += 1
        for word in HIGH_IMPACT_WORDS:
            if word in headline:
                high_impact = True

    if bullish_count > bearish_count:
        return min(2, bullish_count), high_impact, "bullish"
    elif bearish_count > bullish_count:
        return min(2, bearish_count), high_impact, "bearish"
    return 0, high_impact, "neutral"

# ═══════════════════════════════════════════════════
#  VIX
# ═══════════════════════════════════════════════════
def get_vix(obj):
    try:
        data = obj.ltpData("NSE", "India VIX", "99926017")
        return data['data']['ltp']
    except:
        return 15

# ═══════════════════════════════════════════════════
#  PRICES
# ═══════════════════════════════════════════════════
def get_index_price(obj, index):
    # Try WebSocket first (real-time)
    ws_price = get_ws_price(index)
    if ws_price:
        return ws_price
    # Fallback to REST API
    cfg = INDEX_CONFIG[index]
    try:
        data = obj.ltpData(cfg["exchange"], cfg["symbol"], cfg["token"])
        return data["data"]["ltp"]
    except:
        return None

def get_option_ltp(obj, symbol, token):
    try:
        data = obj.ltpData("NFO", symbol, token)
        return data['data']['ltp']
    except:
        return None

# ═══════════════════════════════════════════════════
#  CANDLE DATA
# ═══════════════════════════════════════════════════
def get_candle_data(obj, index):
    cfg = INDEX_CONFIG[index]
    try:
        now       = datetime.datetime.now()
        from_time = (now - datetime.timedelta(days=5)).strftime("%Y-%m-%d %H:%M")
        to_time   = now.strftime("%Y-%m-%d %H:%M")
        params    = {
            "exchange":    cfg["exchange"],
            "symboltoken": cfg["token"],
            "interval":    "FIVE_MINUTE",
            "fromdate":    from_time,
            "todate":      to_time,
        }
        data = obj.getCandleData(params)
        if data['status'] and data['data']:
            df = pd.DataFrame(data['data'],
                columns=['timestamp','open','high','low','close','volume'])
            df['close']  = pd.to_numeric(df['close'])
            df['volume'] = pd.to_numeric(df['volume'])
            return df
        return None
    except:
        return None

# ═══════════════════════════════════════════════════
#  SIGNAL SCORING
# ═══════════════════════════════════════════════════
def calculate_signal_score(obj, index, news_score, news_sentiment, vix):
    score   = 0
    signal  = None
    reasons = []

    ltp = get_index_price(obj, index)
    if not ltp:
        return 0, None, None

    df = get_candle_data(obj, index)
    if df is None or len(df) < 20:
        return 0, None, None

    df['rsi']   = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    df['ema20'] = ta.trend.EMAIndicator(df['close'], window=20).ema_indicator()
    df['ema9']  = ta.trend.EMAIndicator(df['close'], window=9).ema_indicator()

    rsi   = df['rsi'].iloc[-1]
    ema20 = df['ema20'].iloc[-1]
    ema9  = df['ema9'].iloc[-1]
    price = df['close'].iloc[-1]

    avg_vol   = df['volume'].rolling(10).mean().iloc[-1]
    cur_vol   = df['volume'].iloc[-1]
    vol_spike = cur_vol > avg_vol * 1.5

    # RSI
    if rsi < 35:
        score += 2; signal = "CE"
        reasons.append(f"RSI={rsi:.1f} oversold (+2)")
    elif rsi > 65:
        score += 2; signal = "PE"
        reasons.append(f"RSI={rsi:.1f} overbought (+2)")
    else:
        reasons.append(f"RSI={rsi:.1f} neutral (0)")

    # EMA
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

    # Volume
    if vol_spike:
        score += 2
        reasons.append(f"Volume spike (+2)")

    # News
    if news_score > 0:
        if (news_sentiment == "bullish" and signal == "CE") or \
           (news_sentiment == "bearish" and signal == "PE"):
            score += news_score
            reasons.append(f"News confirms (+{news_score})")
        else:
            score -= news_score
            reasons.append(f"News contradicts (-{news_score})")

    # VIX
    if vix > HIGH_VIX_THRESHOLD:
        score -= 2
        reasons.append(f"VIX={vix:.1f} high (-2)")

    print(f"\n📊 {index} | Score:{score}/10 | Signal:{signal} | Price:₹{ltp}")
    for r in reasons:
        print(f"   → {r}")

    return score, signal, ltp

# ═══════════════════════════════════════════════════
#  OPTION HELPERS
# ═══════════════════════════════════════════════════
def get_nearest_expiry(obj, index):
    """
    Fetches the real nearest expiry by searching the scrip master
    instead of guessing a weekday.
    """
    try:
        result = obj.searchScrip("NFO", index)
        if not result or not result.get('data'):
            return None

        expiries = set()
        for item in result['data']:
            sym = item['tradingsymbol']
            # Only pure option symbols like NIFTY30JUN2623900CE
            if not sym.startswith(index):
                continue
            rest = sym[len(index):]
            # Expiry is always 7 chars: DDMMMYY e.g. 30JUN26
            if len(rest) < 7:
                continue
            expiry_str = rest[:7]
            try:
                exp_date = datetime.datetime.strptime(expiry_str, "%d%b%y").date()
                expiries.add((exp_date, expiry_str.upper()))
            except ValueError:
                continue
        if not expiries:
            return None

        today = datetime.date.today()
        future_expiries = sorted([e for e in expiries if e[0] >= today])
        if not future_expiries:
            return None

        return future_expiries[0][1]  # nearest expiry string e.g. '30JUN26'
    except Exception as e:
        print(f"⚠️ Expiry lookup error: {e}")
        return None

def get_strike(ltp, index):
    step = INDEX_CONFIG[index]["step"]
    return round(ltp / step) * step

def lookup_token(obj, symbol):
    try:
        result = obj.searchScrip("NFO", symbol)
        if result and result.get('data'):
            for item in result['data']:
                if item['tradingsymbol'] == symbol:
                    return item['symboltoken']
        return None
    except:
        return None

def get_quantity(index, premium, capital):
    lot = INDEX_CONFIG[index]["lot"]
    if premium and premium > 0:
        # Check if even 1 lot is affordable
        min_cost = premium * lot
        if min_cost > capital:
            return 0  # Cannot afford even 1 lot
        lots = max(1, int(capital / (premium * lot)))
    else:
        lots = 1
    return lots * lot

# ═══════════════════════════════════════════════════
#  DEMO MONITOR — REAL PRICES, NO ORDERS
# ═══════════════════════════════════════════════════
def demo_monitor(obj, entry, symbol, token, qty, nfo="NFO"):
    target = entry * (1 + PER_TRADE_TARGET)
    sl     = entry * (1 - PER_TRADE_SL)

    print(f"\n👁️  [DEMO] Monitoring: {symbol}")
    print(f"   Entry  : ₹{entry:.2f}")
    print(f"   Target : ₹{target:.2f} (+{PER_TRADE_TARGET*100:.0f}%)")
    print(f"   SL     : ₹{sl:.2f}  (-{PER_TRADE_SL*100:.0f}%)")
    print(f"   Qty    : {qty}")
    print(f"   ⚠️  NO REAL ORDER PLACED — DEMO ONLY\n")

    save_live_trade({
        'active':     True,
        'symbol':     symbol,
        'entry':      entry,
        'target':     round(target, 2),
        'sl':         round(sl, 2),
        'qty':        qty,
        'ltp':        entry,
        'pnl':        0,
        'start_time': datetime.datetime.now().strftime('%H:%M:%S'),
        'nfo':        nfo
    })

    while True:
        try:
            # Square off time
            if is_square_off_time():
                ltp = get_option_ltp(obj, symbol, token) or entry
                pnl = (ltp - entry) * qty
                print(f"\n⏰ Square off! P&L:₹{pnl:+.2f} (FAKE)")
                return "SQUAREOFF", pnl

            ltp = get_option_ltp(obj, symbol, token)
            if ltp is None:
                time.sleep(3)
                continue

            pnl = (ltp - entry) * qty
            print(f"   LTP:₹{ltp:.2f} | P&L:₹{pnl:+.2f} (FAKE)   ", end='\r')

            save_live_trade({
                'active':     True,
                'symbol':     symbol,
                'entry':      entry,
                'target':     round(target, 2),
                'sl':         round(sl, 2),
                'qty':        qty,
                'ltp':        ltp,
                'pnl':        round(pnl, 2),
                'start_time': datetime.datetime.now().strftime('%H:%M:%S'),
                'nfo':        nfo
            })

            if ltp >= target:
                print(f"\n🎯 TARGET HIT! ₹{ltp:.2f} | Profit:₹{pnl:+.2f} (FAKE)")
                save_live_trade(None)
                return "TARGET", pnl

            if ltp <= sl:
                print(f"\n🛑 STOP LOSS! ₹{ltp:.2f} | Loss:₹{pnl:+.2f} (FAKE)")
                return "STOPLOSS", pnl
                save_live_trade(None)

            time.sleep(3)

        except Exception as e:
            print(f"\n⚠️ Monitor error: {e}")
            time.sleep(3)

# ═══════════════════════════════════════════════════
#  MAIN DEMO LOOP
# ═══════════════════════════════════════════════════
def run_demo():
    results      = load_demo_results()
    trades_today = 0
    daily_pnl    = 0
    daily_loss   = 0

    print("═" * 50)
    print("🎮  DEMO SCALPER PRO")
    print("    REAL SIGNALS — FAKE MONEY")
    print("═" * 50)
    print(f"   Demo Capital : ₹{results['capital']:.2f} (FAKE)")
    print(f"   Daily Target : 30% = ₹{results['capital']*DAILY_PROFIT_TARGET:.2f}")
    print(f"   Past Trades  : {results['total_trades']}")
    if results['total_trades'] > 0:
        acc = results['winning_trades'] / results['total_trades'] * 100
        print(f"   Accuracy     : {acc:.1f}%")
    print("═" * 50)

    obj     = login()
    indices = list(INDEX_CONFIG.keys())

    while True:

        # Market hours
        if not is_market_open():
            print("\n⏰ Market closed. Waiting...")
            time.sleep(60)
            continue

        # Daily loss check
        if daily_loss >= MAX_DAILY_LOSS:
            print(f"\n🛑 [DEMO] Max loss hit. Stopped.")
            break

        # Daily target check
        daily_target = results['capital'] * DAILY_PROFIT_TARGET
        if daily_pnl >= daily_target:
            print(f"\n🎯 [DEMO] Daily target ₹{daily_target:.2f} hit!")
            print_accuracy(results)
            try:
                cmd = input("Type 'trade' for 1 more or 'stop': ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break
            if cmd == 'stop':
                break
            elif cmd != 'trade':
                continue

        # Max trades check
        elif trades_today >= MAX_AUTO_TRADES:
            print_accuracy(results)
            try:
                cmd = input(f"\n⏸️  {MAX_AUTO_TRADES} trades done. 'trade' or 'stop': ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break
            if cmd == 'stop':
                break
            elif cmd == 'trade':
                trades_today = MAX_AUTO_TRADES - 1
            else:
                continue

        # News
        print("\n📰 Checking news...")
        news_score, high_impact, news_sentiment = analyze_news()

        # VIX
        vix = get_vix(obj)

        # Scan signals
        best_score  = 0
        best_signal = None
        best_index  = None
        best_ltp    = None

        for index in indices:
            score, signal, ltp = calculate_signal_score(
                obj, index, news_score, news_sentiment, vix
            )
            if signal and score > best_score:
                best_score  = score
                best_signal = signal
                best_index  = index
                best_ltp    = ltp

        if not best_signal or best_score < MIN_SIGNAL_SCORE:
            print(f"\n⏳ Score {best_score}/10 — below min {MIN_SIGNAL_SCORE}. Waiting {SCAN_INTERVAL}s...")
            time.sleep(SCAN_INTERVAL)
            continue

        # Build option
        expiry = get_nearest_expiry(obj, best_index)
        if not expiry:
            print("⚠️ Could not determine expiry. Skipping.")
            time.sleep(30)
            continue
        strike = get_strike(best_ltp, best_index)
        symbol = f"{best_index}{expiry}{int(strike)}{best_signal}"
        token  = lookup_token(obj, symbol)

        print(f"\n{'═'*50}")
        print(f"🎮 [DEMO] TRADE #{trades_today + 1}")
        print(f"   Index   : {best_index}")
        print(f"   Signal  : {best_signal}")
        print(f"   Symbol  : {symbol}")
        print(f"   Score   : {best_score}/10")
        print(f"{'═'*50}")

        if not token:
            print("⚠️ Token not found. Skipping.")
            time.sleep(30)
            continue

        nfo = INDEX_CONFIG[best_index]["nfo"]
        entry = get_option_ltp(obj, symbol, token)
        if not entry:
            print("⚠️ No premium. Skipping.")
            time.sleep(30)
            continue

        # Check affordability
        min_cost = entry * INDEX_CONFIG[best_index]["lot"]
        if min_cost > results["capital"]:
            print(f"⚠️ Too expensive! 1 lot costs ₹{min_cost:.0f}, capital ₹{results['capital']:.0f}. Skipping.")
            time.sleep(30)
            continue

        qty = get_quantity(best_index, entry, results['capital'])
        print(f"   Premium  : ₹{entry:.2f} (REAL price)")
        print(f"   Quantity : {qty}")
        print(f"   Value    : ₹{entry*qty:.2f} (FAKE money)")

        trades_today += 1

        # Monitor with real prices
        reason, pnl = demo_monitor(obj, entry, symbol, token, qty, nfo)

        # Update results
        results['capital']      += pnl
        results['total_pnl']    += pnl
        results['total_trades'] += 1
        daily_pnl               += pnl

        if pnl > 0:
            results['winning_trades'] += 1
            daily_loss = max(0, daily_loss)
        else:
            results['losing_trades'] += 1
            daily_loss += abs(pnl)

        # Save results
        results['trades'].append({
            "trade":   trades_today,
            "date":    str(datetime.date.today()),
            "symbol":  symbol,
            "signal":  best_signal,
            "score":   best_score,
            "entry":   entry,
            "exit":    reason,
            "pnl":     round(pnl, 2)
        })
        save_demo_results(results)

        # Trade summary
        accuracy = results['winning_trades'] / results['total_trades'] * 100
        print(f"\n📋 Trade #{trades_today} Done")
        print(f"   Exit     : {reason}")
        print(f"   P&L      : ₹{pnl:+.2f} (FAKE)")
        print(f"   Capital  : ₹{results['capital']:.2f} (FAKE)")
        print(f"   Accuracy : {accuracy:.1f}%")
        print(f"   Daily P&L: ₹{daily_pnl:+.2f}")
        print("-" * 40)

        time.sleep(10)

    # Final report
    print_accuracy(results)
    save_demo_results(results)

# ═══════════════════════════════════════════════════
#  START
# ═══════════════════════════════════════════════════
if __name__ == "__main__":
    run_demo()
