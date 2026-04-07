import streamlit as st
import requests
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import time

# 設定頁面與樣式
st.set_page_config(page_title="比特幣大戶籌碼面板", layout="wide")

st.markdown("""
    <style>
           .block-container {
                padding-top: 2rem; 
                padding-bottom: 0rem;
                padding-left: 2rem;
                padding-right: 2rem;
            }
            [data-testid="stMetricValue"] {
                font-size: 1.8rem;
                font-weight: bold;
            }
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.title("⚙️ 監控設定")
    auto_refresh = st.checkbox("啟動自動紀錄與更新", value=True) 
    refresh_rate = st.number_input("更新頻率 (秒)", min_value=5, value=10) 

symbol = "BTCUSDT"
csv_filename = "history_data_v8.csv"

# API 接口通道
url_ticker = f"https://api.bitget.com/api/v2/mix/market/ticker?symbol={symbol}&productType=USDT-FUTURES"
url_account = f"https://api.bitget.com/api/v2/mix/market/account-long-short?symbol={symbol}&productType=USDT-FUTURES"
url_position = f"https://api.bitget.com/api/v2/mix/market/position-long-short?symbol={symbol}&productType=USDT-FUTURES"
url_oi = f"https://api.bitget.com/api/v2/mix/market/open-interest?symbol={symbol}&productType=USDT-FUTURES"
url_fund = f"https://api.bitget.com/api/v2/mix/market/current-fund-rate?symbol={symbol}&productType=USDT-FUTURES"

res_ticker = requests.get(url_ticker)
res_acc = requests.get(url_account)
res_pos = requests.get(url_position)
res_oi = requests.get(url_oi)
res_fund = requests.get(url_fund)

if all(r.status_code == 200 for r in [res_ticker, res_acc, res_pos, res_oi, res_fund]):
    try:
        # 資料解析
        data_ticker = res_ticker.json()['data'][0]
        data_acc = res_acc.json()['data'][0] 
        data_pos = res_pos.json()['data'][0]
        data_oi = res_oi.json()['data']['openInterestList'][0]
        data_fund_raw = res_fund.json().get('data', [{}])
        data_fund = data_fund_raw[0] if isinstance(data_fund_raw, list) else data_fund_raw
        
        fund_rate = float(data_fund.get('fundingRate', data_fund.get('fundRate', 0.0)))
        btc_price = float(data_ticker['lastPr'])
        oi_total_btc = float(data_oi['size'])
        oi_total_usd = oi_total_btc * btc_price
        readable_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        long_acc = float(data_acc['longAccountRatio'])
        short_acc = float(data_acc['shortAccountRatio'])
        real_ls_ratio_acc = round(long_acc / short_acc, 4)
        long_pos_ratio = float(data_pos.get('longPositionRatio', data_pos.get('longRatio', 0.5)))
        short_pos_ratio = float(data_pos.get('shortPositionRatio', data_pos.get('shortRatio', 0.5)))
        real_ls_ratio_pos = round(long_pos_ratio / short_pos_ratio, 4)
        
        long_vol_usd = round(oi_total_usd * long_pos_ratio, 2)
        short_vol_usd = round(oi_total_usd * short_pos_ratio, 2)
        
        # 寫入歷史 CSV
        if not os.path.exists(csv_filename):
            with open(csv_filename, 'w', encoding='utf-8') as f:
                f.write("Time,BTC_Price,OI_Total_USD,Long_Vol_USD,Short_Vol_USD,LS_Ratio,Fund_Rate\n")
        with open(csv_filename, 'a', encoding='utf-8') as f:
            f.write(f"{readable_time},{btc_price},{oi_total_usd},{long_vol_usd},{short_vol_usd},{real_ls_ratio_pos},{fund_rate}\n")

        # 頂部儀表板
        st.markdown(f"### 🐳 比特幣主力籌碼監控終端 ｜ 💰 價格: **${btc_price:,.2f}**")

        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown(f"**👥 大戶【帳戶數】** (更新: {readable_time})")
            c1, c2, c3 = st.columns(3)
            c1.metric("做多比例", f"{long_acc * 100:.2f}%")
            c2.metric("做空比例", f"{short_acc * 100:.2f}%")
            c3.metric("多空帳戶比", real_ls_ratio_acc)
            fig_acc = px.pie(values=[long_acc, short_acc], names=["做多", "做空"], hole=0.4,
                             color=["做多", "做空"], color_discrete_map={"做多": "#00e5ff", "做空": "#ff5252"})
            fig_acc.update_layout(height=160, margin=dict(t=0, b=0, l=0, r=0), showlegend=False, template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)") 
            st.plotly_chart(fig_acc, use_container_width=True)

        with col_right:
            st.markdown(f"**💰 大戶【真實資金量】** (單位: USD)")
            c4, c5, c6 = st.columns(3)
            c4.metric("多單資金", f"${long_vol_usd/1e6:,.2f} M")
            c5.metric("空單資金", f"${short_vol_usd/1e6:,.2f} M")
            c6.metric("資金費率", f"{fund_rate * 100:.4f}%")
            fig_pos = px.pie(values=[long_vol_usd, short_vol_usd], names=["做多", "做空"], hole=0.4,
                             color=["做多", "做空"], color_discrete_map={"做多": "#00e5ff", "做空": "#ff5252"})
            fig_pos.update_layout(height=160, margin=dict(t=0, b=0, l=0, r=0), showlegend=False, template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pos, use_container_width=True)
        
        st.divider()
        
        # 繪製圖表
        df_history = pd.read_csv(csv_filename)
        display_df = df_history.tail(60).copy()
        
        fig_line = make_subplots(
            rows=4, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.03,
            row_heights=[0.4, 0.2, 0.2, 0.2], 
            specs=[[{"secondary_y": True}], [{"secondary_y": False}], [{"secondary_y": False}], [{"secondary_y": False}]]
        )
        
        fig_line.add_trace(go.Scatter(x=display_df["Time"], y=display_df["BTC_Price"], name="BTC 價格", line=dict(color="#ffd700", width=2)), row=1, col=1, secondary_y=False)
        fig_line.add_trace(go.Scatter(x=display_df["Time"], y=display_df["OI_Total_USD"], name="總資金(OI)", line=dict(color="#ab47bc", width=2, dash='dot')), row=1, col=1, secondary_y=True)
        fig_line.add_trace(go.Scatter(x=display_df["Time"], y=display_df["Long_Vol_USD"], name="多單資金", line=dict(color="#00e5ff", width=2, shape='spline')), row=2, col=1)
        fig_line.add_trace(go.Scatter(x=display_df["Time"], y=display_df["Short_Vol_USD"], name="空單資金", line=dict(color="#ff5252", width=2, shape='spline')), row=2, col=1)
        fig_line.add_trace(go.Scatter(x=display_df["Time"], y=display_df["LS_Ratio"], name="多空比", line=dict(color="#2962ff", width=2, shape='spline')), row=3, col=1)
        fig_line.add_trace(go.Scatter(x=display_df["Time"], y=display_df["Fund_Rate"], name="資金費率", mode="lines+markers", line=dict(color="#ff9800", dash='dot', width=2)), row=4, col=1)

        fig_line.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=650, margin=dict(t=10, b=10, l=0, r=0), legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5), hovermode="x unified")
        
        # 多空比 Y 軸鎖定為 0~2
        fig_line.update_yaxes(range=[0, 2], row=3, col=1) 
        fig_line.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255, 255, 255, 0.1)')
        fig_line.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255, 255, 255, 0.1)', secondary_y=False)

        st.plotly_chart(fig_line, use_container_width=True)

        # 閱讀模式表格
        st.markdown("**📋 歷史巡檢紀錄表 (最新 20 筆)**")
        st.dataframe(df_history.tail(20).iloc[::-1], use_container_width=True)

        with st.expander("📂 展開完整歷史數據紀錄 (所有採樣點)"):
            st.dataframe(df_history.iloc[::-1], use_container_width=True)

    except Exception as e:
        st.error(f"解析失敗: {e}")

if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()