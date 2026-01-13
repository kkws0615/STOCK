import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import urllib3

# --- 設定頁面 ---
st.set_page_config(page_title="台股 ETF 全市場配息神算", layout="wide")
st.title("📈 台股全市場 ETF 配息排行 & 存股計算機")

# --- 初始化 Session State ---
if 'stock_df' not in st.session_state:
    st.session_state.stock_df = pd.DataFrame()
if 'etf_list' not in st.session_state:
    st.session_state.etf_list = {}

# --- 擴充版備用清單 (萬一爬蟲失敗，至少有這些) ---
FALLBACK_ETFS = {
    "0050.TW": "元大台灣50", "0056.TW": "元大高股息", "00878.TW": "國泰永續高股息", "00929.TW": "復華台灣科技優息",
    "00919.TW": "群益台灣精選高息", "00940.TW": "元大台灣價值高息", "00939.TW": "統一台灣高息動能", "006208.TW": "富邦台50",
    "00713.TW": "元大台灣高息低波", "00900.TW": "富邦特選高股息30", "00881.TW": "國泰台灣5G+", "00692.TW": "富邦公司治理",
    "0051.TW": "元大中型100", "0052.TW": "富邦科技", "00631L.TW": "元大台灣50正2", "00632R.TW": "元大台灣50反1",
    "00679B.TW": "元大美債20年", "00687B.TW": "國泰20年美債", "00937B.TW": "群益ESG投等債20+", "00751B.TW": "元大AAA至A公司債",
    "00720B.TW": "元大投資級公司債", "00725B.TW": "國泰投資級公司債", "00850.TW": "元大臺灣ESG永續", "00923.TW": "群益台灣ESG低碳",
    "0053.TW": "元大電子", "0055.TW": "元大MSCI金融", "0057.TW": "富邦摩台", "006203.TW": "元大MSCI台灣",
    "006204.TW": "永豐臺灣加權", "00662.TW": "富邦NASDAQ", "00646.TW": "元大S&P500", "00830.TW": "國泰費城半導體",
    "00891.TW": "中信關鍵半導體", "00892.TW": "富邦台灣半導體", "00893.TW": "國泰智能電動車", "00895.TW": "富邦未來車",
    "00905.TW": "FT臺灣Smart", "00918.TW": "大華優利高填息30", "00915.TW": "凱基優選高股息30", "00922.TW": "國泰台灣領袖50",
    "00927.TW": "群益半導體收益", "00932.TW": "兆豐永續高息等權", "00934.TW": "中信成長高股息", "00935.TW": "野村臺灣新科技50",
    "00936.TW": "台新永續高息中小", "00944.TW": "野村趨勢動能高息", "00946.TW": "群益科技高息成長", "00943.TW": "兆豐電子高息等權",
    "00941.TW": "中信上游半導體", "00921.TW": "兆豐龍頭等權", "00690.TW": "兆豐臺灣藍籌30", "00701.TW": "國泰股利精選30",
    "00730.TW": "富邦臺灣優質高息", "00731.TW": "復華富時高息低波", "00907.TW": "永豐優息存股"
}

# --- 核心函數：抓取全台 ETF 清單 (爬蟲) ---
@st.cache_data(ttl=86400)
def fetch_tw_etfs():
    # 忽略 SSL 警告
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    try:
        url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
        
        # 修正 1: 加入 User-Agent 偽裝成瀏覽器
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # 修正 2: 設定 timeout 避免卡死
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        
        # 讀取 HTML
        dfs = pd.read_html(res.text)
        df = dfs[0]
        
        # 整理資料
        df.columns = df.iloc[0]
        df = df.iloc[1:]
        
        # 篩選 ETF
        target_df = df[df['有價證券別'] == 'ETF']
        
        etf_dict = {}
        for index, row in target_df.iterrows():
            code_name = row['有價證券代號及名稱']
            if " " in code_name:
                code, name = code_name.split(" ", 1)
                etf_dict[f"{code}.TW"] = name
            elif "\u3000" in code_name:
                code, name = code_name.split("\u3000", 1)
                etf_dict[f"{code}.TW"] = name
        
        # 如果抓到的數量太少(例如被擋只抓到空殼)，就拋出錯誤用備用清單
        if len(etf_dict) < 10:
            raise ValueError("抓取數量異常")
            
        return etf_dict

    except Exception as e:
        # 這裡會靜默失敗，回傳備用清單，但我們會在介面上顯示警告
        print(f"爬蟲失敗: {e}")
        return FALLBACK_ETFS

# --- 核心函數：抓取股價與配息 ---
def get_batch_data(ticker_dict):
    data = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(ticker_dict)
    
    # 轉成 List 處理
    keys = list(ticker_dict.keys())
    
    for i, ticker in enumerate(keys):
        name = ticker_dict[ticker]
        
        # 更新進度
        progress = (i + 1) / total
        progress_bar.progress(progress)
        status_text.text(f"正在分析 ({i+1}/{total}): {name} ({ticker})...")
        
        try:
            stock = yf.Ticker(ticker)
            price = stock.fast_info.last_price
            if price is None:
                info = stock.info
                price = info.get('currentPrice', info.get('previousClose', 0))

            if price is None or price == 0:
                continue

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

            data.append({
                "代號": yahoo_url, 
                "名稱": name,
                "配息明細 (近1年)": history_str,
                "現價 (元)": price,
                "近一年配息 (每張)": int(div_per_sheet_year),
                "等值月配息 (每張)": int(avg_monthly_income_sheet),
                "年殖利率 (%)": yield_rate
            })
        except Exception as e:
            continue
            
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(data)

