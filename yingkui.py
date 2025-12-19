import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# --- 1. 你的持仓配置区 (在这里修改数据) ---
# 工程师提示：增加新股票只需按照格式新增一行即可
PORTFOLIO = [
    {"ticker": "RZLT", "qty": 200.0, "cost": 1.26},
    {"ticker": "RKLX", "qty": 20.33, "cost": 45.64},
    {"ticker": "CRWG", "qty": 140.0, "cost": 3.81},
    # {"ticker": "TSLA", "qty": 10.0, "cost": 250.0}, # 以后想加股票就这样取消注释
]

# --- 2. 核心功能函数 ---
@st.cache_data(ttl=60)
def get_usd_cny():
    """获取实时汇率，带备选方案"""
    try:
        res = requests.get("https://open.er-api.com/v6/latest/USD", timeout=5)
        return res.json()['rates']['CNY']
    except:
        return 7.15 # 极端情况下的保底汇率

@st.cache_data(ttl=60)
def fetch_prices(tickers):
    """批量获取最新的美股价格"""
    if not tickers: return {}
    try:
        # yfinance 批量下载
        data = yf.download(tickers, period="1d", interval="1m", progress=False)
        if data.empty: return {}
        
        prices = {}
        for t in tickers:
            try:
                # 兼容单只股票和多只股票返回的 DataFrame 结构
                if len(tickers) == 1:
                    price = data['Close'].iloc[-1]
                else:
                    price = data['Close'][t].dropna().iloc[-1]
                prices[t] = price
            except: continue
        return prices
    except Exception as e:
        st.error(f"行情获取失败: {e}")
        return {}

# --- 3. 界面展示 ---
st.set_page_config(page_title="美股持仓监控", layout="wide")
st.title("📊 我的美股持仓监控 (USD → CNY)")

rate = get_usd_cny()
tickers = [item['ticker'] for item in PORTFOLIO]
prices = fetch_realtime_prices(tickers) # 内部已做缓存

if prices:
    rows = []
    total_cost_usd = 0
    total_value_usd = 0

    for item in PORTFOLIO:
        t = item['ticker']
        if t not in prices: continue
        
        cur_p = prices[t]
        qty = item['qty']
        cost_p = item['cost']
        
        c_usd = qty * cost_p
        v_usd = qty * cur_p
        p_usd = v_usd - c_usd
        p_pct = (p_usd / c_usd * 100) if c_usd != 0 else 0
        
        total_cost_usd += c_usd
        total_value_usd += v_usd
        
        rows.append({
            "代码": t,
            "现价($)": f"{cur_p:.3f}",
            "股数": qty,
            "成本/股": f"{cost_p:.2f}",
            "市值(¥)": round(v_usd * rate, 2),
            "盈亏(¥)": round(p_usd * rate, 2),
            "盈亏率(%)": round(p_pct, 2)
        })

    # 计算总体数据
    total_profit_usd = total_value_usd - total_cost_usd
    total_profit_pct = (total_profit_usd / total_cost_usd * 100) if total_cost_usd != 0 else 0

    # 顶部数据卡片
    c1, c2, c3 = st.columns(3)
    c1.metric("总市值 (人民币)", f"¥{total_value_usd * rate:,.2f}")
    c2.metric("总盈亏 (人民币)", f"¥{total_profit_usd * rate:,.2f}", f"{total_profit_pct:.2f}%")
    c3.metric("实时汇率 (USD/CNY)", f"{rate:.4f}")

    # 详细表格
    df = pd.DataFrame(rows)
    st.subheader("📋 详细持仓清单")
    
    def color_profit(val):
        if isinstance(val, (int, float)):
            return f"color: {'#ff4b4b' if val < 0 else '#00cc66'}"
        return ""

    st.dataframe(
        df.style.applymap(color_profit, subset=['盈亏(¥)', '盈亏率(%)']),
        use_container_width=True,
        height=(len(PORTFOLIO) + 1) * 35 + 40
    )
else:
    st.warning("正在等待行情数据刷新...")

if st.button("🔄 立即刷新数据"):
    st.cache_data.clear()
    st.rerun()

st.divider()
st.caption("注：数据每60秒自动缓存刷新一次。如需永久修改持仓，请直接编辑 GitHub 源码中的 PORTFOLIO 列表。")
