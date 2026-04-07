import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from supabase import create_client
import os
import time

st.set_page_config(page_title="比特幣大戶籌碼面板", layout="wide")

# 隱藏 UI 元素
st.markdown("""
    <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            .stDeployButton {display: none;}
            .block-container { padding-top: 2rem; padding-bottom: 0rem; }
            [data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# ----- 資料庫連線設定 -----
# 注意：這裡同樣使用 Secrets 讀取，不要寫死網址
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_data_from_db():
    # 從 whale_data 資料表抓取最近 200 筆資料
    response = supabase.table("whale_data").select("*").order("time", desc=True).limit(200).execute()
    df = pd.DataFrame(response.data)
    # 將時間轉回排序，讓圖表從左到右
    df = df.sort_values(by="time", ascending=True)
    return df

try:
    df_history = get_data_from_db()
    
    if not df_history.empty:
        latest = df_history.iloc[-1]
        
        # ----- 畫面渲染 -----
        st.markdown(f"### 🐳 比特幣主力籌碼監控終端 ｜ 💰 價格: **${latest['btc_price']:,.2f}**")

        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown(f"**👥 大戶動向** (資料庫最後更新: {latest['time']})")
            c1, c2, c3 = st.columns(3)
            # 這裡我們用資料庫中的 ls_ratio 反推一下比例顯示
            c1.metric("多單資金", f"${latest['long_vol_usd']/1e6:,.2f} M")
            c2.metric("空單資金", f"${latest['short_vol_usd']/1e6:,.2f} M")
            c3.metric("多空資金比", round(latest['ls_ratio'], 4))
            
            fig_pos = px.pie(values=[latest['long_vol_usd'], latest['short_vol_usd']], names=["做多", "做空"], hole=0.4,
                             color=["做多", "做空"], color_discrete_map={"做多": "#00e5ff", "做空": "#ff5252"})
            fig_pos.update_layout(height=160, margin=dict(t=0, b=0, l=0, r=0), showlegend=False, template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)") 
            st.plotly_chart(fig_pos, use_container_width=True)

        with col_right:
            st.markdown(f"**📈 市場概況**")
            c4, c5, c6 = st.columns(3)
            c4.metric("總未平倉量", f"${latest['oi_total_usd']/1e6:,.2f} M")
            c5.metric("資金費率", f"{latest['fund_rate'] * 100:.4f}%")
            
            # 輔助餅圖
            fig_oi = px.pie(values=[latest['oi_total_usd'], 1], names=["總持倉", ""], hole=0.8)
            fig_oi.update_layout(height=160, margin=dict(t=0, b=0, l=0, r=0), showlegend=False, template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_oi, use_container_width=True)
        
        st.divider()
        
        # 繪製趨勢圖表 (與之前邏輯相同)
        fig_line = make_subplots(
            rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03,
            row_heights=[0.4, 0.2, 0.2, 0.2], 
            specs=[[{"secondary_y": True}], [{"secondary_y": False}], [{"secondary_y": False}], [{"secondary_y": False}]]
        )
        
        fig_line.add_trace(go.Scatter(x=df_history["time"], y=df_history["btc_price"], name="價格", line=dict(color="#ffd700", width=2)), row=1, col=1)
        fig_line.add_trace(go.Scatter(x=df_history["time"], y=df_history["oi_total_usd"], name="總資金(OI)", line=dict(color="#ab47bc", width=2, dash='dot')), row=1, col=1, secondary_y=True)
        fig_line.add_trace(go.Scatter(x=df_history["time"], y=df_history["long_vol_usd"], name="多單資金", line=dict(color="#00e5ff", width=2)), row=2, col=1)
        fig_line.add_trace(go.Scatter(x=df_history["time"], y=df_history["short_vol_usd"], name="空單資金", line=dict(color="#ff5252", width=2)), row=2, col=1)
        fig_line.add_trace(go.Scatter(x=df_history["time"], y=df_history["ls_ratio"], name="多空比", line=dict(color="#2962ff", width=2)), row=3, col=1)
        fig_line.add_trace(go.Scatter(x=df_history["time"], y=df_history["fund_rate"], name="資金費率", mode="lines+markers", line=dict(color="#ff9800", dash='dot')), row=4, col=1)

        fig_line.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=650, margin=dict(t=10, b=10, l=0, r=0), hovermode="x unified")
        st.plotly_chart(fig_line, use_container_width=True)

        with st.expander("📂 查看完整雲端歷史數據"):
            st.dataframe(df_history.iloc[::-1], use_container_width=True)

except Exception as e:
    st.error(f"資料讀取失敗: {e}")

# 每 5 分鐘檢查一次網頁是否需要刷新 (此刷新僅影響網頁看得到的資料，不影響資料庫抓取)
time.sleep(300)
st.rerun()
