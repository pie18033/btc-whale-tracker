# ... 前面 import 部分不變 ...

def collect_data():
    # ... API URL 部分 ...
    # 確保這行有在裡面：
    url_account = f"https://api.bitget.com/api/v2/mix/market/account-long-short?symbol={symbol}&productType=USDT-FUTURES"
    
    try:
        # 抓取各端點資料
        res_ticker = requests.get(url_ticker).json()['data'][0]
        res_acc = requests.get(url_account).json()['data'][0] # 帳戶比例
        res_pos = requests.get(url_position).json()['data'][0]
        res_oi = requests.get(url_oi).json()['data']['openInterestList'][0]
        res_fund_raw = requests.get(url_fund).json().get('data', [{}])
        res_fund = res_fund_raw[0] if isinstance(res_fund_raw, list) else res_fund_raw

        data = {
            "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "btc_price": float(res_ticker['lastPr']),
            "oi_total_usd": float(res_oi['size']) * float(res_ticker['lastPr']),
            "long_vol_usd": (float(res_oi['size']) * float(res_ticker['lastPr'])) * float(res_pos.get('longPositionRatio', 0.5)),
            "short_vol_usd": (float(res_oi['size']) * float(res_ticker['lastPr'])) * float(res_pos.get('shortPositionRatio', 0.5)),
            "ls_ratio": round(float(res_pos.get('longPositionRatio', 0.5)) / float(res_pos.get('shortPositionRatio', 0.5)), 4),
            "fund_rate": float(res_fund.get('fundingRate', 0.0)),
            # 新增這兩行：
            "long_acc_ratio": float(res_acc['longAccountRatio']),
            "short_acc_ratio": float(res_acc['shortAccountRatio'])
        }

        supabase.table("whale_data").insert(data).execute()
        print(f"成功寫入全數據: {data['time']}")
    except Exception as e:
        print(f"寫入失敗: {e}")

# ... 後面啟動部分不變 ...
