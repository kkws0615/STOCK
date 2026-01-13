import streamlit as st
import yfinance as yf
import pandas as pd

# --- 設定頁面 ---
st.set_page_config(page_title="台股 ETF 百大配息榜", layout="wide")
st.title("📈 台股百大熱門 ETF 配息排行 & 存股計算機")

# --- 注入 CSS 樣式 (處理浮動視窗與表格美化) ---
st.markdown("""
<style>
    /* 表格樣式 */
    table.custom-table {
        width: 100%;
        border-collapse: collapse;
        font-family: sans-serif;
    }
    table.custom-table th {
        background-color: #f0f2f6;
        color: #31333F;
        padding: 10px;
        text-align: left;
        border-bottom: 2px solid #ddd;
    }
    table.custom-table td {
        padding: 8px 10px;
        border-bottom: 1px solid #eee;
    }
    table.custom-table tr:hover {
        background-color: #f9f9f9;
    }
    
    /* 連結樣式 */
    .stock-link {
        color: #0068c9;
        text-decoration: none;
        font-weight: bold;
    }
    .stock-link:hover {
        text-decoration: underline;
    }

    /* === 浮動視窗 (Tooltip) 核心 CSS === */
    .my-tooltip {
        position: relative;
        display: inline-block;
        border-bottom: 1px dashed #888; /* 虛線底線提示可互動 */
        cursor: pointer; /* 滑鼠變手指 */
    }

    /* 浮動內容框 */
    .my-tooltip .my-tooltiptext {
        visibility: hidden;
        width: 220px;
        background-color: #333;
        color: #fff;
        text-align: center;
        border-radius: 6px;
        padding: 8px;
        position: absolute;
        z-index: 1000;
        bottom: 125%; /* 顯示在上方 */
        left: 50%;
        margin-left: -110px; /* 居中 */
        opacity: 0;
        transition: opacity 0.3s;
        font-size: 0.9em;
        line-height: 1.4;
        box-shadow: 0px 4px 8px rgba(0,0,0,0.2);
    }

    /* 箭頭 */
    .my-tooltip .my-tooltiptext::after {
        content: "";
        position: absolute;
        top: 100%;
        left: 50%;
        margin-left: -5px;
        border-width: 5px;
        border-style: solid;
        border-color: #333 transparent transparent transparent;
    }

    /* 觸發機制：電腦 Hover 或 手機 Focus (點擊) */
    .my-tooltip:hover .my-tooltiptext,
    .my-tooltip:focus .my-tooltiptext, 
    .my-tooltip:focus-within .my-tooltiptext {
        visibility: visible;
        opacity: 1;
    }
</style>
""", unsafe_allow_html=True)

# --- 初始化 Session State ---
if 'stock_df' not in st.session_state:
    st.session_state.stock_df = pd.DataFrame()

