import requests
from datetime import datetime
from supabase import create_client
import os

# 從環境變數讀取金鑰（之後會在 GitHub 設定，這能保護你的隱私）
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

symbol = "BTCUSDT"

def collect_data():
    # 這裡的 API 抓取邏輯跟你原本的一樣
    url_ticker = f"https://api.bitget.com/api/v2/mix/market/ticker?symbol={symbol}&productType=USDT-FUTURES"
    url_account = f"https://api.bitget.com/api/v2/mix/market/account-long-short?symbol={symbol}&productType=USDT-FUTURES"
    url_position = f"https://api.bitget.com/api/v2/mix/market/position-long-short?symbol={symbol}&productType=USDT-FUTURES"
    url_oi = f"https://api.bitget.com/api/v2/mix/market/open-interest?symbol={symbol}&productType=USDT-FUTURES"
    url_fund = f"https://api.bitget.com/api/v2/mix/market/current-fund-rate?symbol={symbol}&productType=USDT-FUTURES"

    try:
        res_ticker = requests.get(url_ticker).json()['data'][0]
        res_acc = requests.get(url_account).json()['data'][0]
        res_pos = requests.get(url_position).json()['data'][0]
        res_oi = requests.get(url_oi).json()['data']['openInterestList'][0]
        res_fund_raw = requests.get(url_fund).json().get('data', [{}])
        res_fund = res_fund_raw[0] if isinstance(res_fund_raw, list) else res_fund_raw

        # 整理數據
        data = {
            "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "btc_price": float(res_ticker['lastPr']),
            "oi_total_usd": float(res_oi['size']) * float(res_ticker['lastPr']),
            "long_vol_usd": (float(res_oi['size']) * float(res_ticker['lastPr'])) * float(res_pos.get('longPositionRatio', 0.5)),
            "short_vol_usd": (float(res_oi['size']) * float(res_ticker['lastPr'])) * float(res_pos.get('shortPositionRatio', 0.5)),
            "ls_ratio": round(float(res_pos.get('longPositionRatio', 0.5)) / float(res_pos.get('shortPositionRatio', 0.5)), 4),
            "fund_rate": float(res_fund.get('fundingRate', 0.0))
        }

        # 寫入 Supabase 資料表
        response = supabase.table("whale_data").insert(data).execute()
        print(f"成功寫入資料: {data['time']}")

    except Exception as e:
        print(f"寫入失敗: {e}")

if __name__ == "__main__":
    collect_data()