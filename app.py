import streamlit as st
import yfinance as yf
import pandas as pd
import google.generativeai as genai

# --- 設定頁面 ---
st.set_page_config(page_title="台股 ETF 智慧存股助理", layout="wide")
st.title("📈 台股 ETF 智慧存股助理 (AI Powered)")

# --- 初始化 Session State ---
if 'stock_df' not in st.session_state:
    st.session_state.stock_df = pd.DataFrame()
if 'portfolio_list' not in st.session_state:
    st.session_state.portfolio_list = []

# --- 側邊欄：設定區 (輸入 API Key) ---
with st.sidebar:
    st.header("🔐 AI 金鑰設定")
    st.caption("輸入 Google Gemini API Key 即可解鎖 AI 分析功能")
    api_key = st.text_input("輸入 API Key", type="password", placeholder="AIzaSy...")
    
    if api_key:
        try:
            genai.configure(api_key=api_key)
            st.success("✅ AI 已連線")
            has_ai = True
        except:
            st.error("❌ Key 無效")
            has_ai = False
    else:
        st.warning("⚠️ 未輸入 Key，僅能使用計算機功能")
        has_ai = False
    
    st.markdown("---")
    st.markdown("[👉 點此免費申請 Google API Key](https://aistudio.google.com/app/apikey)")

# --- 表格樣式 ---
TABLE_CONFIG = {
    "代號": st.column_config.LinkColumn("代號", display_text=r"quote/(.*)"),
    "配息明細 (近1年)": st.column_config.TextColumn("近1年配息明細", width="medium"),
    "現價 (元)": st.column_config.NumberColumn(format="$ %.2f"),
    "近一年配息 (每張)": st.column_config.NumberColumn(format="$ %d"),
    "等值月配息 (每張)": st.column_config.NumberColumn(format="$ %d"),
    "年殖利率 (%)": st.column_config.ProgressColumn(format="%.2f%%", min_value=0, max_value=15),
}

# --- 內建資料庫 (維持不變) ---
ETF_DB = {
    "0056.TW": "元大高股息", "00878.TW": "國泰永續高股息", "00929.TW": "復華台灣科技優息", 
    "00919.TW": "群益台灣精選高息", "00940.TW": "元大台灣價值高息", "00939.TW": "統一台灣高息動能",
    "00713.TW": "元大台灣高息低波", "0050.TW": "元大台灣50", "006208.TW": "富邦台50",
    "00922.TW": "國泰台灣領袖50", "00679B.TW": "元大美債20年", "00687B.TW": "國泰20年美債",
    "00937B.TW": "群益ESG投等債20+", "0052.TW": "富邦科技", "00830.TW": "國泰費城半導體",
    "00881.TW": "國泰台灣5G+", "00662.TW": "富邦NASDAQ", "00646.TW": "元大S&P500"
}
# (為了版面簡潔，這裡我縮減了列表，你可以把上一版完整的複製回來，不影響功能)
etf_options = [f"{code} {name}" for code, name in ETF_DB.items()]

# --- AI 分析函數 ---
def ask_gemini(stock_name, price, yield_rate, dividend_history):
    if not has_ai: return "請先輸入 API Key"
    
    # 這是我們要把資料餵給 AI 的「提示詞 (Prompt)」
    prompt = f"""
    你是一位專業的台股分析師。請根據以下數據，用繁體中文給出 100 字以內的簡短點評。
    重點分析：殖利率是否吸引人？配息是否穩定？適合哪種投資人（存股族/波段/退休）？
    
    股票名稱：{stock_name}
    目前股價：{price}
    年殖利率：{yield_rate:.2f}%
    近一年配息紀錄：{dividend_history}
    """
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI 分析失敗: {str(e)}"