# --- 內建：台股百大熱門 ETF 資料庫 ---
ETF_DB = {
    # === 高股息 ===
    "0056.TW": "元大高股息", "00878.TW": "國泰永續高股息", "00929.TW": "復華台灣科技優息", 
    "00919.TW": "群益台灣精選高息", "00940.TW": "元大台灣價值高息", "00939.TW": "統一台灣高息動能",
    "00713.TW": "元大台灣高息低波", "00900.TW": "富邦特選高股息30", "00915.TW": "凱基優選高股息30",
    "00918.TW": "大華優利高填息30", "00934.TW": "中信成長高股息", "00936.TW": "台新永續高息中小",
    "00944.TW": "野村趨勢動能高息", "00946.TW": "群益科技高息成長", "00943.TW": "兆豐電子高息等權",
    "00701.TW": "國泰股利精選30", "00731.TW": "復華富時高息低波", "00690.TW": "兆豐臺灣藍籌30",
    "00730.TW": "富邦臺灣優質高息", "00907.TW": "永豐優息存股", "00932.TW": "兆豐永續高息等權",
    "00927.TW": "群益半導體收益",
    # === 市值/科技/債券/其他 (保留原本完整清單) ===
    "0050.TW": "元大台灣50", "006208.TW": "富邦台50", "00692.TW": "富邦公司治理", 
    "00922.TW": "國泰台灣領袖50", "00923.TW": "群益台灣ESG低碳", "00850.TW": "元大臺灣ESG永續",
    "0051.TW": "元大中型100", "006204.TW": "永豐臺灣加權", "0057.TW": "富邦摩台",
    "006203.TW": "元大MSCI台灣", "00921.TW": "兆豐龍頭等權", "00905.TW": "FT臺灣Smart",
    "0052.TW": "富邦科技", "0053.TW": "元大電子", "00881.TW": "國泰台灣5G+",
    "00891.TW": "中信關鍵半導體", "00892.TW": "富邦台灣半導體", "00830.TW": "國泰費城半導體",
    "00935.TW": "野村臺灣新科技50", "00941.TW": "中信上游半導體", "00893.TW": "國泰智能電動車",
    "00895.TW": "富邦未來車", "00901.TW": "永豐智能車供應鏈", "00733.TW": "富邦臺灣中小",
    "0055.TW": "元大MSCI金融", "00938.TW": "凱基優選30",
    "00679B.TW": "元大美債20年", "00687B.TW": "國泰20年美債", "00937B.TW": "群益ESG投等債20+",
    "00933B.TW": "國泰10Y+金融債", "00720B.TW": "元大投資級公司債", "00725B.TW": "國泰投資級公司債",
    "00751B.TW": "元大AAA至A公司債", "00772B.TW": "中信高評級公司債", "00795B.TW": "中信美國公債20年",
    "00680L.TW": "元大美債20正2", "00688L.TW": "國泰20年美債正2", "00857B.TW": "永豐20年美債",
    "00724B.TW": "群益10年IG金融債", "00746B.TW": "富邦A級公司債", "00740B.TW": "富邦全球投等債",
    "00662.TW": "富邦NASDAQ", "00646.TW": "元大S&P500", "00757.TW": "統一FANG+",
    "006205.TW": "富邦上証", "0061.TW": "元大寶滬深", "00636.TW": "國泰中國A50",
    "00882.TW": "中信中國高股息", "00885.TW": "富邦越南", "00909.TW": "國泰數位支付服務",
    "00861.TW": "元大全球未來通訊", "00762.TW": "元大全球AI", "00851.TW": "台新全球AI",
    "00631L.TW": "元大台灣50正2", "00632R.TW": "元大台灣50反1", "00673R.TW": "元大SP500反1",
    "00650L.TW": "復華香港正2", "00655L.TW": "國泰中國A50正2"
}

etf_options = [f"{code} {name}" for code, name in ETF_DB.items()]

# --- 核心函數：抓取股價與配息 ---
def get_batch_data(ticker_dict):
    data = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(ticker_dict)
    keys = list(ticker_dict.keys())
    
    for i, ticker in enumerate(keys):
        name = ticker_dict[ticker]
        progress_bar.progress((i + 1) / total)
        status_text.text(f"正在分析 ({i+1}/{total}): {name}...")
        
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
                    if count >= 10: freq_tag = "月配"
                    elif count >= 3: freq_tag = "季配"
                    elif count == 2: freq_tag = "半"
                    else: freq_tag = "年配"
                    
                    vals = [f"{x:.2f}".rstrip('0').rstrip('.') for x in last_year_divs.tolist()]
                    # 把詳細資料存在變數裡，不放在表格直接顯示
                    history_str = f"【{freq_tag}】<br>近一年明細:<br>{' / '.join(vals)}"

            div_per_sheet_year = total_annual_div * 1000
            avg_monthly_income_sheet = div_per_sheet_year / 12
            yield_rate = (total_annual_div / price) * 100 if price > 0 else 0
            
            # 代號只顯示數字，方便手機看
            short_code = ticker.replace(".TW", "")
            yahoo_url = f"https://tw.stock.yahoo.com/quote/{short_code}"

            data.append({
                "code_url": yahoo_url,
                "code_text": short_code,
                "name": name,
                "tooltip_content": history_str, # 這是要藏在浮動視窗的內容
                "price": price,
                "monthly_income": int(avg_monthly_income_sheet),
                "yield": yield_rate
            })
        except:
            continue
            
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(data)

