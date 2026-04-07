# ... 前面 import 與 CSS 不變 ...

try:
    df_history = get_data_from_db()
    
    if not df_history.empty:
        latest = df_history.iloc[-1]
        
        # ----- 畫面渲染 -----
        st.markdown(f"### 🐳 比特幣主力籌碼監控終端 ｜ 💰 價格: **${latest['btc_price']:,}**")

        col_left, col_right = st.columns(2)
        with col_left:
            # 判斷是否有新欄位資料（相容舊資料）
            l_acc = latest.get('long_acc_ratio', 0.5)
            s_acc = latest.get('short_acc_ratio', 0.5)
            
            st.markdown(f"**👥 大戶【帳戶數】** (更新: {latest['time']})")
            c1, c2, c3 = st.columns(3)
            c1.metric("做多比例", f"{l_acc * 100:.2f}%")
            c2.metric("做空比例", f"{s_acc * 100:.2f}%")
            c3.metric("多空帳戶比", round(l_acc/s_acc, 4) if s_acc != 0 else 0)
            
            fig_acc = px.pie(values=[l_acc, s_acc], names=["做多", "做空"], hole=0.4,
                             color=["做多", "做空"], color_discrete_map={"做多": "#00e5ff", "做空": "#ff5252"})
            fig_acc.update_layout(height=160, margin=dict(t=0, b=0, l=0, r=0), showlegend=False, template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)") 
            st.plotly_chart(fig_acc, use_container_width=True)

        with col_right:
            st.markdown(f"**💰 大戶【真實資金量】** (單位: USD)")
            c4, c5, c6 = st.columns(3)
            c4.metric("多單資金", f"${latest['long_vol_usd']/1e6:,.0f} M")
            c5.metric("空單資金", f"${latest['short_vol_usd']/1e6:,.0f} M")
            c6.metric("資金費率", f"{latest['fund_rate'] * 100:.4f}%")
            
            fig_pos = px.pie(values=[latest['long_vol_usd'], latest['short_vol_usd']], names=["做多", "做空"], hole=0.4,
                             color=["做多", "做空"], color_discrete_map={"做多": "#00e5ff", "做空": "#ff5252"})
            fig_pos.update_layout(height=160, margin=dict(t=0, b=0, l=0, r=0), showlegend=False, template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pos, use_container_width=True)
        
        st.divider()
        
        # --- 趨勢圖表 (與之前邏輯相同) ---
        # (這裡省略重複的 fig_line 代碼，保持原樣即可)
        # ...
        
        # --- 表格邏輯優化 ---
        st.markdown("**📋 歷史巡檢紀錄表 (最新 20 筆)**")
        # 預設只顯示最後 20 筆，且時間反轉排序（最新在上）
        st.dataframe(df_history.tail(20).iloc[::-1], use_container_width=True)

        with st.expander("📂 展開完整歷史數據紀錄 (所有雲端採樣點)"):
            st.dataframe(df_history.iloc[::-1], use_container_width=True)

except Exception as e:
    st.error(f"資料讀取失敗: {e}")

# ... 結尾刷新邏輯 ...
