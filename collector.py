import requests
from datetime import datetime
from supabase import create_client
import os

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

symbol = "BTCUSDT"

def collect_data():
    base_url = "https://api.bitget.com/api/v2/mix/market"
    product = "productType=USDT-FUTURES"
    
    try:
        # 抓取數據
        res_ticker = requests.get(f"{base_url}/ticker?symbol={symbol}&{product}").json()['data'][0]
        res_acc = requests.get(f"{base_url}/account-long-short?symbol={symbol}&{product}").json()['data'][0]
        res_pos = requests.get(f"{base_url}/position-long-short?symbol={symbol}&{product}").json()['data'][0]
        res_oi = requests.get(f"{base_url}/open-interest?symbol={symbol}&{product}").json()['data']['openInterestList'][0]
        res_fund_data = requests.get(f"{base_url}/current-fund-rate?symbol={symbol}&{product}").json().get('data', [{}])
        res_fund = res_fund_data[0] if isinstance(res_fund_data, list) else res_fund_data

        price = float(res_ticker['lastPr'])
        oi_usd = float(res_oi['size']) * price

        data = {
            "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "btc_price": price,
            "oi_total_usd": oi_usd,
            "long_vol_usd": oi_usd * float(res_pos.get('longPositionRatio', 0.5)),
            "short_vol_usd": oi_usd * float(res_pos.get('shortPositionRatio', 0.5)),
            "ls_ratio": round(float(res_pos.get('longPositionRatio', 0.5)) / float(res_pos.get('shortPositionRatio', 0.5)), 4),
            "fund_rate": float(res_fund.get('fundingRate', 0.0)),
            "long_acc_ratio": float(res_acc['longAccountRatio']),
            "short_acc_ratio": float(res_acc['shortAccountRatio'])
        }

        supabase.table("whale_data").insert(data).execute()
        print(f"寫入成功: {data['time']}")
    except Exception as e:
        print(f"失敗: {e}")

if __name__ == "__main__":
    collect_data()
