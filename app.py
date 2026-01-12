import streamlit as st
import yfinance as yf
import pandas as pd

# 設定頁面標題
st.set_page_config(page_title="台股 ETF 等值月配息計算機", layout="wide")
st.title("📈 台股 ETF/股票 等值月配息分析")

# --- 側邊欄：設定觀察清單 ---
st.sidebar.header("設定")
# 預設一些熱門 ETF
default_tickers = "0050.TW, 0056.TW, 00878.TW, 00929.TW, 2330.TW"
user_tickers = st.sidebar.text_area("輸入股票代號 (用逗號分隔)", value=default_tickers)

# 將字串轉為 List
ticker_list = [t.strip().upper() for t in user_tickers.split(",")]

# --- 核心函數：獲取資料 ---
@st.cache_data
def get_stock_data(tickers):
    data = []
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # 獲取歷史配息
            divs = stock.dividends
            
            # 篩選過去 365 天的配息
            one_year_ago = pd.Timestamp.now() - pd.Timedelta(days=365)
            last_year_divs = divs[divs.index > one_year_ago.tz_localize(divs.index.dtype.tz)]
            
            total_annual_div = last_year_divs.sum() # 近一年總配息
            current_price = info.get('currentPrice', info.get('previousClose', 0))
            
            # 計算
            avg_monthly_income = total_annual_div / 12
            yield_rate = (total_annual_div / current_price) * 100 if current_price > 0 else 0
            
            data.append({
                "代號": ticker,
                "名稱": info.get('longName', ticker),
                "現價": current_price,
                "近一年總配息": round(total_annual_div, 2),
                "等值月配息 (每股)": round(avg_monthly_income, 3),
                "年殖利率 (%)": round(yield_rate, 2)
            })
        except Exception as e:
            pass # 忽略錯誤的代號
            
    return pd.DataFrame(data)

# --- 獲取資料 ---
if ticker_list:
    df = get_stock_data(ticker_list)
else:
    df = pd.DataFrame()

# --- 頁面佈局 ---
tab1, tab2 = st.tabs(["🏆 存股排行 (等值月配)", "💰 試算計算機"])

# === 第一區塊：排序 ===
with tab1:
    st.header("近一年配息排行")
    if not df.empty:
        # 排序邏輯：依照「等值月配息」降序排列
        sorted_df = df.sort_values(by="等值月配息 (每股)", ascending=False).reset_index(drop=True)
        
        # 顯示表格 (使用 dataframe 會有互動排序功能)
        st.dataframe(
            sorted_df,
            column_config={
                "等值月配息 (每股)": st.column_config.NumberColumn(
                    "等值月配息 (元)",
                    format="$ %.3f",
                ),
                "近一年總配息": st.column_config.NumberColumn(
                    "近一年總配息",
                    format="$ %.2f",
                ),
                "年殖利率 (%)": st.column_config.ProgressColumn(
                    "年殖利率",
                    format="%.2f%%",
                    min_value=0,
                    max_value=15,
                ),
            },
            use_container_width=True
        )
    else:
        st.warning("無法獲取資料，請檢查股票代號格式 (例如: 00878.TW)")

# === 第二區塊：計算機 ===
with tab2:
    st.header("配息試算")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 輸入：選擇股票
        selected_ticker = st.selectbox("選擇股票", df["代號"] if not df.empty else [])
        
        # 顯示該股票數據
        if selected_ticker:
            stock_info = df[df["代號"] == selected_ticker].iloc[0]
            st.metric("平均每股每月可領", value=f"${stock_info['等值月配息 (每股)']}")
            st.metric("目前股價", value=f"${stock_info['現價']}")

    with col2:
        # 輸入：放入多少錢
        investment_amount = st.number_input("預計投入金額 (台幣)", min_value=10000, value=100000, step=10000)
        
        if selected_ticker and stock_info['現價'] > 0:
            # 計算可買股數
            shares_can_buy = int(investment_amount / stock_info['現價'])
            # 計算每月預估領息
            monthly_income = shares_can_buy * stock_info['等值月配息 (每股)']
            
            st.divider()
            st.write(f"以現價 **{stock_info['現價']}** 元計算：")
            st.success(f"約可買進 **{shares_can_buy}** 股")
            st.info(f"預估每月可領: **NT$ {int(monthly_income):,}** 元")
