import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from supabase import create_client
import os
import time

# 基礎設定
st.set_page_config(page_title="比特幣大戶籌碼監控終端", layout="wide")

# 1. 🚀 極致黑化 CSS：強行覆蓋所有 Streamlit 預設背景
st.markdown("""
    <style>
            /* 1. 全頁面背景黑化 */
            .stApp {
                background-color: #000000;
                color: #FFFFFF;
            }
            
            /* 2. 標題與所有文字強制變白 */
            h1, h2, h3, h4, h5, h6, p, label, div {
                color: #FFFFFF !important;
            }
            
            /* 3. 隱藏預設 UI 元素 */
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            .stDeployButton {display: none;}
            
            /* 4. 排版設定與底部間距防止遮擋 */
            .block-container { 
                padding-top: 2rem; 
                padding-bottom: 12rem; 
            }
            
            /* 5. Metrics 專業樣式設定 */
            [data-testid="stMetricLabel"] {
                color: rgba(255, 255, 255, 0.7) !important;
                font-size: 1.1rem !important;
            }
            [data-testid="stMetricValue"] { 
                font-size: 2.2rem; 
                font-weight: bold; 
                color: #FFFFFF !important;
            }
            
            /* 6. 表格與 Expander 黑化 */
            .stDataFrame, .stExpander {
                border: 1px solid rgba(255,255,255,0.1);
                background-color: #0e1117;
            }
            
            /* 7. 分割線變淡 */
            hr { border: 0; border-top: 1px solid rgba(255,255,255,0.1); }
            
    </style>
    """, unsafe_allow_html=True)

# 資料庫連線
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_data_from_db():
    response = supabase.table("whale_data").select("*").order("time", desc=True).limit(200).execute()
    df = pd.DataFrame(response.data)
    if not df.empty:
        df = df.sort_values(by="time", ascending=True)
        # 金額轉整數
        for col in ["btc_price", "oi_total_usd", "long_vol_usd", "short_vol_usd"]:
            if col in df.columns:
                df[col] = df[col].astype(int)
    return df

# 圖表背景設置常數
TRANSPARENT = 'rgba(0,0,0,0)'
LIGHT_GRID = 'rgba(255,255,255,0.08)'

# 主程式邏輯
try:
    df_history = get_data_from_db()
    
    if not df_history.empty:
        latest = df_history.iloc[-1]
        
        # 標題
        st.markdown(f"### 🐳 比特幣主力籌碼監控終端 ｜ 💰 價格: <span style='color:#ffd700'>**${latest['btc_price']:,}**</span>", unsafe_allow_html=True)

        col_left, col_right = st.columns(2)
        
        with col_left:
            # 取得帳戶比例
            l_acc = latest.get('long_acc_ratio', 0.5)
            s_acc = latest.get('short_acc_ratio', 0.5)
            st.markdown(f"**👥 大戶【帳戶數】** (更新: {latest['time']})")
            c1, c2, c3 = st.columns(3)
            c1.metric("做多比例", f"{l_acc * 100:.2f}%")
            c2.metric("做空比例", f"{s_acc * 100:.2f}%")
            c3.metric("多空帳戶比", round(l_acc/s_acc, 4) if s_acc != 0 else 0)
            
            fig_acc = px.pie(values=[l_acc, s_acc], names=["做多", "做空"], hole=0.5,
                             color=["做多", "做空"], color_discrete_map={"做多": "#00e5ff", "做空": "#ff5252"})
            # 2. 🚀 圖表背景黑化 (透明，讓 CSS 背景秀出來)
            fig_acc.update_layout(height=180, margin=dict(t=0, b=0, l=0, r=0), 
                                 showlegend=False, template="plotly_dark", 
                                 paper_bgcolor=TRANSPARENT, plot_bgcolor=TRANSPARENT) 
            st.plotly_chart(fig_acc, use_container_width=True)

        with col_right:
            st.markdown(f"**💰 大戶【真實資金量】** (單位: USD)")
            c4, c5, c6 = st.columns(3)
            c4.metric("多單資金", f"${latest['long_vol_usd']/1e6:,.0f} M")
            c5.metric("空單資金", f"${latest['short_vol_usd']/1e6:,.0f} M")
            # 依你要求，保留多空持倉比
            c6.metric("多空持倉比", round(latest['ls_ratio'], 4))
            
            fig_pos = px.pie(values=[latest['long_vol_usd'], latest['short_vol_usd']], names=["做多", "做空"], hole=0.5,
                             color=["做多", "做空"], color_discrete_map={"做多": "#00e5ff", "做空": "#ff5252"})
            # 2. 🚀 圖表背景黑化 (透明)
            fig_pos.update_layout(height=180, margin=dict(t=0, b=0, l=0, r=0), 
                                  showlegend=False, template="plotly_dark", 
                                  paper_bgcolor=TRANSPARENT, plot_bgcolor=TRANSPARENT)
            st.plotly_chart(fig_pos, use_container_width=True)
        
        st.divider()
        
        # 3. 🚀 趨勢圖表黑化設定
        fig_line = make_subplots(
            rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03,
            row_heights=[0.4, 0.2, 0.2, 0.2], 
            specs=[[{"secondary_y": True}], [{"secondary_y": False}], [{"secondary_y": False}], [{"secondary_y": False}]]
        )
        fig_line.add_trace(go.Scatter(x=df_history["time"], y=df_history["btc_price"], name="價格", line=dict(color="#ffd700", width=2.5)), row=1, col=1)
        fig_line.add_trace(go.Scatter(x=df_history["time"], y=df_history["oi_total_usd"], name="總持倉(OI)", line=dict(color="#ab47bc", width=2, dash='dot')), row=1, col=1, secondary_y=True)
        fig_line.add_trace(go.Scatter(x=df_history["time"], y=df_history["long_vol_usd"], name="多單資金", line=dict(color="#00e5ff", width=2)), row=2, col=1)
        fig_line.add_trace(go.Scatter(x=df_history["time"], y=df_history["short_vol_usd"], name="空單資金", line=dict(color="#ff5252", width=2)), row=2, col=1)
        fig_line.add_trace(go.Scatter(x=df_history["time"], y=df_history["ls_ratio"], name="多空比", line=dict(color="#FFFFFF", width=2)), row=3, col=1)
        fig_line.add_trace(go.Scatter(x=df_history["time"], y=df_history["fund_rate"], name="資金費率", mode="lines+markers", line=dict(color="#ff9800", dash='dot')), row=4, col=1)
        
        # 設置統一的 dark layout
        fig_line.update_layout(template="plotly_dark", paper_bgcolor=TRANSPARENT, plot_bgcolor=TRANSPARENT, height=650, margin=dict(t=10, b=10, l=0, r=0), hovermode="x unified", font=dict(color="white"))
        
        # 設置淺色網格
        fig_line.update_xaxes(showgrid=True, gridwidth=1, gridcolor=LIGHT_GRID)
        fig_line.update_yaxes(showgrid=True, gridwidth=1, gridcolor=LIGHT_GRID)
        
        st.plotly_chart(fig_line, use_container_width=True)

        # 表格顯示
        st.markdown("**📋 歷史巡檢紀錄表 (最新 20 筆)**")
        st.dataframe(df_history.tail(20).iloc[::-1], use_container_width=True)

        with st.expander("📂 展開完整歷史數據紀錄 (200 筆)"):
            st.dataframe(df_history.iloc[::-1], use_container_width=True)

except Exception as error_msg:
    st.error(f"資料讀取失敗: {error_msg}")

time.sleep(300)
st.rerun()
