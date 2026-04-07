import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from supabase import create_client
import time

st.set_page_config(page_title="加密貨幣大戶籌碼監控", layout="wide")

# CSS 樣式 (維持黑魂版)
st.markdown("""
    <style>
            .stApp { background-color: #000000; color: #FFFFFF; }
            h1, h2, h3, h4, h5, h6, p, label, div { color: #FFFFFF !important; }
            #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;} .stDeployButton {display: none;}
            .block-container { padding-top: 2rem; padding-bottom: 5rem; }
            [data-testid="stMetricValue"] { font-size: 2.2rem; font-weight: bold; color: #FFFFFF !important; }
            .table-wrapper { overflow-x: auto; margin-top: 10px; }
            .scrollable-wrapper { max-height: 400px; overflow-y: auto; overflow-x: auto; border: 1px solid #333; }
            .custom-table { width: 100%; border-collapse: collapse; background-color: #000000; font-size: 14px; }
            .custom-table th { background-color: #1a1a1a; color: #ffd700; text-align: left; padding: 12px; position: sticky; top: 0; z-index: 1; }
            .custom-table td { padding: 10px; border-bottom: 1px solid #222; white-space: nowrap; }
    </style>
    """, unsafe_allow_html=True)

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_data(table_name, price_col):
    response = supabase.table(table_name).select("*").order("time", desc=True).limit(1500).execute()
    df = pd.DataFrame(response.data)
    if not df.empty:
        df = df.sort_values(by="time", ascending=True)
        df['time'] = pd.to_datetime(df['time']) + pd.Timedelta(hours=8)
        df['price'] = df[price_col].astype(int)
        if 'long_acc_ratio' in df.columns:
            df['ls_acc_ratio'] = df['long_acc_ratio'] / df['short_acc_ratio']
    return df

def build_table(df_render):
    rows = "".join([f"<tr><td>{r.time.strftime('%Y-%m-%d %H:%M')}</td><td>${r.price:,}</td><td>{r.long_vol_usd/1e9:.3f}</td><td>{r.short_vol_usd/1e9:.3f}</td><td>{r.ls_acc_ratio:.4f}</td><td>{r.ls_ratio:.4f}</td></tr>" for _, r in df_render.iterrows()])
    return f'<table class="custom-table"><tr><th>時間</th><th>價格</th><th>多單(B)</th><th>空單(B)</th><th>帳戶比</th><th>持倉比</th></tr>{rows}</table>'

def render_section(symbol, table_name, price_col, color_hex):
    df = get_data(table_name, price_col)
    if df.empty: return
    latest = df.iloc[-1]
    
    st.markdown(f"## 🐳 {symbol} 監控 ｜ <span style='color:{color_hex}'>**${latest.price:,}**</span>", unsafe_allow_html=True)
    c_l, c_r = st.columns(2)
    
    with c_l:
        st.metric("帳戶多空比", f"{latest.ls_acc_ratio:.4f}")
        fig = px.pie(values=[latest.long_acc_ratio, latest.short_acc_ratio], names=["做多", "做空"], hole=0.6, color_discrete_map={"做多": "#00e5ff", "做空": "#ff5252"})
        fig.update_layout(height=200, showlegend=True, paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"))
        st.plotly_chart(fig, use_container_width=True)

    with c_r:
        st.metric("持倉多空比", f"{latest.ls_ratio:.4f}")
        fig = px.pie(values=[latest.long_vol_usd, latest.short_vol_usd], names=["做多", "做空"], hole=0.6, color_discrete_map={"做多": "#00e5ff", "做空": "#ff5252"})
        fig.update_layout(height=200, showlegend=True, paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"))
        st.plotly_chart(fig, use_container_width=True)

    fig_line = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.4, 0.3, 0.3])
    fig_line.add_trace(go.Scatter(x=df["time"], y=df["price"], name="價格", line=dict(color=color_hex, width=3)), row=1, col=1)
    fig_line.add_trace(go.Scatter(x=df["time"], y=df["long_vol_usd"], name="多單$", line=dict(color="#b2ebf2", width=2)), row=2, col=1)
    fig_line.add_trace(go.Scatter(x=df["time"], y=df["short_vol_usd"], name="空單$", line=dict(color="#ffcdd2", width=2)), row=2, col=1)
    fig_line.add_trace(go.Scatter(x=df["time"], y=df["ls_ratio"], name="持倉比", line=dict(color="#FFFFFF", width=2)), row=3, col=1)
    fig_line.add_trace(go.Scatter(x=df["time"], y=df["ls_acc_ratio"], name="帳戶比", line=dict(color="#00e676", width=2)), row=3, col=1)
    fig_line.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=600, margin=dict(t=30, b=10, l=10, r=50), legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center"))
    fig_line.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.08)", tickformat="%m-%d %H:%M")
    fig_line.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.08)")
    st.plotly_chart(fig_line, use_container_width=True)

    with st.expander(f"📂 展開 {symbol} 完整數據紀錄 (1500 筆)"):
        st.markdown(f'<div class="scrollable-wrapper">{build_table(df.iloc[::-1])}</div>', unsafe_allow_html=True)

# 主程式呼叫
try:
    render_section("BTC", "whale_data", "btc_price", "#ffd700")
    st.markdown("<br><hr><br>", unsafe_allow_html=True) # 分隔線
    render_section("ETH", "eth_whale_data", "eth_price", "#a0a0ff") # ETH 用淡紫色區分
except Exception as e:
    st.error(f"連線失敗: {e}")

time.sleep(300)
st.rerun()
