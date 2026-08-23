import pyotp
from SmartApi import SmartConnect

# Credentials
CLIENT_ID = "G57817669"
API_KEY = "pkChF10O"
TOTP_SECRET = "GAWUC3JHMVDVI3RSYHH7K53RCQ"
PASSWORD = "2005"

# Login
totp = pyotp.TOTP(TOTP_SECRET).now()
obj = SmartConnect(api_key=API_KEY)
data = obj.generateSession(CLIENT_ID, PASSWORD, totp)

if not data['status']:
    print("❌ Login Failed!")
    exit()

print("✅ Login Successful!")
auth_token = data['data']['jwtToken']

# ─── FETCH LIVE PRICE ───────────────────────────────
def get_live_price(symbol, token):
    price_data = obj.ltpData("NSE", symbol, token)
    return price_data['data']['ltp']

# ─── PLACE BUY ORDER ────────────────────────────────
def buy(symbol, token, quantity):
    order = {
        "variety": "NORMAL",
        "tradingsymbol": symbol,
        "symboltoken": token,
        "transactiontype": "BUY",
        "exchange": "NSE",
        "ordertype": "MARKET",
        "producttype": "INTRADAY",
        "duration": "DAY",
        "quantity": quantity
    }
    response = obj.placeOrder(order)
    print(f"✅ BUY Order Placed! Order ID: {response['data']['orderid']}")
    return response

# ─── PLACE SELL ORDER ───────────────────────────────
def sell(symbol, token, quantity):
    order = {
        "variety": "NORMAL",
        "tradingsymbol": symbol,
        "symboltoken": token,
        "transactiontype": "SELL",
        "exchange": "NSE",
        "ordertype": "MARKET",
        "producttype": "INTRADAY",
        "duration": "DAY",
        "quantity": quantity
    }
    response = obj.placeOrder(order)
    print(f"✅ SELL Order Placed! Order ID: {response['data']['orderid']}")
    return response

# ─── SIMPLE TRADING STRATEGY ────────────────────────
def run_bot():
    SYMBOL = "RELIANCE-EQ"
    TOKEN = "2885"
    QUANTITY = 1          # Number of shares
    BUY_TARGET = 1310.0   # Buy if price drops to this
    SELL_TARGET = 1325.0  # Sell if price rises to this
    STOP_LOSS = 1305.0    # Exit if price falls below this

    print("\n🤖 Bot Started! Watching RELIANCE...\n")

    ltp = get_live_price(SYMBOL, TOKEN)
    print(f"📈 Current Price: ₹{ltp}")
    print(f"🎯 Buy Target:   ₹{BUY_TARGET}")
    print(f"🎯 Sell Target:  ₹{SELL_TARGET}")
    print(f"🛑 Stop Loss:    ₹{STOP_LOSS}")

    if ltp <= BUY_TARGET:
        print(f"\n💚 Price ₹{ltp} hit BUY target! Placing BUY order...")
        buy(SYMBOL, TOKEN, QUANTITY)

    elif ltp >= SELL_TARGET:
        print(f"\n🔴 Price ₹{ltp} hit SELL target! Placing SELL order...")
        sell(SYMBOL, TOKEN, QUANTITY)

    elif ltp <= STOP_LOSS:
        print(f"\n🛑 STOP LOSS hit at ₹{ltp}! Exiting position...")
        sell(SYMBOL, TOKEN, QUANTITY)

    else:
        print(f"\n⏳ Price ₹{ltp} — No action needed yet.")

# ─── RUN ────────────────────────────────────────────
run_bot()
