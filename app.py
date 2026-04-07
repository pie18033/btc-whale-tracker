import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client, Client
import os
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# --- 1. 頁面配置 (必須是 Streamlit 的第一個指令) ---
st.set_page_config(page_title="BTC/ETH 大戶籌碼終端機", layout="wide", initial_sidebar_state="collapsed")

# --- 2. 自動重整心跳 (每 5 分鐘) ---
# 放在最前面，確保網頁一啟動就掛上計時器
st_autorefresh(interval=300000, key="data_refresher")

# --- 3. 初始化 Supabase 連線 ---
@st.cache_resource
def init_connection():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)

supabase = init_connection()

# --- 4. 數據抓取邏輯 ---
def get_data(table_name):
    res = supabase.table(table_name).select("*").order("time", desc=True).limit(200).execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time')
    return df

# --- 5. 表格美化函式 ---
def build_table(df):
    if df.empty: return ""
    # 這裡放你原本的 HTML 表格產生邏輯
    # ... (節省篇幅，建議保留你原本的 build_table 內容) ...
    return df.to_html(classes='table-wrapper') 

# --- 6. 核心繪圖與顯示函式 ---
def render_section(symbol, table_name, price_col, color_hex):
    st.subheader(f"📊 {symbol} 籌碼背離監控")
    df = get_data(table_name)
    
    if df.empty:
        st.warning(f"暫無 {symbol} 數據")
        return

    # 繪製 Plotly 圖表
    fig = go.Figure()
    # 價格線
    fig.add_trace(go.Scatter(x=df['time'], y=df[price_col], name="Price", line=dict(color=color_hex, width=2)))
    # LS Ratio (副座標)
    fig.add_trace(go.Scatter(x=df['time'], y=df['ls_ratio'], name="L/S Ratio", yaxis="y2", line=dict(color="#00ff88", width=1.5, dash='dot')))
    
    fig.update_layout(
        template="plotly_dark",
        height=400,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis=dict(title="Price (USDT)", side="left"),
        yaxis2=dict(title="L/S Ratio", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 顯示最近 20 筆紀錄
    with st.expander(f"📂 展開 {symbol} 詳細歷史紀錄"):
        st.dataframe(df.tail(20).iloc[::-1], use_container_width=True)

# --- 7. 主程式進入點 ---
def main():
    st.title("🐋 Crypto Whale Tracker")
    st.markdown("---")
    
    try:
        # 執行 BTC 區塊
        render_section("BTC", "whale_data", "btc_price", "#ffd700")
        
        st.markdown("<br><hr style='border: 1px solid #333;'><br>", unsafe_allow_html=True)
        
        # 執行 ETH 區塊
        render_section("ETH", "eth_whale_data", "eth_price", "#a0a8ff")
        
    except Exception as e:
        st.error(f"⚠️ 數據讀取失敗：{e}")

if __name__ == "__main__":
    main()
