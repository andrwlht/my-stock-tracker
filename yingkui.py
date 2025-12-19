import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# --- 1. 持仓配置区 ---
PORTFOLIO = [
    {"ticker": "RZLT", "qty": 200.0, "cost": 1.26},
    {"ticker": "RKLX", "qty": 20.33, "cost": 45.64},
    {"ticker": "CRWG", "qty": 140.0, "cost": 3.81},
]

@st.cache_data(ttl=60)
def get_usd_cny():
    try:
        res = requests.get("https://open.er-api.com/v6/latest/USD", timeout=5)
        return res.json()['rates']['CNY']
    except:
        return 7.25

@st.cache_data(ttl=60)
def fetch_prices(tickers):
    """采用更稳健的方法获取价格"""
    if not tickers: return {}
    prices = {}
    try:
        # 逐个获取以确保稳定性，特别是对于杠杆ETF
        for t in tickers:
            ticker_obj = yf.Ticker(t)
            # 尝试获取最新价格（先尝试快照数据，再尝试历史数据）
            hist = ticker_obj.history(period="1d")
            if not hist.empty:
                prices[t] = hist['Close'].iloc[-1]
            else:
                # 备选方案：获取实时价格快照
                info = ticker_obj.fast_info
                if 'last_price' in info:
                    prices[t] = info['last_price']
        return prices
    except Exception as e:
        st.error(f"行情接口异常: {e}")
        return {}

# --- 3. 界面展示 ---
st.set_page_config(page_title="美股持仓监控", layout="wide")
st.title("📊 我的美股持仓监控 (USD → CNY)")

rate = get_usd_cny()
tickers_list = [item['ticker'] for item in PORTFOLIO]
prices = fetch_prices(tickers_list)

# 调试辅助：如果你发现不显示，取消下面这行的注释可以看到后台抓到了哪些代码
# st.write(f"调试信息 - 已获取到的价格: {prices}")

if prices:
    rows = []
    total_cost_usd = 0
    total_value_usd = 0

    for item in PORTFOLIO:
        t = item['ticker']
        # 增强容错：如果获取不到价格，给一个提示而不是直接跳过
        if t not in prices:
            st.warning(f"无法获取 {t} 的实时价格，请确认该股当前是否有交易量。")
            continue
        
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

    if rows:
        total_profit_usd = total_value_usd - total_cost_usd
        total_profit_pct = (total_profit_usd / total_cost_usd * 100) if total_cost_usd != 0 else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("总资产 (¥)", f"¥{total_value_usd * rate:,.2f}")
        c2.metric("总盈亏 (¥)", f"¥{total_profit_usd * rate:,.2f}", f"{total_profit_pct:.2f}%")
        c3.metric("实时汇率", f"{rate:.4f}")

        df = pd.DataFrame(rows)
        st.subheader("📋 详细持仓清单")
        
        def color_profit(val):
            if isinstance(val, (int, float)):
                return f"color: {'#ff4b4b' if val < 0 else '#00cc66'}"
            return ""

        st.dataframe(
            df.style.applymap(color_profit, subset=['盈亏(¥)', '盈亏率(%)']),
            use_container_width=True
        )
    else:
        st.error("所有持仓代码均无法获取价格。")
else:
    st.warning("行情获取中，请稍后...")

if st.button("🔄 强制刷新"):
    st.cache_data.clear()
    st.rerun()
