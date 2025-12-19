import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime

# 页面配置
st.set_page_config(page_title="美股盈亏结算-专业版", layout="wide")

# --- 核心函数：获取汇率 (多源冗余) ---
@st.cache_data(ttl=3600)
def fetch_usd_cny():
    """尝试从多个公开API获取汇率"""
    urls = [
        "https://open.er-api.com/v6/latest/USD",
        "https://api.exchangerate-api.com/v4/latest/USD"
    ]
    for url in urls:
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                return res.json()['rates']['CNY']
        except:
            continue
    return 7.25  # 最终兜底汇率

# --- 核心函数：获取股价 ---
@st.cache_data(ttl=60)
def fetch_prices(tickers):
    """从 yfinance 获取最新价格"""
    try:
        # 使用 download 快速获取多个代码
        df = yf.download(tickers, period="1d", interval="1m", progress=False)
        if df.empty: return None
        
        current_prices = {}
        for t in tickers:
            # 提取最后一行有效的收盘价
            price = df['Close'][t].dropna().iloc[-1]
            current_prices[t] = price
        return current_prices
    except Exception as e:
        st.error(f"股价获取失败: {e}")
        return None

# --- UI 界面 ---
st.title("📊 个人股票持仓盈亏分析系统")
st.markdown(f"> **当前同步时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (USD/CNY 汇率每小时更新)")

# 提示栏
with st.expander("📝 填表说明 & 风险告知"):
    st.write("""
    - 数据源: yfinance (延迟 15-20 min)。
    - **RZLT**: 生物医药类，波动大。
    - **RKLX/CRWG**: 2倍杠杆 ETF，存在调仓损耗，不建议长期无视风险持有。
    - **工艺提醒**: 系统已设置 60s 缓存，频繁刷新不会立即改变数据。
    """)

# 初始数据
default_stocks = {
    "RZLT": {"name": "Rezolute", "qty": 200.0, "cost": 1.26},
    "RKLX": {"name": "2X Long RKLB", "qty": 20.33, "cost": 45.64},
    "CRWG": {"name": "2X Long CRWV", "qty": 140.0, "cost": 3.81}
}

# 输入区
st.subheader("⚙️ 参数输入")
input_data = {}
cols = st.columns(3)

for i, (ticker, info) in enumerate(default_stocks.items()):
    with cols[i]:
        st.markdown(f"**{ticker}** ({info['name']})")
        q = st.number_input("股数", value=info['qty'], key=f"q_{ticker}", format="%.2f")
        c = st.number_input("成本/股 ($)", value=info['cost'], key=f"c_{ticker}", format="%.2f")
        input_data[ticker] = {"qty": q, "cost": c}

# 动作按钮
if st.button("🔄 刷新全盘数据", type="primary", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# --- 计算逻辑 ---
prices = fetch_prices(list(default_stocks.keys()))
rate = fetch_usd_cny()

if prices:
    rows = []
    total_cost_u, total_val_u = 0, 0

    for ticker, vals in input_data.items():
        p = prices[ticker]
        cost_u = vals['qty'] * vals['cost']
        val_u = vals['qty'] * p
        profit_u = val_u - cost_u
        pct = (profit_u / cost_u * 100) if cost_u != 0 else 0
        
        total_cost_u += cost_u
        total_val_u += val_u
        
        rows.append({
            "代码": ticker,
            "现价($)": f"{p:.3f}",
            "持有量": vals['qty'],
            "成本($)": f"{vals['cost']:.2f}",
            "市值($)": round(val_u, 2),
            "市值(¥)": round(val_u * rate, 2),
            "盈亏(¥)": round(profit_u * rate, 2),
            "盈亏率": pct
        })

    # 汇总计算
    total_p_u = total_val_u - total_cost_u
    total_pct = (total_p_u / total_cost_u * 100) if total_cost_u != 0 else 0
    
    # 构建 DataFrame
    df = pd.DataFrame(rows)
    
    # 样式美化
    def style_profit(val):
        color = 'red' if val < 0 else 'green'
        icon = '▼' if val < 0 else '▲'
        return f'color: {color}; font-weight: bold;'

    # 展示汇总卡片
    c1, c2, c3 = st.columns(3)
    c1.metric("总资产 (¥)", f"{total_val_u * rate:,.2f}")
    c2.metric("总盈亏 (¥)", f"{total_p_u * rate:,.2f}", f"{total_pct:.2f}%")
    c3.metric("当前汇率", f"{rate:.4f}")

    st.subheader("📋 详细清单")
    st.dataframe(
        df.style.applymap(style_profit, subset=['盈亏(¥)', '盈亏率']),
        use_container_width=True
    )
else:
    st.warning("正在连接行情服务器，请稍候或检查网络...")

st.divider()
st.caption("Developed by Gemini for Engineering Excellence. 🛠️")