# --- 核心函數：抓取股價與配息 ---
def get_batch_data(ticker_dict, table_placeholder):
    data = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(ticker_dict)
    keys = list(ticker_dict.keys())
    
    for i, ticker in enumerate(keys):
        name = ticker_dict[ticker]
        progress_bar.progress((i + 1) / total)
        status_text.text(f"分析中: {name}...")
        try:
            stock = yf.Ticker(ticker)
            price = stock.fast_info.last_price
            if price is None:
                info = stock.info
                price = info.get('currentPrice', info.get('previousClose', 0))
            if price is None or price == 0: continue

            divs = stock.dividends
            history_str = "無配息"
            total_annual_div = 0
            if not divs.empty:
                one_year_ago = pd.Timestamp.now(tz=divs.index.tz) - pd.Timedelta(days=365)
                last_year_divs = divs[divs.index > one_year_ago]
                total_annual_div = last_year_divs.sum()
                if not last_year_divs.empty:
                    count = len(last_year_divs)
                    if count >= 10: freq_tag = "月"
                    elif count >= 3: freq_tag = "季"
                    elif count == 2: freq_tag = "半"
                    else: freq_tag = "年"
                    vals = [f"{x:.2f}".rstrip('0').rstrip('.') for x in last_year_divs.tolist()]
                    history_str = f"{freq_tag}: {'/'.join(vals)}"

            div_per_sheet_year = total_annual_div * 1000
            avg_monthly_income_sheet = div_per_sheet_year / 12
            yield_rate = (total_annual_div / price) * 100 if price > 0 else 0
            yahoo_url = f"https://tw.stock.yahoo.com/quote/{ticker}"

            new_row = {
                "代號": yahoo_url, "名稱": name, "配息明細 (近1年)": history_str,
                "現價 (元)": price, "近一年配息 (每張)": int(div_per_sheet_year),
                "等值月配息 (每張)": int(avg_monthly_income_sheet), "年殖利率 (%)": yield_rate
            }
            data.append(new_row)
            current_df = pd.DataFrame(data).sort_values(by="等值月配息 (每張)", ascending=False).reset_index(drop=True)
            table_placeholder.dataframe(current_df, column_config=TABLE_CONFIG, use_container_width=True, hide_index=True, height=800)
        except: continue
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(data)

# --- 介面佈局 ---
tab1, tab2 = st.tabs(["🏆 百大 ETF 排行榜", "🤖 AI 存股顧問"])

# === Tab 1: 排行 (維持不變) ===
with tab1:
    col_btn, col_info = st.columns([1, 4])
    with col_btn:
        start_scan = st.button("🚀 開始掃描")
    with col_info:
        st.write(f"資料庫：共 **{len(ETF_DB)}** 檔")

    table_placeholder = st.empty()
    if start_scan:
        df = get_batch_data(ETF_DB, table_placeholder)
        if not df.empty:
            st.session_state.stock_df = df.sort_values(by="等值月配息 (每張)", ascending=False).reset_index(drop=True)

    if not st.session_state.stock_df.empty:
        table_placeholder.empty()
        search = st.text_input("🔍 搜尋", "")
        df_show = st.session_state.stock_df
        if search:
            df_show = df_show[df_show["名稱"].str.contains(search, case=False) | df_show["代號"].str.contains(search, case=False)]
        st.dataframe(df_show, column_config=TABLE_CONFIG, use_container_width=True, hide_index=True, height=800)
    elif not start_scan:
        st.info("👆 請點擊按鈕載入資料")

