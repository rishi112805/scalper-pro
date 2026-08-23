import threading
import json
import time
import pyotp
from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2

# ─── CREDENTIALS ────────────────────────────────────
CLIENT_ID   = "G57817669"
API_KEY     = "pkChF10O"
TOTP_SECRET = "GAWUC3JHMVDVI3RSYHH7K53RCQ"
PASSWORD    = "2005"

# ─── LIVE PRICE STORE ───────────────────────────────
live_prices = {
    "NIFTY":     None,
    "BANKNIFTY": None,
    "SENSEX":    None,
}

TOKEN_MAP = {
    "99926000": "NIFTY",
    "99926009": "BANKNIFTY",
    "99919000": "SENSEX",
}

# Global WebSocket object
sws = None

# ─── LOGIN ──────────────────────────────────────────
def login():
    totp = pyotp.TOTP(TOTP_SECRET).now()
    obj  = SmartConnect(api_key=API_KEY)
    data = obj.generateSession(CLIENT_ID, PASSWORD, totp)
    if data['status']:
        print("✅ Login OK")
        return obj, data['data']['jwtToken'], data['data']['feedToken']
    print("❌ Login Failed")
    exit()

# ─── CALLBACKS ──────────────────────────────────────
def on_open(wsapp):
    print("🔌 WebSocket Connected! Subscribing...")
    global sws
    token_list = [
        {"exchangeType": 1, "tokens": ["99926000", "99926009"]},
        {"exchangeType": 3, "tokens": ["99919000"]},
    ]
    sws.subscribe("feed_1", 3, token_list)
    print("✅ Subscribed! Waiting for data...")

def on_data(wsapp, message):
    try:
        data  = json.loads(message)
        token = str(data.get('tk', ''))
        ltp   = data.get('ltp')
        if token in TOKEN_MAP and ltp:
            index = TOKEN_MAP[token]
            live_prices[index] = float(ltp)
            n = live_prices['NIFTY']
            b = live_prices['BANKNIFTY']
            s = live_prices['SENSEX']
            print(f"\r⚡ NIFTY:₹{n}  BANKNIFTY:₹{b}  SENSEX:₹{s}    ", end='')
    except Exception as e:
        pass

def on_error(wsapp, error):
    print(f"\n⚠️ Error: {error}")

def on_close(wsapp):
    print("\n🔌 WebSocket Closed")

# ─── START ──────────────────────────────────────────
def start_websocket(jwt_token, feed_token):
    global sws
    sws = SmartWebSocketV2(
        auth_token=jwt_token,
        api_key=API_KEY,
        client_code=CLIENT_ID,
        feed_token=feed_token
    )
    sws.on_open  = on_open
    sws.on_data  = on_data
    sws.on_error = on_error
    sws.on_close = on_close
    sws.connect()

if __name__ == "__main__":
    print("⚡ Starting Fast Price Feed...")
    obj, jwt_token, feed_token = login()

    ws_thread = threading.Thread(
        target=start_websocket,
        args=(jwt_token, feed_token),
        daemon=True
    )
    ws_thread.start()

    print("Waiting for connection...\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Stopped!")
