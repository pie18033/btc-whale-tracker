import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from supabase import create_client
import os
import time

st.set_page_config(page_title="Bitget比特幣大戶籌碼監控", layout="wide")

# CSS 樣式 (加入表格的 RWD 左右滑動設定)
st.markdown("""
    <style>
            .stApp { background-color: #000000; color: #FFFFFF; }
            h1, h2, h3, h4, h5, h6, p, label, div { color: #FFFFFF !important; }
            #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;} .stDeployButton {display: none;}
            .block-container { padding-top: 2rem; padding-bottom: 12rem; }
            
            [data-testid="stMetricValue"] { font-size: 2.5rem; font-weight: bold; color: #FFFFFF !important; }
            [data-testid="stMetricLabel"] { color: rgba(255, 255, 255, 0.8) !important; font-size: 1.2rem !important; }

            /* 自定義黑化表格與響應式滑動 */
            .table-wrapper { overflow-x: auto; margin-top: 10px; }
            .custom-table {
                width: 100%; border-collapse: collapse; background-color: #000000; color: #FFFFFF;
                font-family: sans-serif; font-size: 14px; min-width: 600px;
            }
            .custom-table th { background-color: #1a1a1a; color: #ffd700; text-align: left; padding: 12px; border-bottom: 2px solid #333; white-space: nowrap; }
            .custom-table td { padding: 10px; border-bottom: 1px solid #222; white-space: nowrap; }
            .custom-table tr:hover { background-color: #111; }
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
        # 轉換 time 欄位為 datetime 格式，方便後續格式化
        df['time'] = pd.to_datetime(df['time'])
        for col in ["btc_price", "oi_total_usd", "long_vol_usd", "short_vol_usd"]:
            if col in df.columns:
                df[col] = df[col].astype(int)
        
        if 'long_acc_ratio' in df.columns and 'short_acc_ratio' in df.columns:
            df['ls_acc_ratio'] = df.apply(
                lambda row: row['long_acc_ratio'] / row['short_acc_ratio'] 
                if pd.notnull(row.get('short_acc_ratio')) and row['short_acc_ratio'] != 0 else None, 
                axis=1
            )
        else:
            df['ls_acc_ratio'] = None
            
    return df

CHART_FONT = dict(size=13, color="white", family="Arial Black")
TRANSPARENT = 'rgba(0,0,0,0)'
LIGHT_GRID = 'rgba(255, 255, 255, 0.08)'

try:
    df_history = get_data_from_db()
    if not df_history.empty:
        latest = df_history.iloc[-1]
        
        st.markdown(f"### 🐳 Bitget比特幣大戶籌碼終端 ｜ 💰 <span style='color:#ffd700'>**${latest['btc_price']:,}**</span>", unsafe_allow_html=True)

        col_left, col_right = st.columns(2)
        with col_left:
            l_acc = latest.get('long_acc_ratio', 0.5)
            s_acc = latest.get('short_acc_ratio', 0.5)
            st.markdown("#### 👥 帳戶共識 (人頭數)")
            st.metric("多空帳戶比", f"{l_acc/s_acc:.4f}" if s_acc != 0 else "0")
            
            fig_acc = px.pie(values=[l_acc, s_acc], names=["做多", "做空"], hole=0.6,
                             color=["做多", "做空"], color_discrete_map={"做多": "#00e5ff", "做空": "#ff5252"})
            fig_acc.update_traces(sort=False)
            fig_acc.add_annotation(text="帳戶", showarrow=False, font=dict(size=20, color="white"))
            
            fig_acc.update_layout(height=240, margin=dict(t=10, b=10, l=10, r=10), 
                                 showlegend=True, template="plotly_dark", 
                                 paper_bgcolor=TRANSPARENT, font=CHART_FONT,
                                 legend=dict(font=dict(color="#FFFFFF", size=13), orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)) 
            st.plotly_chart(fig_acc, use_container_width=True)

        with col_right:
            st.markdown("#### 💰 資金實力 (倉位量)")
            st.metric("多空持倉比", f"{latest['ls_ratio']:.4f}")
            
            fig_pos = px.pie(values=[latest['long_vol_usd'], latest['short_vol_usd']], names=["做多", "做空"], hole=0.6,
                             color=["做多", "做空"], color_discrete_map={"做多": "#00e5ff", "做空": "#ff5252"})
            fig_pos.update_traces(sort=False)
            fig_pos.add_annotation(text="資金", showarrow=False, font=dict(size=20, color="white"))
            
            fig_pos.update_layout(height=240, margin=dict(t=10, b=10, l=10, r=10), 
                                  showlegend=True, template="plotly_dark", 
                                  paper_bgcolor=TRANSPARENT, font=CHART_FONT,
                                  legend=dict(font=dict(color="#FFFFFF", size=13), orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
            st.plotly_chart(fig_pos, use_container_width=True)
        
        st.divider()
        
        fig_line = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.4, 0.2, 0.2, 0.2], specs=[[{"secondary_y": True}], [{"secondary_y": False}], [{"secondary_y": False}], [{"secondary_y": False}]])
        
        fig_line.add_trace(go.Scatter(x=df_history["time"], y=df_history["btc_price"], name="價格", line=dict(color="#ffd700", width=3)), row=1, col=1)
        fig_line.add_trace(go.Scatter(x=df_history["time"], y=df_history["oi_total_usd"], name="OI總額", line=dict(color="#b39ddb", width=2, dash='dot')), row=1, col=1, secondary_y=True)
        fig_line.add_trace(go.Scatter(x=df_history["time"], y=df_history["long_vol_usd"], name="多單$", line=dict(color="#b2ebf2", width=2)), row=2, col=1)
        fig_line.add_trace(go.Scatter(x=df_history["time"], y=df_history["short_vol_usd"], name="空單$", line=dict(color="#ffcdd2", width=2)), row=2, col=1)
        fig_line.add_trace(go.Scatter(x=df_history["time"], y=df_history["ls_ratio"], name="持倉多空比", line=dict(color="#FFFFFF", width=2.5)), row=3, col=1)
        fig_line.add_trace(go.Scatter(x=df_history["time"], y=df_history["ls_acc_ratio"], name="帳戶多空比", line=dict(color="#00e676", width=2.5)), row=3, col=1)
        fig_line.add_trace(go.Scatter(x=df_history["time"], y=df_history["fund_rate"], name="費率", mode="lines+markers", line=dict(color="#ffe0b2")), row=4, col=1)
        
        # 🚀 排版優化：圖例置頂水平排列、增加右側邊距(r=55)防遮擋
        fig_line.update_layout(
            template="plotly_dark", paper_bgcolor=TRANSPARENT, plot_bgcolor=TRANSPARENT, height=750, font=CHART_FONT, hovermode="x unified",
            margin=dict(t=50, b=10, l=10, r=55),
            legend=dict(
                orientation="h", 
                yanchor="bottom", 
                y=1.02, 
                xanchor="center", 
                x=0.5,
                font=dict(color="#FFFFFF", size=13)
            )
        )
        
        # 🚀 X 軸時間優化：45度傾斜、格式化為「月-日 時:分」
        fig_line.update_xaxes(
            showgrid=True, gridwidth=1, gridcolor=LIGHT_GRID, showline=True, linewidth=1.5, linecolor='rgba(255,255,255,0.2)', mirror=True, ticks="outside", tickwidth=1, tickcolor=LIGHT_GRID, ticklen=5,
            tickangle=-45, tickformat="%m-%d %H:%M"
        )
        
        fig_line.update_yaxes(showgrid=True, gridwidth=1, gridcolor=LIGHT_GRID, showline=True, linewidth=1.5, linecolor='rgba(255,255,255,0.2)', mirror=True, ticks="outside", tickwidth=1, tickcolor=LIGHT_GRID, ticklen=5)
        
        fig_line.update_layout(
            yaxis=dict(tickfont=dict(color="#ffd700", size=12)),   
            yaxis2=dict(tickfont=dict(color="#b39ddb", size=12)),  
            yaxis3=dict(tickfont=dict(color="#b2ebf2", size=12)),  
            yaxis4=dict(tickfont=dict(color="#FFFFFF", size=12)),  
            yaxis5=dict(tickfont=dict(color="#ffe0b2", size=12))   
        )
        
        st.plotly_chart(fig_line, use_container_width=True)

        # 🚀 表格 RWD 包裝器
        st.markdown("**📋 歷史巡檢紀錄 (最新 20 筆)**")
        df_20 = df_history.tail(20).iloc[::-1]
        
        html_table = f"""
        <div class="table-wrapper">
            <table class="custom-table">
                <tr>
                    <th>時間</th><th>價格</th><th>OI總額(M)</th><th>多單資金(M)</th><th>空單資金(M)</th><th>持倉多空比</th><th>費率</th>
                </tr>
                {"".join([f"<tr><td>{r.time.strftime('%Y-%m-%d %H:%M:%S')}</td><td>${r.btc_price:,}</td><td>{r.oi_total_usd/1000000:.1f}M</td><td>{r.long_vol_usd/1000000:.1f}M</td><td>{r.short_vol_usd/1000000:.1f}M</td><td>{r.ls_ratio:.4f}</td><td>{r.fund_rate*100:.4f}%</td></tr>" for i, r in df_20.iterrows()])}
            </table>
        </div>
        """
        st.markdown(html_table, unsafe_allow_html=True)

        with st.expander("📂 展開原始數據 (200 筆)"):
            st.dataframe(df_history.iloc[::-1], use_container_width=True)

except Exception as e:
    st.error(f"連線失敗: {e}")

time.sleep(300)
st.rerun()