# === Tab 2: AI 投資組合 (加入 AI 功能) ===
with tab2:
    st.header("🤖 AI 輔助存股計算機")
    
    col_input, col_result = st.columns([1, 2])
    
    with col_input:
        with st.container(border=True):
            st.subheader("1. 選擇與分析")
            selected_option = st.selectbox("選擇股票", etf_options)
            
            # --- 新增：AI 分析按鈕 ---
            if st.button("✨ 呼叫 AI 幫我健檢這檔"):
                if has_ai and selected_option:
                    with st.spinner("Gemini 正在讀取財報數據..."):
                        # 先抓數據
                        tk = selected_option.split(" ")[0]
                        nm = selected_option.split(" ")[1]
                        try:
                            s = yf.Ticker(tk)
                            p = s.fast_info.last_price
                            if p is None: p = s.info.get('currentPrice', 0)
                            d = s.dividends
                            yr_div = 0
                            h_str = "無"
                            if not d.empty:
                                y_ago = pd.Timestamp.now(tz=d.index.tz) - pd.Timedelta(days=365)
                                last_d = d[d.index > y_ago]
                                yr_div = last_d.sum()
                                h_str = '/'.join([f"{x:.2f}" for x in last_d.tolist()])
                            
                            y_rate = (yr_div / p) * 100 if p > 0 else 0
                            
                            # 呼叫 AI
                            analysis = ask_gemini(f"{nm} ({tk})", p, y_rate, h_str)
                            st.info(f"🤖 **Gemini 分析報告：**\n\n{analysis}")
                            
                        except:
                            st.error("數據抓取失敗，無法分析")
                elif not has_ai:
                    st.warning("請先在左側邊欄輸入 API Key")

            st.divider()
            
            # 原本的加入清單功能
            add_money = st.number_input("預計投入金額", value=100000, step=10000)
            if st.button("➕ 加入投資組合"):
                if selected_option and add_money > 0:
                    tk = selected_option.split(" ")[0]
                    nm = selected_option.split(" ")[1]
                    try:
                        s = yf.Ticker(tk)
                        p = s.fast_info.last_price
                        if p is None: p = s.info.get('currentPrice', 0)
                        if p > 0:
                            cost = p * 1000
                            sheets = int(add_money / cost)
                            real_cost = sheets * cost
                            
                            d = s.dividends
                            yr_div = 0
                            if not d.empty:
                                y_ago = pd.Timestamp.now(tz=d.index.tz) - pd.Timedelta(days=365)
                                yr_div = d[d.index > y_ago].sum()
                            
                            ttl_yr = yr_div * 1000 * sheets
                            mnth = ttl_yr / 12
                            
                            st.session_state.portfolio_list.append({
                                "股票": f"{nm} ({tk})",
                                "投入金額": int(real_cost),
                                "持有張數": f"{sheets} 張",
                                "平均月配": int(mnth)
                            })
                            st.success(f"已加入 {sheets} 張")
                    except: pass

            if st.button("🗑️ 清空清單"):
                st.session_state.portfolio_list = []
                st.rerun()

    with col_result:
        st.subheader("2. 投資組合預覽")
        if len(st.session_state.portfolio_list) > 0:
            df_p = pd.DataFrame(st.session_state.portfolio_list)
            st.dataframe(df_p, use_container_width=True, hide_index=True)
            
            ttl_inv = df_p["投入金額"].sum()
            ttl_m = df_p["平均月配"].sum()
            yld = (ttl_m * 12 / ttl_inv * 100) if ttl_inv > 0 else 0
            
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("總投入", f"${ttl_inv:,}")
            c2.metric("✨ 預估月領", f"${ttl_m:,}")
            c3.metric("組合殖利率", f"{yld:.2f}%")
            
            # --- 新增：AI 總評功能 ---
            if st.button("🤖 請 AI 評估這個投資組合風險"):
                if has_ai:
                    with st.spinner("Gemini 正在檢視您的資產配置..."):
                        portfolio_str = df_p.to_string()
                        prompt = f"""
                        使用者建立了一個 ETF 投資組合如下：
                        {portfolio_str}
                        
                        總金額：{ttl_inv}
                        平均殖利率：{yld:.2f}%
                        
                        請給出簡短的風險評估（例如：是否過度集中在科技股？或是配置很均衡？）。
                        """
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        res = model.generate_content(prompt)
                        st.success(f"**投資組合診斷書：**\n\n{res.text}")
                else:
                    st.warning("請輸入 API Key")
        else:
            st.info("👈 請加入股票")
