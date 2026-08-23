import pyotp
import time
import datetime
from SmartApi import SmartConnect
import pandas as pd
import ta

# ─── CREDENTIALS ────────────────────────────────────
CLIENT_ID    = "G57817669"
API_KEY      = "pkChF10O"
TOTP_SECRET  = "GAWUC3JHMVDVI3RSYHH7K53RCQ"
PASSWORD     = "2005"

# ─── BOT CONFIG ─────────────────────────────────────
MAX_AUTO_TRADES    = 4
TARGET_PERCENT     = 50
STOPLOSS_PERCENT   = 20
MAX_LOSS_PER_DAY   = 1000
CAPITAL            = 5000

# ─── INDEX CONFIG ───────────────────────────────────
INDEX_CONFIG = {
    "NIFTY": {
        "exchange": "NSE",
        "symbol":   "Nifty 50",
        "token":    "99926000",
        "step":     50,
        "lot":      25,
        "expiry_day": 3,   # Thursday
    },
    "BANKNIFTY": {
        "exchange": "NSE",
        "symbol":   "Nifty Bank",
        "token":    "99926009",
        "step":     100,
        "lot":      15,
        "expiry_day": 2,   # Wednesday
    },
    "SENSEX": {
        "exchange": "BSE",
        "symbol":   "SENSEX",
        "token":    "99919000",
        "step":     100,
        "lot":      10,
        "expiry_day": 4,   # Friday
    },
}

# ─── STATE ──────────────────────────────────────────
trades_today     = 0
total_loss_today = 0

# ─── LOGIN ──────────────────────────────────────────
def login():
    try:
        totp = pyotp.TOTP(TOTP_SECRET).now()
        obj  = SmartConnect(api_key=API_KEY)
        data = obj.generateSession(CLIENT_ID, PASSWORD, totp)
        if data['status']:
            print("✅ Login Successful!")
            return obj
        print(f"❌ Login Failed: {data}")
        exit()
    except Exception as e:
        print(f"❌ Login Error: {e}")
        exit()

# ─── MARKET HOURS ───────────────────────────────────
def is_market_open():
    now   = datetime.datetime.now()
    start = now.replace(hour=9,  minute=15, second=0, microsecond=0)
    end   = now.replace(hour=15, minute=30, second=0, microsecond=0)
    if now.weekday() >= 5:
        return False
    return start <= now <= end

