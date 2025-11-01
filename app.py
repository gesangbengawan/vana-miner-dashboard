from flask import Flask, render_template_string, request, session
from web3 import Web3
import requests
from datetime import datetime
import threading
import time

app = Flask(__name__)
app.secret_key = "vana-miner-bro-2025"

# === KONFIG ===
RPC_ENDPOINT = "https://rpc.vana.org"
CONTRACT_ADDRESS = "0x0CC1Bc0131DD9782e65ca0319Cd3a60eBA3a932d"
VANASCAN_API = "https://vanascan.io/api"
w3 = Web3(Web3.HTTPProvider(RPC_ENDPOINT))

ABI = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)

WALLETS = [
    {"name": "RDP1",  "address": "0x969Cc633F02106CDeB430eC3c294870C62B9D11B"},
    {"name": "RDP2",  "address": "0x3473755d5A4DEa305598A3575056EcED4FEa8071"},
    {"name": "RDP3",  "address": "0xE6861f7079305D1edE0de87573b04Be235808272"},
    {"name": "RDP4",  "address": "0x48C251B84978b3DF7e2c3E5eED49514cDdA0312E"},
    {"name": "RDP5",  "address": "0x6f85574694060B8c647c29564079Cf82FC129325"},
    {"name": "RDP6",  "address": "0x67B1Cc39B662b44592D4efF8Ed94cc413eD5770F"},
    {"name": "RDP7",  "address": "0x8036145d67f750AcaF84aeB85d0a667d8dC3692D"},
    {"name": "RDP8",  "address": "0xc6CD242e13D1bfCAC1F6d8D8d50E3DB67a09AbF7"},
    {"name": "RDP9",  "address": "0xC8028FBF6826634551a4Fb3D783FE09578642677"},
    {"name": "RDP10", "address": "0xCDCdA001e3cD234f9D08e9bD0f75F718B9dDa1b2"},
    {"name": "RDP11", "address": "0x70F8c59c263160E726dFA9a358060Aa4bbB63b62"},
    {"name": "RDP12", "address": "0x8dB5D5c57a4720aede211D14b09A486DE2934810"},
    {"name": "RDP13", "address": "0x8eD4e0E7BA2dA7Aa967897A18e993f84f8F9e895"}
]

# === CACHE + NOTIF ===
cache = {"data": {}, "last_balances": {}, "notifications": [], "last_update": 0}
cache_lock = threading.Lock()

