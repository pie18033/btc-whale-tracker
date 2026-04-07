import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from supabase import create_client
import os
import time

# 基礎設定
st.set_page_config(page_title="比特幣大戶籌碼面板", layout="wide")

# CSS 優化：隱藏 UI、增加底部間距
st.markdown("""
    <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            .stDeployButton {display: none;}
            .block-container { 
                padding-top: 2rem; 
                padding-bottom: 12rem; 
            }
            [data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 資料庫連線
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_data_from_db():
    # 抓取最近 200 筆資料
    response = supabase.table("whale_data").select("*").order("time", desc=True).limit(200).execute()
    df = pd.DataFrame(response.data)
    if not df.empty:
        df = df.sort_values(by="time", ascending=True)
        # 金額轉整數，美化顯示
        for col in ["btc_price", "oi_total_usd", "long_vol_usd", "short_vol_usd"]:
            if col in df.columns:
                df[col] = df[col].astype(int)
    return df

# 主程式邏輯
try:
    df_history = get_data_from_db()
    
    if not df_history.empty:
        latest = df_history.iloc[-1]
        
        st.markdown(f"### 🐳 比特幣主力籌碼監控終端 ｜ 💰 價格: **${latest['btc_price']:,}**")

        col_left, col_right = st.columns(2)
        
        with col_left:
            # 取得帳戶比例 (若舊資料沒有則預設 0.5)
            l_acc = latest.get('long_acc_ratio', 0.5)
            s_acc = latest.get('short_acc_ratio', 0.5)
            st.markdown(f"**👥 大戶【帳戶數】** (更新: {latest['time']})")
            c1, c2, c3 = st.columns(3)
            c1.metric("做多比例", f"{l_acc * 100:.2f}%")
            c2.metric("做空比例", f"{s_acc * 100:.2f}%")
            c3.metric("多空帳戶比", round(l_acc/s_acc, 4) if s_acc != 0 else 0)
            
            fig_acc = px.pie(values=[l_acc, s_acc], names=["做多", "做空"], hole=0.4,
                             color=["做多", "做空"], color_discrete_map={"做多": "#00e5ff", "做空": "#ff5252"})
            fig_acc.update_layout(height=170, margin=dict(t=0, b=0, l=0, r=0), showlegend=False, template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)") 
            st.plotly_chart(fig_acc, use_container_width=True)

        with col_right:
            st.markdown(f"**💰 大戶【真實資金量】** (單位: USD)")
            c4, c5, c6 = st.columns(3)
            c4.metric("多單資金", f"${latest['long_vol_usd']/1e6:,.0f} M")
            c5.metric("空單資金", f"${latest['short_vol_usd']/1e6:,.0f} M")
            # 修改這裡：把原本的「資金費率」改為「多空持倉比」
            c6.metric("多空持倉比", round(latest['ls_ratio'], 4))
            
            # 下方的圓餅圖保持原樣
            fig_pos = px.pie(values=[latest['long_vol_usd'], latest['short_vol_usd']], names=["做多", "做空"], hole=0.4,
                             color=["做多", "做空"], color_discrete_map={"做多": "#00e5ff", "做空": "#ff5252"})
            fig_pos.update_layout(height=170, margin=dict(t=0, b=0, l=0, r=0), showlegend=False, template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pos, use_container_width=True)
        
        st.divider()
        
        # 趨勢圖表
        fig_line = make_subplots(
            rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03,
            row_heights=[0.4, 0.2, 0.2, 0.2], 
            specs=[[{"secondary_y": True}], [{"secondary_y": False}], [{"secondary_y": False}], [{"secondary_y": False}]]
        )
        fig_line.add_trace(go.Scatter(x=df_history["time"], y=df_history["btc_price"], name="價格", line=dict(color="#ffd700", width=2)), row=1, col=1)
        fig_line.add_trace(go.Scatter(x=df_history["time"], y=df_history["oi_total_usd"], name="總持倉(OI)", line=dict(color="#ab47bc", width=2, dash='dot')), row=1, col=1, secondary_y=True)
        fig_line.add_trace(go.Scatter(x=df_history["time"], y=df_history["long_vol_usd"], name="多單資金", line=dict(color="#00e5ff", width=2)), row=2, col=1)
        fig_line.add_trace(go.Scatter(x=df_history["time"], y=df_history["short_vol_usd"], name="空單資金", line=dict(color="#ff5252", width=2)), row=2, col=1)
        fig_line.add_trace(go.Scatter(x=df_history["time"], y=df_history["ls_ratio"], name="多空比", line=dict(color="#2962ff", width=2)), row=3, col=1)
        fig_line.add_trace(go.Scatter(x=df_history["time"], y=df_history["fund_rate"], name="資金費率", mode="lines+markers", line=dict(color="#ff9800", dash='dot')), row=4, col=1)
        fig_line.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=600, margin=dict(t=10, b=10, l=0, r=0), hovermode="x unified")
        st.plotly_chart(fig_line, use_container_width=True)

        # 表格顯示：預設 20 筆
        st.markdown("**📋 歷史巡檢紀錄表 (最新 20 筆)**")
        st.dataframe(df_history.tail(20).iloc[::-1], use_container_width=True)

        with st.expander("📂 展開完整歷史數據紀錄 (200 筆)"):
            st.dataframe(df_history.iloc[::-1], use_container_width=True)

except Exception as error_msg:
    st.error(f"資料讀取失敗: {error_msg}")

time.sleep(300)
st.rerun()
