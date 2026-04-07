import requests
from datetime import datetime
from supabase import create_client
import os

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")  # 取得 TG Token
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")      # 取得 TG Chat ID

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

TARGETS = [
    {"symbol": "BTCUSDT", "table": "whale_data", "price_key": "btc_price"},
    {"symbol": "ETHUSDT", "table": "eth_whale_data", "price_key": "eth_price"}
]

# 🚀 Telegram 發送通知模組
def send_tg_notify(msg):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        print("未設定 TG_BOT_TOKEN 或 TG_CHAT_ID，跳過通知")
        return
    
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML" # 支援簡單的 HTML 粗體/斜體
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Telegram 通知發送成功！")
        else:
            print(f"Telegram 發送失敗，狀態碼: {response.status_code}")
    except Exception as e:
        print(f"Telegram 通知發送異常: {e}")

def collect_data():
    base_url = "https://api.bitget.com/api/v2/mix/market"
    product = "productType=USDT-FUTURES"
    
    for target in TARGETS:
        symbol = target["symbol"]
        try:
            res_ticker = requests.get(f"{base_url}/ticker?symbol={symbol}&{product}").json()['data'][0]
            res_acc = requests.get(f"{base_url}/account-long-short?symbol={symbol}&{product}").json()['data'][0]
            res_pos = requests.get(f"{base_url}/position-long-short?symbol={symbol}&{product}").json()['data'][0]
            res_fund_data = requests.get(f"{base_url}/current-fund-rate?symbol={symbol}&{product}").json().get('data', [{}])
            res_fund = res_fund_data[0] if isinstance(res_fund_data, list) else res_fund_data

            price = float(res_ticker['lastPr'])
            oi_res = requests.get(f"{base_url}/open-interest?symbol={symbol}&{product}").json()['data']['openInterestList'][0]
            oi_usd = float(oi_res['size']) * price

            ls_acc_ratio = float(res_acc['longAccountRatio']) / float(res_acc['shortAccountRatio'])
            ls_pos_ratio = float(res_pos.get('longPositionRatio', 0.5)) / float(res_pos.get('shortPositionRatio', 0.5))

            data = {
                "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                target["price_key"]: price,
                "long_vol_usd": oi_usd * float(res_pos.get('longPositionRatio', 0.5)),
                "short_vol_usd": oi_usd * float(res_pos.get('shortPositionRatio', 0.5)),
                "ls_ratio": ls_pos_ratio,
                "fund_rate": float(res_fund.get('fundingRate', 0.0)),
                "long_acc_ratio": float(res_acc['longAccountRatio']),
                "short_acc_ratio": float(res_acc['shortAccountRatio'])
            }

            supabase.table(target["table"]).insert(data).execute()
            print(f"{symbol} 寫入成功")

            # 🚀 檢查背離並發送 TG 警報 (套用至 BTC 與 ETH)
            # 觸發條件：散戶極度看多 (帳戶比 > 1.2) 且 大戶偷偷做空 (持倉比 < 0.95)
            if ls_acc_ratio > 1.2 and ls_pos_ratio < 0.95:
                # 組裝美美的 Telegram 訊息格式
                alert_msg = (
                    f"⚠️ <b>【大戶背離警告】</b>\n"
                    f"幣種：#{symbol}\n"
                    f"價格：<b>${price:,}</b>\n"
                    f"──────────────\n"
                    f"👥 帳戶多空比：{ls_acc_ratio:.2f} (散戶偏多)\n"
                    f"💰 持倉多空比：{ls_pos_ratio:.2f} (大戶偏空)\n"
                    f"──────────────\n"
                    f"<i>請注意潛在的回調風險！</i>"
                )
                send_tg_notify(alert_msg)

        except Exception as e:
            print(f"{symbol} 失敗: {e}")

if __name__ == "__main__":
    collect_data()