def time_ago(ts):
    diff = datetime.now() - datetime.fromtimestamp(ts)
    if diff.total_seconds() < 60: return "baru saja"
    if diff.total_seconds() < 3600: return f"{int(diff.total_seconds()//60)} menit lalu"
    if diff.total_seconds() < 86400:
        h = int(diff.total_seconds()//3600)
        m = int((diff.total_seconds()%3600)//60)
        return f"{h} jam {m} menit lalu" if m else f"{h} jam lalu"
    return f"{int(diff.total_seconds()//86400)} hari lalu"

def fetch_wallet_data(wallet):
    addr = wallet['address']
    balance = 0.0
    try:
        balance = float(w3.from_wei(contract.functions.balanceOf(addr).call(), 'ether'))
    except: pass

    txs = []
    try:
        url = f"{VANASCAN_API}?module=account&action=tokentx&contractaddress={CONTRACT_ADDRESS}&address={addr}&page=1&offset=50&sort=desc"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200 and resp.json().get('status') == '1':
            for tx in resp.json()['result']:
                if tx['to'].lower() == addr.lower():
                    val = float(tx['value']) / 1e18
                    txs.append({
                        "hash": tx['hash'][:10] + "...",
                        "value": val,
                        "time_ago": time_ago(int(tx['timeStamp'])),
                        "timestamp": int(tx['timeStamp'])
                    })
    except: pass

    today = sum(t['value'] for t in txs if (datetime.now() - datetime.fromtimestamp(t['timestamp'])).days == 0)
    return {"balance": balance, "txs": txs, "today": today}

def background_updater():
    while True:
        new_data = {}
        for w in WALLETS:
            new_data[w['address']] = fetch_wallet_data(w)
        
        with cache_lock:
            for w in WALLETS:
                addr = w['address']
                old_bal = cache["last_balances"].get(addr, 0)
                new_bal = new_data[addr]["balance"]
                if new_bal > old_bal + 0.0001:
                    reward = new_bal - old_bal
                    notif = {
                        "id": int(time.time() * 1000),
                        "rdp": w['name'],
                        "amount": reward,
                        "time": datetime.now().strftime("%H:%M:%S")
                    }
                    cache["notifications"].append(notif)
                    cache["last_balances"][addr] = new_bal
            
            cache["data"] = new_data
            cache["last_update"] = datetime.now().strftime("%H:%M:%S")
        
        time.sleep(10)

threading.Thread(target=background_updater, daemon=True).start()

# === TEMA ===
THEMES = {
    "dark": """
        :root {--bg:#0a0a0a; --card:#1a1a1a; --text:#eee; --accent:#00ff88; --border:#333; --notif:#004400;}
        body {background:var(--bg); color:var(--text);}
        .card {background:var(--card); border:1px solid var(--border);}
        .name, .bal, .value {color:var(--accent);}
        .notif {background:var(--notif); border-left:4px solid var(--accent); position:relative; padding-right:30px;}
        .notif .close {position:absolute; right:8px; top:8px; font-size:18px; cursor:pointer; opacity:0.7;}
        .notif .close:hover {opacity:1;}
        .tx-item {font-size:14px; padding:10px; border-radius:8px; background:#111; margin:4px;}
        .tx-hash {font-weight:bold; font-size:13px;}
        .tx-value {color:var(--accent); font-weight:bold;}
        .tx-time {font-size:12px; color:#888;}
    """,
    "light": """
        :root {--bg:#f8f9fa; --card:#ffffff; --text:#212529; --accent:#007bff; --border:#dee2e6; --notif:#d4edda;}
        body {background:var(--bg); color:var(--text);}
        .card {background:var(--card); border:1px solid var(--border);}
        .name, .bal, .value {color:var(--accent);}
        .notif {background:var(--notif); border-left:4px solid var(--accent); position:relative; padding-right:30px;}
        .notif .close {position:absolute; right:8px; top:8px; font-size:18px; cursor:pointer; opacity:0.7;}
        .notif .close:hover {opacity:1;}
        .tx-item {font-size:14px; padding:10px; border-radius:8px; background:#f1f3f5; margin:4px;}
        .tx-hash {font-weight:bold; font-size:13px;}
        .tx-value {color:var(--accent); font-weight:bold;}
        .tx-time {font-size:12px; color:#666;}
    """,
    "matrix": """
        @import url('https://fonts.googleapis.com/css2?family=Orbitron&display=swap');
        :root {--bg:#000; --card:#111; --text:#0f0; --accent:#0f0; --border:#0f0; --notif:#004400;}
        body {background:var(--bg); color:var(--text); font-family:'Orbitron',monospace;}
        .card {background:var(--card); border:1px solid var(--border);}
        .name, .bal, .value {color:var(--accent); text-shadow:0 0 5px #0f0;}
        .notif {background:var(--notif); border-left:4px solid #0f0; position:relative; padding-right:30px;}
        .notif .close {position:absolute; right:8px; top:8px; font-size:18px; cursor:pointer; opacity:0.7;}
        .notif .close:hover {opacity:1;}
        .tx-item {font-size:14px; padding:10px; border-radius:8px; background:#001100; margin:4px; border:1px solid #0f0;}
        .tx-hash {font-weight:bold; font-size:13px;}
        .tx-value {color:var(--accent); font-weight:bold;}
        .tx-time {font-size:12px; color:#0f0;}
    """
}

# === UTAMA (SAMA SEPERTI v6.1) ===
@app.route('/')
def index():
    theme = request.args.get('theme', session.get('theme', 'dark'))
    session['theme'] = theme
    css = THEMES.get(theme, THEMES['dark'])

    with cache_lock:
        data = cache["data"]
        update_time = cache["last_update"]
        notifs = cache["notifications"][-5:]

    total = sum(d['balance'] for d in data.values())

    html = f"""<!DOCTYPE html>
<html><head>
    <title>VFSN v6.2</title>
    <meta http-equiv="refresh" content="60">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        {css}
        * {{margin:0;padding:0;box-sizing:border-box;}}
        body {{font-family:'Segoe UI',sans-serif;padding:15px;}}
        .header {{text-align:center;margin:20px 0;}}
        .header h1 {{font-size:22px;}}
        .themes {{display:flex;gap:8px;justify-content:center;margin:15px 0;}}
        .theme-btn {{padding:6px 12px;border-radius:6px;font-size:12px;cursor:pointer;}}
        .notif-bar {{max-width:900px;margin:0 auto 15px;}}
        .notif {{padding:10px 12px 10px 12px; margin:6px 0; border-radius:8px; font-size:14px; transition:0.3s;}}
        .notif.swipe {{transform:translateX(-100%); opacity:0;}}
        .wallets {{display:grid;gap:12px;max-width:900px;margin:auto;}}
        .wallet-card {{padding:14px;border-radius:10px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;}}
        .name {{font-weight:bold;font-size:17px;}}
        .addr {{font-size:12px;opacity:0.8;}}
        .bal {{font-weight:bold;font-size:16px;}}
        @media (max-width:600px) {{.wallets{{grid-template-columns:1fr;}}}}
        @media (min-width:601px) {{.wallets{{grid-template-columns:repeat(2,1fr);}}}}
    </style>
    <script>
        let startX = 0;
        function handleTouchStart(e, id) {{ startX = e.changedTouches[0].screenX; }}
        function handleTouchEnd(e, id) {{
            const endX = e.changedTouches[0].screenX;
            if (Math.abs(endX - startX) > 50) {{
                const el = document.getElementById('notif-' + id);
                el.classList.add('swipe');
                setTimeout(() => el.remove(), 300);
                fetch('/clear_notif/' + id, {{method: 'POST'}});
            }}
        }}
        function deleteNotif(id) {{
            const el = document.getElementById('notif-' + id);
            el.classList.add('swipe');
            setTimeout(() => el.remove(), 300);
            fetch('/clear_notif/' + id, {{method: 'POST'}});
        }}
    </script>
</head><body>
    <div class="header">
        <h1>VFSN Miner Dashboard v6.2</h1>
        <div>Total: <strong>{total:.6f} VFSN</strong></div>
        <div style="font-size:11px;margin-top:4px;">Update: {update_time}</div>
    </div>
    <div class="themes">
        <a href="?theme=dark" class="theme-btn" style="background:#333;color:#fff;">Dark</a>
        <a href="?theme=light" class="theme-btn" style="background:#fff;color:#000;">Light</a>
        <a href="?theme=matrix" class="theme-btn" style="background:#000;color:#0f0;">Matrix</a>
    </div>
"""
    if notifs:
        html += '<div class="notif-bar">'
        for n in notifs:
            html += f'''
            <div class="notif" id="notif-{n["id"]}" 
                 ontouchstart="handleTouchStart(event, {n["id"]})" 
                 ontouchend="handleTouchEnd(event, {n["id"]})">
                <span>REWARD! {n["rdp"]} +{n["amount"]:.6f} VFSN ({n["time"]})</span>
                <span class="close" onclick="deleteNotif({n["id"]})">x</span>
            </div>
            '''
        html += '</div>'

    html += '<div class="wallets">'
    for w in WALLETS:
        d = data.get(w['address'], {})
        short = w['address'][:8] + "..." + w['address'][-6:]
        html += f'''
        <a href="/wallet/{w['address']}" style="text-decoration:none;color:inherit;">
            <div class="wallet-card">
                <div><div class="name">{w['name']}</div><div class="addr">{short}</div></div>
                <div class="bal">{d.get('balance',0):.6f}</div>
            </div>
        </a>
        '''
    html += "</div></body></html>"
    return html

@app.route('/clear_notif/<int:notif_id>', methods=['POST'])
def clear_notif(notif_id):
    with cache_lock:
        cache["notifications"] = [n for n in cache["notifications"] if n['id'] != notif_id]
    return "", 204

# === DETAIL: 5 KOLOM × 5 BARIS (25 TX) ===
@app.route('/wallet/<address>')
def detail(address):
    theme = session.get('theme', 'dark')
    css = THEMES.get(theme, THEMES['dark'])
    page = int(request.args.get('page', 1))
    per_page = 25

    wallet = next((w for w in WALLETS if w['address'] == address), None)
    if not wallet: return "Not Found", 404

    with cache_lock:
        d = cache["data"].get(address, {})

    txs = d.get('txs', [])
    total_pages = 2
    start = (page-1) * per_page
    page_txs = txs[start:start+per_page]

    # 5 kolom × 5 baris
    cols = [page_txs[i:i+5] for i in range(0, len(page_txs), 5)]

    html = f"""<!DOCTYPE html>
<html><head>
    <title>{wallet['name']} - Detail</title>
    <meta http-equiv="refresh" content="60">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        {css}
        body {{padding:15px;}}
        .back {{font-size:14px;margin-bottom:15px;display:inline-block;}}
        .card {{padding:18px;border-radius:12px;margin:12px 0;}}
        .title {{font-size:20px;font-weight:bold;}}
        .balance {{font-size:30px;text-align:center;margin:10px 0;}}
        .tx-grid {{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-top:15px;}}
        .tx-item {{font-size:14px;padding:12px;border-radius:10px;background:rgba(0,0,0,0.2);}}
        .tx-hash {{font-weight:bold;font-size:13px;}}
        .tx-value {{color:var(--accent);font-weight:bold;font-size:15px;}}
        .tx-time {{font-size:12px;color:#888;}}
        .pagination {{display:flex;gap:10px;justify-content:center;margin:20px 0;}}
        .page-btn {{padding:8px 16px;border-radius:8px;font-size:14px;text-decoration:none;}}
        .page-btn.active {{background:var(--accent);color:#000;font-weight:bold;}}
        @media (max-width:900px) {{.tx-grid{{grid-template-columns:repeat(3,1fr);}}}}
        @media (max-width:600px) {{.tx-grid{{grid-template-columns:1fr;}}}}
    </style>
</head><body>
    <a href="/" class="back">Back</a>
    <div class="card">
        <div class="title">{wallet['name']}</div>
        <div style="font-size:12px;word-break:break-all;margin:5px 0;">{address}</div>
        <div class="balance">{d.get('balance',0):.6f} VFSN</div>
        <div style="text-align:center;font-size:14px;">Hari ini: <strong>+{d.get('today',0):.6f} VFSN</strong></div>
    </div>
    <div class="card">
        <div style="margin-bottom:10px;font-weight:bold;">50 Transaksi Terakhir (Halaman {page}/2)</div>
        <div class="tx-grid">
"""
    for col in cols:
        for tx in col:
            html += f'''
            <div class="tx-item">
                <div class="tx-hash">{tx['hash']}</div>
                <div class="tx-value">+{tx['value']:.6f}</div>
                <div class="tx-time">{tx['time_ago']}</div>
            </div>
            '''
        # Fill empty cells
        for _ in range(5 - len(col)):
            html += '<div class="tx-item" style="visibility:hidden;"></div>'

    html += f"""
        </div>
        <div class="pagination">
"""
    for p in range(1, 3):
        active = "active" if p == page else ""
        html += f'<a href="?page={p}" class="page-btn {active}">{p}</a>'
    html += """
        </div>
    </div></body></html>
    """
    return html

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)