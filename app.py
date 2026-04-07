import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from supabase import create_client
import time

st.set_page_config(page_title="加密貨幣大戶籌碼監控", layout="wide")

# CSS 樣式
st.markdown("""
    <style>
            .stApp { background-color: #000000; color: #FFFFFF; }
            h1, h2, h3, h4, h5, h6, p, label, div { color: #FFFFFF !important; }
            #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;} .stDeployButton {display: none;}
            .block-container { padding-top: 2rem; padding-bottom: 12rem; }
            
            [data-testid="stMetricValue"] { font-size: 2.5rem; font-weight: bold; color: #FFFFFF !important; }
            [data-testid="stMetricLabel"] { color: rgba(255, 255, 255, 0.8) !important; font-size: 1.2rem !important; }

            .table-wrapper { overflow-x: auto; margin-top: 10px; }
            .scrollable-wrapper { max-height: 400px; overflow-y: auto; overflow-x: auto; margin-top: 10px; border: 1px solid #333; }
            
            .custom-table {
                width: 100%; border-collapse: collapse; background-color: #000000; color: #FFFFFF;
                font-family: sans-serif; font-size: 14px; min-width: 600px;
            }
            .custom-table th { 
                background-color: #1a1a1a; color: #ffd700; text-align: left; 
                padding: 12px; border-bottom: 2px solid #333; white-space: nowrap;
                position: sticky; top: 0; z-index: 1;
            }
            .custom-table td { padding: 10px; border-bottom: 1px solid #222; white-space: nowrap; }
            .custom-table tr:hover { background-color: #111; }
            
            ::-webkit-scrollbar { width: 8px; height: 8px; }
            ::-webkit-scrollbar-track { background: #000000; }
            ::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }
            ::-webkit-scrollbar-thumb:hover { background: #555; }
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
        if 'long_acc_ratio' in df.columns and 'short_acc_ratio' in df.columns:
            df['ls_acc_ratio'] = df.apply(
                lambda row: row['long_acc_ratio'] / row['short_acc_ratio'] 
                if pd.notnull(row.get('short_acc_ratio')) and row['short_acc_ratio'] != 0 else None, 
                axis=1
            )
        else:
            df['ls_acc_ratio'] = None
    return df

def build_table(df_to_render):
    rows = []
    for _, r in df_to_render.iterrows():
        time_str = r.time.strftime('%Y-%m-%d %H:%M:%S')
        acc_ratio_str = f"{r.ls_acc_ratio:.4f}" if pd.notnull(r.get('ls_acc_ratio')) else "N/A"
        rows.append(f"<tr><td>{time_str}</td><td>${r.price:,}</td><td>{r.long_vol_usd/1000000000:.3f}</td><td>{r.short_vol_usd/1000000000:.3f}</td><td>{acc_ratio_str}</td><td>{r.ls_ratio:.4f}</td></tr>")
    
    return f"""
    <table class="custom-table">
        <tr>
            <th>時間</th><th>價格</th><th>多單資金(B)</th><th>空單資金(B)</th><th>帳戶多空比</th><th>持倉多空比</th>
        </tr>
        {"".join(rows)}
    </table>
    """

CHART_FONT = dict(size=13, color="white", family="Arial Black")
TRANSPARENT = 'rgba(0,0,0,0)'
LIGHT_GRID = 'rgba(255, 255, 255, 0.08)'

def render_section(symbol, table_name, price_col, color_hex):
    df = get_data(table_name, price_col)
    
    # 防呆機制：如果資料庫是空的，顯示提示並跳過繪圖
    if df.empty:
        st.warning(f"目前 {symbol} 資料庫尚無數據，請稍後或手動觸發 GitHub 爬蟲。")
        return
        
    latest = df.iloc[-1]
    
    st.markdown(f"### 🐳 {symbol} 大戶籌碼終端 ｜ 💰 <span style='color:{color_hex}'>**${latest.price:,}**</span>", unsafe_allow_html=True)

    col_left, col_right = st.columns(2)
    with col_left:
        l_acc = latest.get('long_acc_ratio', 0.5)
        s_acc = latest.get('short_acc_ratio', 0.5)
        st.markdown("#### 👥 帳戶共識 (人頭數)")
        st.metric("多空帳戶比", f"{l_acc/s_acc:.4f}" if s_acc != 0 else "0")
        
        # 恢復 240 圓餅圖高度與字體
        fig_acc = px.pie(values=[l_acc, s_acc], names=["做多", "做空"], hole=0.6, color=["做多", "做空"], color_discrete_map={"做多": "#00e5ff", "做空": "#ff5252"})
        fig_acc.update_traces(sort=False)
        fig_acc.add_annotation(text="帳戶", showarrow=False, font=dict(size=20, color="white"))
        fig_acc.update_layout(height=240, margin=dict(t=10, b=10, l=10, r=10), showlegend=True, template="plotly_dark", paper_bgcolor=TRANSPARENT, font=CHART_FONT, legend=dict(font=dict(color="#FFFFFF", size=13), orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)) 
        st.plotly_chart(fig_acc, use_container_width=True)

    with col_right:
        st.markdown("#### 💰 資金實力 (倉位量)")
        st.metric("多空持倉比", f"{latest['ls_ratio']:.4f}")
        
        # 恢復 240 圓餅圖高度與字體
        fig_pos = px.pie(values=[latest['long_vol_usd'], latest['short_vol_usd']], names=["做多", "做空"], hole=0.6, color=["做多", "做空"], color_discrete_map={"做多": "#00e5ff", "做空": "#ff5252"})
        fig_pos.update_traces(sort=False)
        fig_pos.add_annotation(text="資金", showarrow=False, font=dict(size=20, color="white"))
        fig_pos.update_layout(height=240, margin=dict(t=10, b=10, l=10, r=10), showlegend=True, template="plotly_dark", paper_bgcolor=TRANSPARENT, font=CHART_FONT, legend=dict(font=dict(color="#FFFFFF", size=13), orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
        st.plotly_chart(fig_pos, use_container_width=True)
    
    st.divider()
    
    fig_line = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.4, 0.3, 0.3])
    
    fig_line.add_trace(go.Scatter(x=df["time"], y=df["price"], name="價格", line=dict(color=color_hex, width=3)), row=1, col=1)
    fig_line.add_trace(go.Scatter(x=df["time"], y=df["long_vol_usd"], name="多單$", line=dict(color="#b2ebf2", width=2)), row=2, col=1)
    fig_line.add_trace(go.Scatter(x=df["time"], y=df["short_vol_usd"], name="空單$", line=dict(color="#ffcdd2", width=2)), row=2, col=1)
    fig_line.add_trace(go.Scatter(x=df["time"], y=df["ls_ratio"], name="持倉多空比", line=dict(color="#FFFFFF", width=2.5)), row=3, col=1)
    fig_line.add_trace(go.Scatter(x=df["time"], y=df["ls_acc_ratio"], name="帳戶多空比", line=dict(color="#00e676", width=2.5)), row=3, col=1)
    
    fig_line.update_layout(template="plotly_dark", paper_bgcolor=TRANSPARENT, plot_bgcolor=TRANSPARENT, height=650, font=CHART_FONT, hovermode="x unified", margin=dict(t=50, b=10, l=10, r=55), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(color="#FFFFFF", size=13)))
    
    # 恢復子圖表的獨立白色框線 (mirror=True)
    fig_line.update_xaxes(showgrid=True, gridwidth=1, gridcolor=LIGHT_GRID, showline=True, linewidth=1.5, linecolor='rgba(255,255,255,0.2)', mirror=True, ticks="outside", tickwidth=1, tickcolor=LIGHT_GRID, ticklen=5, tickangle=-45, tickformat="%m-%d %H:%M")
    fig_line.update_yaxes(showgrid=True, gridwidth=1, gridcolor=LIGHT_GRID, showline=True, linewidth=1.5, linecolor='rgba(255,255,255,0.2)', mirror=True, ticks="outside", tickwidth=1, tickcolor=LIGHT_GRID, ticklen=5)
    fig_line.update_layout(yaxis=dict(tickfont=dict(color=color_hex, size=12)), yaxis2=dict(tickfont=dict(color="#b2ebf2", size=12)), yaxis3=dict(tickfont=dict(color="#FFFFFF", size=12)))
    
    st.plotly_chart(fig_line, use_container_width=True)

    # 恢復最新 20 筆表格
    st.markdown(f"**📋 {symbol} 歷史巡檢紀錄 (最新 20 筆)**")
    df_20 = df.tail(20).iloc[::-1]
    st.markdown(f'<div class="table-wrapper">{build_table(df_20)}</div>', unsafe_allow_html=True)

    with st.expander(f"📂 展開 {symbol} 完整數據紀錄 (1500 筆 / 約一個月)"):
        st.markdown(f'<div class="scrollable-wrapper">{build_table(df.iloc[::-1])}</div>', unsafe_allow_html=True)

# 主程式呼叫
try:
    render_section("BTC", "whale_data", "btc_price", "#ffd700")
    st.markdown("<br><hr style='border: 1px solid #333;'><br>", unsafe_allow_html=True)
    render_section("ETH", "eth_whale_data", "eth_price", "#a0a0ff")
except Exception as e:
    st.error(f"連線失敗: {e}")

time.sleep(300)
st.rerun()