# --- 側邊欄：工具區 ---
with st.sidebar:
    st.header("⚙️ 設定")
    if st.button("🗑️ 清除快取 (重置資料)"):
        st.cache_data.clear()
        if 'stock_df' in st.session_state:
            del st.session_state['stock_df']
        if 'etf_list' in st.session_state:
            del st.session_state['etf_list']
        st.rerun()

# --- 主程式邏輯 ---
if not st.session_state.etf_list:
    with st.spinner("正在連線證交所更新最新 ETF 清單..."):
        st.session_state.etf_list = fetch_tw_etfs()

# 檢查是否使用了備用清單
is_fallback = len(st.session_state.etf_list) == len(FALLBACK_ETFS)
list_count = len(st.session_state.etf_list)

etf_options = [f"{code} {name}" for code, name in st.session_state.etf_list.items()]

# --- 介面佈局 ---
tab1, tab2 = st.tabs(["🏆 全台 ETF 配息排行", "💰 存股計算機 (以張為單位)"])

# === 第一區塊：排行 ===
with tab1:
    col_btn, col_count = st.columns([1, 4])
    with col_btn:
        if st.button("🚀 開始掃描全市場"):
            st.toast(f"開始掃描 {list_count} 檔 ETF，請耐心等候...", icon="⏳")
            df = get_batch_data(st.session_state.etf_list)
            if not df.empty:
                st.session_state.stock_df = df.sort_values(by="等值月配息 (每張)", ascending=False).reset_index(drop=True)
            else:
                st.error("掃描失敗，請稍後再試")
    
    with col_count:
        if is_fallback:
            st.warning(f"⚠️ 證交所連線不穩，目前使用內建熱門清單 (共 {list_count} 檔)。")
        else:
            st.success(f"✅ 已成功連線證交所，目前資料庫共有 {list_count} 檔上市 ETF")

    # 顯示搜尋與表格
    if not st.session_state.stock_df.empty:
        
        search_term = st.text_input("🔍 搜尋結果 (輸入關鍵字後按 Enter)", "")
        
        df_display = st.session_state.stock_df
        if search_term:
            df_display = df_display[
                df_display["名稱"].str.contains(search_term, case=False) | 
                df_display["代號"].str.contains(search_term, case=False)
            ]

        st.dataframe(
            df_display,
            column_config={
                "代號": st.column_config.LinkColumn(
                    "代號", 
                    display_text=r"quote/(.*)", 
                    help="點擊前往 Yahoo 股市" 
                ),
                "配息明細 (近1年)": st.column_config.TextColumn(
                    "近1年配息明細 (元/股)",
                    width="medium"
                ),
                "現價 (元)": st.column_config.NumberColumn(format="$ %.2f"),
                "近一年配息 (每張)": st.column_config.NumberColumn(format="$ %d"),
                "等值月配息 (每張)": st.column_config.NumberColumn(format="$ %d"),
                "年殖利率 (%)": st.column_config.ProgressColumn(
                    format="%.2f%%", min_value=0, max_value=15
                ),
            },
            use_container_width=True,
            hide_index=True,
            height=800 
        )
    else:
        st.info("👆 請點擊上方按鈕開始掃描")

# === 第二區塊：計算機 ===
with tab2:
    st.header("每「張」股票配息試算")
    col1, col2 = st.columns(2)
    
    with col1:
        selected_option = st.selectbox("🔍 搜尋並選擇 ETF/股票", etf_options)
        
        if selected_option:
            ticker = selected_option.split(" ")[0]
            name = selected_option.split(" ")[1]
            stock = yf.Ticker(ticker)
            price = stock.fast_info.last_price
            if price is None:
                 info = stock.info
                 price = info.get('currentPrice', info.get('previousClose', 0))
            
            divs = stock.dividends
            if not divs.empty:
                one_year_ago = pd.Timestamp.now(tz=divs.index.tz) - pd.Timedelta(days=365)
                annual_div_share = divs[divs.index > one_year_ago].sum()
            else:
                annual_div_share = 0

            price_per_sheet = price * 1000
            monthly_income_per_sheet = (annual_div_share * 1000) / 12
            
            st.divider()
            st.metric("股票名稱", f"{name} ({ticker})")
            st.metric("目前股價 (每股)", f"${price:.2f}")
            st.metric("買一張成本", f"${int(price_per_sheet):,}")
            st.metric("平均每張每月可領", f"${int(monthly_income_per_sheet):,}")

    with col2:
        investment_amount = st.number_input("💰 預計投入金額 (台幣)", value=100000, step=10000)
        if selected_option and price > 0:
            sheets_can_buy = int(investment_amount / price_per_sheet)
            remainder_money = investment_amount - (sheets_can_buy * price_per_sheet)
            total_monthly_income = sheets_can_buy * monthly_income_per_sheet
            
            st.divider()
            st.subheader("試算結果")
            st.success(f"可買進 **{sheets_can_buy}** 張")
            if sheets_can_buy > 0:
                st.info(f"預估每月總共可領: **NT$ {int(total_monthly_income):,}** 元")
            else:
                st.warning("資金不足以買進一張")
            st.caption(f"剩餘資金: ${int(remainder_money):,} (不足一張)")