# ─── NEAREST EXPIRY ─────────────────────────────────
def get_nearest_expiry(index="NIFTY"):
    """
    Returns expiry string in Angel One format: DDMMMYY (e.g. 03JUL26)
    """
    today       = datetime.date.today()
    target_day  = INDEX_CONFIG[index]["expiry_day"]
    days_ahead  = (target_day - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    expiry = today + datetime.timedelta(days=days_ahead)
    return expiry.strftime("%d%b%y").upper()   # e.g. 03JUL26

# ─── BUILD OPTION SYMBOL ────────────────────────────
def build_option_symbol(index, expiry_str, strike, option_type):
    """
    Builds symbol like: NIFTY03JUL2624000CE
    """
    return f"{index}{expiry_str}{int(strike)}{option_type}"

# ─── LOOKUP TOKEN ───────────────────────────────────
def lookup_token(obj, symbol):
    """
    Searches Angel One for the token of a given option symbol.
    """
    try:
        # Extract index name for search
        index = symbol[:len([k for k in INDEX_CONFIG if symbol.startswith(k)][0])]
        result = obj.searchScrip("NFO", symbol)
        if result and result.get('data'):
            for item in result['data']:
                if item['tradingsymbol'] == symbol:
                    return item['symboltoken']
        print(f"⚠️ Token not found for: {symbol}")
        return None
    except Exception as e:
        print(f"⚠️ Token lookup error: {e}")
        return None

# ─── LIVE INDEX PRICE ───────────────────────────────
def get_index_price(obj, index):
    cfg = INDEX_CONFIG[index]
    try:
        data = obj.ltpData(cfg["exchange"], cfg["symbol"], cfg["token"])
        return data['data']['ltp']
    except Exception as e:
        print(f"⚠️ Price fetch error {index}: {e}")
        return None

# ─── LIVE OPTION PRICE ──────────────────────────────
def get_option_ltp(obj, symbol, token):
    try:
        data = obj.ltpData("NFO", symbol, token)
        return data['data']['ltp']
    except Exception as e:
        print(f"⚠️ Option LTP error: {e}")
        return None

# ─── CANDLE DATA ────────────────────────────────────
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
            df['close'] = pd.to_numeric(df['close'])
            return df
        print(f"⚠️ No candle data for {index}")
        return None
    except Exception as e:
        print(f"⚠️ Candle error {index}: {e}")
        return None

# ─── ANALYZE MARKET ─────────────────────────────────
def analyze_market(obj, index):
    ltp = get_index_price(obj, index)
    if not ltp:
        return None, None

    df = get_candle_data(obj, index)
    if df is None or len(df) < 20:
        print(f"⚠️ Not enough data for {index}")
        return None, None

    df['rsi']   = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    df['ema20'] = ta.trend.EMAIndicator(df['close'],    window=20).ema_indicator()

    rsi   = df['rsi'].iloc[-1]
    ema   = df['ema20'].iloc[-1]
    price = df['close'].iloc[-1]

    print(f"\n📊 {index} | Price:₹{ltp} | RSI:{rsi:.1f} | EMA:{ema:.1f}")

    if rsi < 40 and price > ema:
        print(f"   → BULLISH signal → BUY CE")
        return "CE", ltp
    elif rsi > 60 and price < ema:
        print(f"   → BEARISH signal → BUY PE")
        return "PE", ltp
    else:
        print(f"   → No signal (RSI in neutral zone)")
        return None, None

# ─── GET STRIKE ─────────────────────────────────────
def get_strike(ltp, index):
    step   = INDEX_CONFIG[index]["step"]
    return round(ltp / step) * step

# ─── GET QUANTITY ────────────────────────────────────
def get_quantity(index, premium):
    lot = INDEX_CONFIG[index]["lot"]
    if premium and premium > 0:
        lots = max(1, int(CAPITAL / (premium * lot)))
    else:
        lots = 1
    return lots * lot

# ─── PLACE ORDER ────────────────────────────────────
def place_order(obj, symbol, token, qty, txn_type="BUY"):
    print(f"\n🚀 {txn_type}: {symbol} | Qty:{qty}")
    try:
        order = {
            "variety":         "NORMAL",
            "tradingsymbol":   symbol,
            "symboltoken":     token,
            "transactiontype": txn_type,
            "exchange":        "NFO",
            "ordertype":       "MARKET",
            "producttype":     "INTRADAY",
            "duration":        "DAY",
            "quantity":        qty,
        }
        res = obj.placeOrder(order)
        if res and res.get('data'):
            print(f"✅ Order ID: {res['data']['orderid']}")
            return res['data']['orderid']
        print(f"⚠️ Order failed: {res}")
        return None
    except Exception as e:
        print(f"❌ Order error: {e}")
        return None

# ─── MONITOR POSITION ───────────────────────────────
def monitor_position(obj, entry, symbol, token, qty):
    target = entry * (1 + TARGET_PERCENT   / 100)
    sl     = entry * (1 - STOPLOSS_PERCENT / 100)

    print(f"\n👁️  Monitoring: {symbol}")
    print(f"   Entry  : ₹{entry:.2f}")
    print(f"   Target : ₹{target:.2f} (+{TARGET_PERCENT}%)")
    print(f"   SL     : ₹{sl:.2f}  (-{STOPLOSS_PERCENT}%)")

    while True:
        try:
            # Square off at 15:15
            now = datetime.datetime.now()
            if now >= now.replace(hour=15, minute=15, second=0, microsecond=0):
                ltp = get_option_ltp(obj, symbol, token) or entry
                pnl = (ltp - entry) * qty
                print(f"\n⏰ Square off time! P&L: ₹{pnl:+.2f}")
                place_order(obj, symbol, token, qty, "SELL")
                return "SQUAREOFF", pnl

            ltp = get_option_ltp(obj, symbol, token)
            if ltp is None:
                time.sleep(5)
                continue

            pnl = (ltp - entry) * qty
            print(f"   LTP:₹{ltp:.2f} | P&L:₹{pnl:+.2f}   ", end='\r')

            if ltp >= target:
                print(f"\n🎯 TARGET HIT! ₹{ltp:.2f} | Profit:₹{pnl:+.2f}")
                place_order(obj, symbol, token, qty, "SELL")
                return "TARGET", pnl

            if ltp <= sl:
                print(f"\n🛑 STOP LOSS HIT! ₹{ltp:.2f} | Loss:₹{pnl:+.2f}")
                place_order(obj, symbol, token, qty, "SELL")
                return "STOPLOSS", pnl

            time.sleep(5)

        except Exception as e:
            print(f"\n⚠️ Monitor error: {e}")
            time.sleep(5)

# ─── MAIN LOOP ──────────────────────────────────────
def run_bot():
    global trades_today, total_loss_today

    print("=" * 55)
    print("🤖  ANGEL ONE OPTIONS TRADING BOT")
    print("=" * 55)
    print(f"   Indices         : NIFTY, BANKNIFTY, SENSEX")
    print(f"   Max Auto Trades : {MAX_AUTO_TRADES}")
    print(f"   Target          : {TARGET_PERCENT}%")
    print(f"   Stop Loss       : {STOPLOSS_PERCENT}%")
    print(f"   Max Daily Loss  : ₹{MAX_LOSS_PER_DAY}")
    print(f"   Capital/Trade   : ₹{CAPITAL}")
    print("=" * 55)

    obj     = login()
    indices = list(INDEX_CONFIG.keys())

    while True:
        # Market hours check
        if not is_market_open():
            print("\n⏰ Market closed. Waiting 60s...")
            time.sleep(60)
            continue

        # Daily loss check
        if total_loss_today >= MAX_LOSS_PER_DAY:
            print(f"\n🛑 Max daily loss hit (₹{total_loss_today:.2f}). Bot stopped.")
            break

        # After 4 auto trades — wait for manual input
        if trades_today >= MAX_AUTO_TRADES:
            try:
                cmd = input(
                    f"\n⏸️  {MAX_AUTO_TRADES} auto trades done. "
                    "Type 'trade' for 1 more or 'stop' to exit: "
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n👋 Exiting.")
                break

            if cmd == 'stop':
                print("👋 Bot stopped.")
                break
            elif cmd == 'trade':
                trades_today = MAX_AUTO_TRADES - 1
            else:
                print("❓ Type 'trade' or 'stop'.")
                continue

        # Scan for signal
        best_signal = best_index = best_ltp = None
        for index in indices:
            signal, ltp = analyze_market(obj, index)
            if signal:
                best_signal, best_index, best_ltp = signal, index, ltp
                break

        if not best_signal:
            print("\n⏳ No signal. Rechecking in 60s...")
            time.sleep(60)
            continue

        # Build option details
        expiry     = get_nearest_expiry(best_index)
        strike     = get_strike(best_ltp, best_index)
        symbol     = build_option_symbol(best_index, expiry, strike, best_signal)
        token      = lookup_token(obj, symbol)

        print(f"\n🎯 SIGNAL: {symbol}")
        print(f"   Expiry : {expiry}")
        print(f"   Strike : {strike}")
        print(f"   Type   : {best_signal}")

        if not token:
            print("⚠️ Token not found. Skipping.")
            time.sleep(30)
            continue

        # Get premium & quantity
        entry = get_option_ltp(obj, symbol, token)
        if not entry:
            print("⚠️ Could not get option price. Skipping.")
            time.sleep(30)
            continue

        qty = get_quantity(best_index, entry)
        print(f"   Premium  : ₹{entry:.2f}")
        print(f"   Quantity : {qty}")
        print(f"   Capital  : ₹{entry * qty:.2f}")
        print(f"   Trade No : {trades_today + 1}/{MAX_AUTO_TRADES}")

        # Place BUY order
        order_id = place_order(obj, symbol, token, qty, "BUY")
        if not order_id:
            print("⚠️ Order failed. Skipping.")
            time.sleep(30)
            continue

        trades_today += 1

        # Monitor & auto exit
        reason, pnl = monitor_position(obj, entry, symbol, token, qty)

        if pnl < 0:
            total_loss_today += abs(pnl)

        print(f"\n📋 Trade #{trades_today} Done")
        print(f"   Exit   : {reason}")
        print(f"   P&L    : ₹{pnl:+.2f}")
        print(f"   Loss   : ₹{total_loss_today:.2f}/₹{MAX_LOSS_PER_DAY}")
        print("-" * 40)

        time.sleep(10)

    print(f"\n✅ Session ended | Trades:{trades_today} | Loss:₹{total_loss_today:.2f}")

# ─── START ──────────────────────────────────────────
if __name__ == "__main__":
    run_bot()