# --- 產生 HTML 表格的函數 ---
def generate_html_table(df):
    html = '<table class="custom-table">'
    # 表頭
    html += '<thead><tr>'
    html += '<th width="15%">代號</th>'
    html += '<th width="35%">名稱 (點擊看明細)</th>'
    html += '<th width="15%">股價</th>'
    html += '<th width="20%">月領(張)</th>'
    html += '<th width="15%">殖利率</th>'
    html += '</tr></thead><tbody>'
    
    for _, row in df.iterrows():
        # 1. 代號 (超連結)
        code_cell = f'<a href="{row["code_url"]}" target="_blank" class="stock-link">{row["code_text"]}</a>'
        
        # 2. 名稱 (浮動視窗)
        # tabindex="0" 讓手機點擊時可以取得焦點 (Focus)，觸發 CSS 的顯示效果
        name_cell = f'''
        <div class="my-tooltip" tabindex="0">
            {row["name"]}
            <span class="my-tooltiptext">{row["tooltip_content"]}</span>
        </div>
        '''
        
        # 3. 數據格式化
        price_cell = f"${row['price']:.2f}"
        monthly_cell = f"${row['monthly_income']:,}"
        yield_cell = f"{row['yield']:.2f}%"
        
        html += f'<tr>'
        html += f'<td>{code_cell}</td>'
        html += f'<td>{name_cell}</td>'
        html += f'<td>{price_cell}</td>'
        html += f'<td>{monthly_cell}</td>'
        html += f'<td>{yield_cell}</td>'
        html += f'</tr>'
        
    html += '</tbody></table>'
    return html

# --- 介面佈局 ---
tab1, tab2 = st.tabs(["🏆 百大 ETF 排行榜", "💰 存股計算機 (以張為單位)"])

# === 第一區塊：排行 ===
with tab1:
    col_btn, col_sort = st.columns([1, 4])
    with col_btn:
        if st.button("🚀 開始掃描"):
            df = get_batch_data(ETF_DB)
            if not df.empty:
                st.session_state.stock_df = df
            else:
                st.error("掃描失敗")
    
    # 顯示搜尋與表格
    if not st.session_state.stock_df.empty:
        df_display = st.session_state.stock_df
        
        # 排序選項 (因為 HTML 表格不能點標題排序，所以做在這裡)
        with col_sort:
            sort_by = st.selectbox("排序方式", ["依「月領金額」高->低", "依「殖利率」高->低", "依「股價」低->高"])
            
            if "月領" in sort_by:
                df_display = df_display.sort_values(by="monthly_income", ascending=False)
            elif "殖利率" in sort_by:
                df_display = df_display.sort_values(by="yield", ascending=False)
            elif "股價" in sort_by:
                df_display = df_display.sort_values(by="price", ascending=True)

        # 搜尋
        search_term = st.text_input("🔍 搜尋 (輸入代號或名稱，例如: 929)", "")
        if search_term:
            df_display = df_display[
                df_display["name"].str.contains(search_term, case=False) | 
                df_display["code_text"].str.contains(search_term, case=False)
            ]

        # === 關鍵：使用 HTML 渲染表格 ===
        st.markdown(generate_html_table(df_display), unsafe_allow_html=True)
        
    else:
        st.info("👆 請點擊上方按鈕載入資料")

# === 第二區塊：計算機 (維持原樣) ===
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
            st.metric("目前股價", f"${price:.2f}")
            st.metric("買一張成本", f"${int(price_per_sheet):,}")
            st.metric("平均每張月領", f"${int(monthly_income_per_sheet):,}")

    with col2:
        investment_amount = st.number_input("💰 預計投入金額", value=100000, step=10000)
        if selected_option and price > 0:
            sheets_can_buy = int(investment_amount / price_per_sheet)
            remainder = investment_amount - (sheets_can_buy * price_per_sheet)
            total_monthly = sheets_can_buy * monthly_income_per_sheet
            st.divider()
            st.success(f"可買進 **{sheets_can_buy}** 張")
            st.info(f"每月總領: **NT$ {int(total_monthly):,}**")
            st.caption(f"剩餘: ${int(remainder):,}")
