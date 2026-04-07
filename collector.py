import requests
from datetime import datetime
from supabase import create_client
import os

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 定義要抓取的幣種與對應的資料表
TARGETS = [
    {"symbol": "BTCUSDT", "table": "whale_data", "price_key": "btc_price"},
    {"symbol": "ETHUSDT", "table": "eth_whale_data", "price_key": "eth_price"}
]

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

            data = {
                "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                target["price_key"]: price,
                "long_vol_usd": oi_usd * float(res_pos.get('longPositionRatio', 0.5)),
                "short_vol_usd": oi_usd * float(res_pos.get('shortPositionRatio', 0.5)),
                "ls_ratio": float(res_pos.get('longPositionRatio', 0.5)) / float(res_pos.get('shortPositionRatio', 0.5)),
                "fund_rate": float(res_fund.get('fundingRate', 0.0)),
                "long_acc_ratio": float(res_acc['longAccountRatio']),
                "short_acc_ratio": float(res_acc['shortAccountRatio'])
            }

            supabase.table(target["table"]).insert(data).execute()
            print(f"{symbol} 寫入成功")
        except Exception as e:
            print(f"{symbol} 失敗: {e}")

if __name__ == "__main__":
    collect_data()
