import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from supabase import create_client
import time
from streamlit_autorefresh import st_autorefresh
st.set_page_config(page_title="加密貨幣大戶籌碼監控", layout="wide")

# CSS 樣式
st.markdown("""
    <style>
            .stApp { background-color: #000000; color: #FFFFFF; }
            h1, h2, h3, h4, h5, h6, p, label, div { color: #FFFFFF !important; }
            #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;} .stDeployButton {display: none;}
            .block-container { padding-top: 2rem; padding-bottom: 5rem; }
            
            [data-testid="stMetricValue"] { font-size: 2.2rem; font-weight: bold; color: #FFFFFF !important; }
            
            .table-wrapper { overflow-x: auto; margin-top: 10px; }
            .scrollable-wrapper { max-height: 400px; overflow-y: auto; overflow-x: auto; border: 1px solid #333; }
            
            .custom-table { width: 100%; border-collapse: collapse; background-color: #000000; font-size: 14px; text-align: center; }
            .custom-table th { background-color: #1a1a1a; color: #ffd700; text-align: center; padding: 10px 6px; position: sticky; top: 0; z-index: 1; white-space: nowrap; border-bottom: 2px solid #333; }
            .custom-table td { padding: 10px 6px; border-bottom: 1px solid #222; white-space: nowrap; }
            
            ::-webkit-scrollbar { width: 6px; height: 6px; }
            ::-webkit-scrollbar-track { background: #000000; }
            ::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
            ::-webkit-scrollbar-thumb:hover { background: #555; }

            @media (max-width: 600px) {
                .custom-table { font-size: 11px; } 
                .custom-table th, .custom-table td { padding: 8px 3px; } 
                [data-testid="stMetricValue"] { font-size: 1.8rem !important; } 
            }
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

def build_table(df_render):
    rows = []
    for _, r in df_render.iterrows():
        time_str = r.time.strftime('%m-%d %H:%M')
        acc_ratio_str = f"{r.ls_acc_ratio:.4f}" if pd.notnull(r.get('ls_acc_ratio')) else "N/A"
        rows.append(f"<tr><td>{time_str}</td><td>${r.price:,}</td><td>{r.long_vol_usd/1e9:.3f}</td><td>{r.short_vol_usd/1e9:.3f}</td><td>{acc_ratio_str}</td><td>{r.ls_ratio:.4f}</td></tr>")
    
    return f"""
    <table class="custom-table">
        <tr>
            <th>時間</th><th>價格</th><th>多單(B)</th><th>空單(B)</th><th>帳戶比</th><th>持倉比</th>
        </tr>
        {"".join(rows)}
    </table>
    """

def render_section(symbol, table_name, price_col, color_hex):
    df = get_data(table_name, price_col)
    
    if df.empty:
        st.warning(f"目前 {symbol} 資料庫尚無數據，請稍後或手動觸發 GitHub 爬蟲。")
        return
        
    latest = df.iloc[-1]
    
    st.markdown(f"### 🐳 {symbol} 籌碼監控 ｜ 💰 <span style='color:{color_hex}'>**${latest.price:,}**</span>", unsafe_allow_html=True)

    col_left, col_right = st.columns(2)
    with col_left:
        l_acc = latest.get('long_acc_ratio', 0.5)
        s_acc = latest.get('short_acc_ratio', 0.5)
        st.markdown("#### 👥 帳戶共識 (人數)")
        st.metric("多空帳戶比", f"{l_acc/s_acc:.4f}" if s_acc != 0 else "0")
        
        fig_acc = px.pie(values=[l_acc, s_acc], names=["做多", "做空"], hole=0.6, color=["做多", "做空"], color_discrete_map={"做多": "#00e5ff", "做空": "#ff5252"})
        fig_acc.update_traces(sort=False)
        fig_acc.add_annotation(text="帳戶", showarrow=False, font=dict(size=18, color="white"))
        fig_acc.update_layout(height=220, margin=dict(t=10, b=10, l=10, r=10), showlegend=True, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', font=dict(size=12, color="white"), legend=dict(font=dict(color="#FFFFFF", size=12), orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)) 
        st.plotly_chart(fig_acc, use_container_width=True)

    with col_right:
        st.markdown("#### 💰 資金實力 (倉位)")
        st.metric("多空持倉比", f"{latest['ls_ratio']:.4f}")
        
        fig_pos = px.pie(values=[latest['long_vol_usd'], latest['short_vol_usd']], names=["做多", "做空"], hole=0.6, color=["做多", "做空"], color_discrete_map={"做多": "#00e5ff", "做空": "#ff5252"})
        fig_pos.update_traces(sort=False)
        fig_pos.add_annotation(text="資金", showarrow=False, font=dict(size=18, color="white"))
        fig_pos.update_layout(height=220, margin=dict(t=10, b=10, l=10, r=10), showlegend=True, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', font=dict(size=12, color="white"), legend=dict(font=dict(color="#FFFFFF", size=12), orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
        st.plotly_chart(fig_pos, use_container_width=True)
    
    st.divider()
    
    fig_line = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.4, 0.3, 0.3])
    
    fig_line.add_trace(go.Scatter(x=df["time"], y=df["price"], name="價格", line=dict(color=color_hex, width=3)), row=1, col=1)
    fig_line.add_trace(go.Scatter(x=df["time"], y=df["long_vol_usd"], name="多單$", line=dict(color="#b2ebf2", width=2)), row=2, col=1)
    fig_line.add_trace(go.Scatter(x=df["time"], y=df["short_vol_usd"], name="空單$", line=dict(color="#ffcdd2", width=2)), row=2, col=1)
    fig_line.add_trace(go.Scatter(x=df["time"], y=df["ls_ratio"], name="持倉比", line=dict(color="#FFFFFF", width=2.5)), row=3, col=1)
    fig_line.add_trace(go.Scatter(x=df["time"], y=df["ls_acc_ratio"], name="帳戶比", line=dict(color="#00e676", width=2.5)), row=3, col=1)
    
    # 🚀 優化 1：徹底黑化游標提示框
    fig_line.update_layout(
        template="plotly_dark", 
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)', 
        height=550, 
        hovermode="x unified", 
        hoverlabel=dict(
            bgcolor="rgba(20, 20, 20, 0.9)", # 深灰色半透明背景
            font_size=12,
            font_color="white",              # 字體改為純白
            bordercolor="rgba(255, 255, 255, 0.2)" # 淡淡的銀色邊框
        ),
        margin=dict(t=50, b=10, l=10, r=40), 
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(color="#FFFFFF", size=12))
    )
    
    # 🚀 優化 2：把粗虛線變成優雅的極細半透明實線
    fig_line.update_xaxes(
        showgrid=True, gridwidth=1, gridcolor='rgba(255, 255, 255, 0.08)', 
        showline=True, linewidth=1.5, linecolor='rgba(255,255,255,0.2)', 
        mirror=True, ticks="outside", tickwidth=1, tickcolor='rgba(255, 255, 255, 0.08)', 
        ticklen=5, tickangle=-45, tickformat="%m-%d %H:%M",
        showspikes=True, spikemode="across", spikedash="solid", # 改為實線
        spikethickness=1, spikecolor="rgba(255, 255, 255, 0.3)" # 1px 半透明白色
    )
    
    fig_line.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255, 255, 255, 0.08)', showline=True, linewidth=1.5, linecolor='rgba(255,255,255,0.2)', mirror=True, ticks="outside", tickwidth=1, tickcolor='rgba(255, 255, 255, 0.08)', ticklen=5)
    fig_line.update_layout(yaxis=dict(tickfont=dict(color=color_hex, size=11)), yaxis2=dict(tickfont=dict(color="#b2ebf2", size=11)), yaxis3=dict(tickfont=dict(color="#FFFFFF", size=11)))
    
    st.plotly_chart(fig_line, use_container_width=True)

    st.markdown(f"**📋 {symbol} 巡檢紀錄 (近20筆)**")
    df_20 = df.tail(20).iloc[::-1]
    st.markdown(f'<div class="table-wrapper">{build_table(df_20)}</div>', unsafe_allow_html=True)

    with st.expander(f"📂 展開 {symbol} 完整紀錄 (近一個月)"):
        st.markdown(f'<div class="scrollable-wrapper">{build_table(df.iloc[::-1])}</div>', unsafe_allow_html=True)

# 主程式呼叫
try:
    render_section("BTC", "whale_data", "btc_price", "#ffd700")
    st.markdown("<br><hr style='border: 1px solid #333;'><br>", unsafe_allow_html=True)
    render_section("ETH", "eth_whale_data", "eth_price", "#a0a0ff")
except Exception as e:
    st.error(f"連線失敗: {e}")
    
st_autorefresh(interval=300000, key="data_refresher")



# 每 300,000 毫秒（5 分鐘）自動刷新網頁一次

