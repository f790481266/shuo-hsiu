import math
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# 本機桌面通知支援
try:
    from plyer import notification

    HAS_PLYER = True
except ImportError:
    HAS_PLYER = False

# ==========================================
# 1. 頁面基本設定
# ==========================================
st.set_page_config(
    page_title="個人資產風控與旅遊規劃儀表板", page_icon="🏦", layout="wide"
)

# 建立上方 3 個主選單分頁
tab1, tab2, tab3 = st.tabs([
    "🏦 總資產與質押風控儀表板",
    "✈️ 機票預算與哩程計算",
    "🗺️ 旅遊行程、信用卡回饋與購物清單",
])

# ==========================================
# 2. 你的真實資產與持股數據
# ==========================================
DEFAULT_PORTFOLIO = {
    "0050.TW": {"name": "元大台灣50", "cost": 97.89, "shares": 30000},  # 30張
    "006208.TW": {"name": "富邦台50", "cost": 133.03, "shares": 2000},  # 2張
    "00896.TW": {
        "name": "中信綠能及電動車",
        "cost": 25.80,
        "shares": 1000,
    },  # 1張
    "009816.TW": {
        "name": "凱基台灣TOP50",
        "cost": 15.33,
        "shares": 205000,
    },  # 205張
    "009826.TW": {
        "name": "009826",
        "cost": 10.00,
        "shares": 150000,
    },  # 150張 (單純紀錄資產)
}

LOAN_AMOUNT = 3800000  # 質押借貸金額 (380萬)
CASH_RESERVE = 800000  # 手頭預留現金防線 (80萬)
BANK_FUND_BASE = 300000  # 銀行內 0050 累積型不配息基金基準成本 (30萬)
CURRENT_MARGIN = 1.65  # 券商帳面顯示維持率 (165%)


def notify_desktop(title, message):
    """發送 Windows / Mac 電腦桌面卡片通知"""
    if HAS_PLYER:
        try:
            notification.notify(
                title=title, message=message, app_name="資產風控監控", timeout=10
            )
        except Exception:
            pass


@st.cache_data(ttl=1800)
def fetch_stock_data(ticker):
    try:
        df = yf.download(ticker, period="5y", interval="1d", progress=False)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df["MA60"] = df["Close"].rolling(window=60).mean()
        df["Bias60"] = (df["Close"] - df["MA60"]) / df["MA60"] * 100

        low_9 = df["Low"].rolling(window=9).min()
        high_9 = df["High"].rolling(window=9).max()
        rsv = (df["Close"] - low_9) / (high_9 - low_9) * 100

        k_vals, d_vals = [50.0], [50.0]
        for r in rsv.iloc[1:]:
            r_v = float(r) if not pd.isna(r) else 50.0
            new_k = (2 / 3) * k_vals[-1] + (1 / 3) * r_v
            new_d = (2 / 3) * d_vals[-1] + (1 / 3) * new_k
            k_vals.append(new_k)
            d_vals.append(new_d)

        df["K"] = k_vals
        df["D"] = d_vals
        return df
    except Exception:
        return None


# 預先計算各持股當前市值
stock_data_dict = {}
stock_market_values = {}
total_stock_market_val = 0.0
total_stock_cost_val = 0.0

for ticker, info in DEFAULT_PORTFOLIO.items():
    df = fetch_stock_data(ticker)
    stock_data_dict[ticker] = df

    if df is not None and not df.empty:
        latest_price = float(df["Close"].iloc[-1])
    else:
        latest_price = info["cost"]

    m_val = latest_price * info["shares"]
    stock_market_values[info["name"]] = m_val
    total_stock_market_val += m_val
    total_stock_cost_val += info["cost"] * info["shares"]

# 動態追蹤銀行內 0050 不配息累積型基金淨值
df_0050 = stock_data_dict.get("0050.TW")
if df_0050 is not None and not df_0050.empty:
    latest_0050_p = float(df_0050["Close"].iloc[-1])
    base_0050_p = DEFAULT_PORTFOLIO["0050.TW"]["cost"]
    fund_growth_ratio = latest_0050_p / base_0050_p
    current_bank_fund_val = BANK_FUND_BASE * fund_growth_ratio
else:
    current_bank_fund_val = BANK_FUND_BASE


# ==========================================
# 📍 TAB 1: 總資產與質押風控儀表板
# ==========================================
with tab1:
    st.title("🛡️ 全功能個人總資產、質押風控與觸底監控儀表板")
    st.caption(
        "整合持股成本、質押借貸、銀行 0050 累積型基金、實質維持率與 60 日均線觸底訊號"
    )

    st.markdown("### 💰 全局總資產統計概況")
    total_assets = (
        total_stock_market_val + CASH_RESERVE + current_bank_fund_val
    )
    net_assets = total_assets - LOAN_AMOUNT
    unrealized_profit = total_stock_market_val - total_stock_cost_val
    fund_unrealized = current_bank_fund_val - BANK_FUND_BASE

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("總資產 (包含借貸)", f"${total_assets:,.0f} 元")
    c2.metric(
        "淨資產 (扣除借貸)",
        f"${net_assets:,.0f} 元",
        f"股票未實現損益 ${unrealized_profit:+,.0f}",
    )
    c3.metric("證券總市值 (含009826)", f"${total_stock_market_val:,.0f} 元")
    c4.metric("預留現金防衛盾", f"${CASH_RESERVE:,.0f} 元", "剛性防線")
    c5.metric(
        "銀行內 0050 不配息基金",
        f"${current_bank_fund_val:,.0f} 元",
        f"即時未實現 ${fund_unrealized:+,.0f}",
    )

    st.markdown("#### 📊 資產配置精美圓餅圖")
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        macro_data = pd.DataFrame(
            {
                "資產類別": [
                    "股票證券總市值",
                    "預留現金防線",
                    "銀行0050累積型基金",
                ],
                "金額": [
                    total_stock_market_val,
                    CASH_RESERVE,
                    current_bank_fund_val,
                ],
            }
        )
        fig1 = px.pie(
            macro_data,
            names="資產類別",
            values="金額",
            title="<b>整體資產分布比例</b>",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        fig1.update_traces(
            textinfo="percent+label",
            hovertemplate="%{label}: $%{value:,.0f}元",
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col_chart2:
        if stock_market_values:
            micro_data = pd.DataFrame(
                {
                    "股票名稱": list(stock_market_values.keys()),
                    "市值": list(stock_market_values.values()),
                }
            )
            fig2 = px.pie(
                micro_data,
                names="股票名稱",
                values="市值",
                title="<b>證券庫存個股佔比 (含 009826)</b>",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig2.update_traces(
                textinfo="percent+label",
                hovertemplate="%{label}: $%{value:,.0f}元",
            )
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ------------------------------------------
    # 🎯 證券總市值單筆複利計時器與視覺化進度條
    # ------------------------------------------
    st.markdown("### 🎯 證券總市值里程碑目標計時器與進度條 (1,000萬 ~ 5,000萬)")
    st.caption(
        f"以當前【證券總市值】**${total_stock_market_val:,.0f} 元** 為單筆起算基期，Show Hand 零新增投入複利滾動"
    )

    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        st.metric(
            "單筆 Show Hand 起算基期",
            f"${total_stock_market_val:,.0f} 元",
            "證券總市值",
        )
    with col_t2:
        annual_rate = st.number_input(
            "📈 股票組合預期年化報酬率 (%)",
            min_value=1.0,
            max_value=20.0,
            value=8.0,
            step=0.5,
            help="以長期市值型與台股大盤合理複利年化報酬率 (8.0%) 推算。",
        )
    with col_t3:
        monthly_deposit = st.number_input(
            "💵 每月預計新增投入買股資金 (元)",
            min_value=0,
            max_value=1000000,
            value=0,
            step=5000,
            help="Show Hand 策略預設不再新增投入資金 ($0 元)",
        )

    # 📊 新增視覺化進度條介面
    st.markdown("#### 📈 各里程碑達成進度條")
    targets_bar = [
        ("1,000 萬元里程碑", 10000000),
        ("2,000 萬元里程碑", 20000000),
        ("3,000 萬元里程碑", 30000000),
        ("5,000 萬元里程碑", 50000000),
    ]

    for label, target_val in targets_bar:
        progress_ratio = min(
            max(total_stock_market_val / target_val, 0.0), 1.0
        )
        pct_display = progress_ratio * 100
        st.text(
            f"{label}：當前市值 ${total_stock_market_val:,.0f} / 目標 ${target_val:,.0f} ({pct_display:.1f}%)"
        )
        st.progress(progress_ratio)

    st.markdown("#### ⏳ 達標預估時間倒數表")
    targets = [10000000, 20000000, 30000000, 50000000]
    r_monthly = (annual_rate / 100) / 12

    milestone_results = []

    for target in targets:
        if total_stock_market_val >= target:
            milestone_results.append({
                "目標證券總市值": f"${target//10000:,} 萬",
                "達成狀態": "🎉 已達成！",
                "預估所需時間": "0 個月",
                "預計達成時間": "已在手中",
            })
        else:
            curr_stock_val = total_stock_market_val
            months = 0
            while curr_stock_val < target and months < 1200:
                curr_stock_val = (
                    curr_stock_val * (1 + r_monthly) + monthly_deposit
                )
                months += 1

            years_needed = months / 12.0
            milestone_results.append({
                "目標證券總市值": f"${target//10000:,} 萬",
                "達成狀態": "⌛ 進行中",
                "預估所需時間": f"約 {months} 個月",
                "預計達成時間": f"約 {years_needed:.1f} 年後",
            })

    df_milestones = pd.DataFrame(milestone_results)
    st.table(df_milestones)

    st.divider()

    st.markdown("### 🏦 股票質押借貸與防禦維護率")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("質押總借貸金額", f"${LOAN_AMOUNT:,.0f} 元", "負債槓桿 (續借不還本)")
    m2.metric("券商帳面顯示維持率", f"{CURRENT_MARGIN * 100:.0f}%", "追繳線 130%")

    collateral_val = LOAN_AMOUNT * CURRENT_MARGIN
    real_margin = (collateral_val + CASH_RESERVE) / LOAN_AMOUNT * 100
    m3.metric(
        "含現金實質維護率",
        f"{real_margin:.1f}%",
        f"+{(CASH_RESERVE/LOAN_AMOUNT)*100:.1f}% 現金保護",
    )

    drop_to_warning = (CURRENT_MARGIN - 1.30) / CURRENT_MARGIN * 100
    m4.metric("大盤安全耐受跌幅", f"{drop_to_warning:.1f}%", "距 130% 追繳預警線")

    st.divider()

    st.markdown("### 🎯 個股持股均價與 60日均線觸底檢測")
    rebound_alerts = []
    cols = st.columns(2)

    for idx, (ticker, info) in enumerate(DEFAULT_PORTFOLIO.items()):
        with cols[idx % 2]:
            st.subheader(f"{info['name']} ({ticker.replace('.TW', '')})")
            df = stock_data_dict[ticker]

            if df is None or df.empty:
                cost = info["cost"]
                p1, p2 = st.columns(2)
                p1.metric("當前紀錄單價", f"{cost:.2f} 元", "成本價")
                p2.metric(
                    "持有總張數",
                    f"{info['shares']//1000} 張",
                    "資產記錄中",
                )
                st.info(
                    "ℹ️ 該標的尚未掛牌或無即時 K 線數據，僅進行資產總額統計。"
                )
                continue

            today = df.iloc[-1]
            yesterday = df.iloc[-2]

            close_p = float(today["Close"])
            ma60_p = float(today["MA60"])
            bias = float(today["Bias60"])
            k_today, d_today = float(today["K"]), float(today["D"])
            k_yest, d_yest = float(yesterday["K"]), float(yesterday["D"])

            cost = info["cost"]
            diff_cost_pct = ((close_p - cost) / cost) * 100

            p1, p2, p3 = st.columns(3)
            p1.metric(
                "最新收盤價",
                f"{close_p:.2f} 元",
                f"較成本 {diff_cost_pct:+.2f}%",
            )
            p2.metric("你的購入均價", f"{cost:.2f} 元", "持有成本")
            p3.metric(
                "60日均線 (季線)", f"{ma60_p:.2f} 元", f"乖離率 {bias:+.2f}%"
            )

            cond_bias = bias <= -5.0
            cond_oversold = k_today < 25
            cond_cross = (k_yest < d_yest) and (k_today >= d_today)

            if cond_bias and cond_oversold and cond_cross:
                st.success(
                    "🚨 **已觸發觸底反彈訊號！** (季線負乖離 > 5% 且 KD黃金交叉)"
                )
                alert_msg = f"{info['name']} 最新價 {close_p:.2f} 元已達到觸底反彈條件！"
                rebound_alerts.append(alert_msg)
            elif bias <= -5.0:
                st.warning(
                    "⚠️ **價格修正中** (已跌破季線 5% 以上，靜待 KD 低檔黃金交叉)"
                )
            else:
                st.info("🟢 走勢正常，目前未達季線超跌點")

            chart_df = df[["Close", "MA60"]].tail(120)
            chart_df.columns = ["最新股價", "60日均線 (季線)"]
            st.line_chart(chart_df)

    if rebound_alerts:
        st.sidebar.error("🚨 偵測到觸底反彈訊號！")
        for alert in rebound_alerts:
            st.sidebar.write(f"• {alert}")
            notify_desktop("🚨 股市觸底反彈通知", alert)
    else:
        st.sidebar.success("✅ 盤面走勢溫和，未達觸底反彈買點。")


# ==========================================
# 📍 TAB 2: 高雄出發機票預算與持卡試算
# ==========================================
with tab2:
    st.title("✈️ 高雄出發 (KHH) 日本機票預估與持卡累積哩程")
    st.caption("出發日期區間：2026/12/25 ~ 2026/12/27 (聖誕跨年旺季參考檔期)")

    PRICE_TABLE = {
        "沖繩 (OKA)": {
            "台灣虎航 (LCC)": 10000,
            "中華航空": 14500,
            "長榮航空": 15000,
        },
        "名古屋 (NGO)": {
            "台灣虎航 (LCC)": 13000,
            "中華航空": 19000,
            "長榮航空": 19500,
        },
        "大阪 (KIX)": {
            "台灣虎航 (LCC)": 14500,
            "中華航空": 21000,
            "長榮航空": 21500,
        },
        "東京 (NRT)": {
            "台灣虎航 (LCC)": 15500,
            "中華航空": 22000,
            "長榮航空": 22500,
        },
    }

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        sel_dest = st.selectbox("🎯 選擇目的地航線", list(PRICE_TABLE.keys()))
    with col_f2:
        sel_airline = st.selectbox(
            "🛫 選擇航空公司", list(PRICE_TABLE[sel_dest].keys())
        )
    with col_f3:
        passengers = st.number_input(
            "👥 出遊人數 (人)", min_value=1, max_value=10, value=2
        )

    st.markdown("#### 💳 選擇你持有的信用卡試算")
    card_choice = st.radio(
        "請選擇欲刷卡說明的卡片：",
        [
            "🥇 國泰長榮極致御璽卡 ($10/哩，無上限 - 首選推薦)",
            "🥈 國泰 CUBE 卡 - 切換趣旅行 ($12/哩 或 3%無上限)",
            "🥉 匯豐輕旅卡 ($20/哩)",
        ],
        horizontal=False,
    )

    if "長榮極致御璽" in card_choice:
        mile_rate = 10
        limit_desc = "回饋無上限"
        card_name = "國泰世華長榮極致御璽卡"
        rec_reason = "長榮官網購票與海外實體刷卡均享 NT$10/哩（啟用指定倍數最優 $5/哩），哩程無上限！"
    elif "CUBE" in card_choice:
        mile_rate = 12
        limit_desc = "3% 小樹點無上限"
        card_name = "國泰世華 CUBE 卡 (趣旅行)"
        rec_reason = "海外實體與指定航空公司 3% 小樹點無上限！點數可靈活換長榮/華航哩程或直接抵帳單。"
    else:
        mile_rate = 20
        limit_desc = "無上限"
        card_name = "匯豐輕旅卡"
        rec_reason = "每滿 NT$20 累積 1 哩，作為輔助備用卡。"

    unit_price = PRICE_TABLE[sel_dest][sel_airline]
    total_flight_cost = unit_price * passengers
    est_miles = total_flight_cost // mile_rate

    st.divider()

    st.markdown(f"### 📊 刷卡建議與試算結果（搭配：{card_name}）")
    res1, res2, res3, res4 = st.columns(4)
    res1.metric("預估單人來回機票", f"${unit_price:,.0f} 元")
    res2.metric("總機票預算", f"${total_flight_cost:,.0f} 元", f"{passengers} 人")
    res3.metric("預計獲得回饋/哩程", f"{est_miles:,.0f} 哩/點", f"約 ${mile_rate}/哩")
    res4.metric("回饋上限規則", "無上限", limit_desc)

    st.success(f"💡 **評估建議：** {rec_reason}")

    st.markdown("#### 📋 2026/12/25-27 高雄出發各航線均價一覽表")
    df_prices = pd.DataFrame(PRICE_TABLE).T
    st.dataframe(df_prices.style.format("${:,.0f} 元"), use_container_width=True)


# ==========================================
# 📍 TAB 3: 旅遊行程、信用卡回饋與購物清單
# ==========================================
with tab3:
    st.title("🗺️ 2026-2027 旅遊行程規劃、信用卡回饋上限與購物清單")

    # 1. 即時日幣匯率（以台灣銀行現金賣出為基準）
    JPY_RATE = 0.1983  # 台灣銀行日圓現金賣出最新參考匯率

    st.markdown("### 💴 台灣銀行最新日圓參考匯率")
    h1, h2, h3 = st.columns(3)
    h1.metric("日圓現金賣出匯率", f"{JPY_RATE:.4f}", "台灣銀行即時標竿")
    sample_jpy = 10000
    h2.metric("10,000 日圓折合台幣", f"${sample_jpy * JPY_RATE:,.0f} 元")
    h3.metric("100,000 日圓折合台幣", f"${100000 * JPY_RATE:,.0f} 元")

    st.divider()

    # 2. 近期出國行程安排
    st.markdown("### 🗓️ 你的 5 趟預定出國行程清單")
    trips_data = [
        {"目的地": "🇰🇷 韓國", "日期區間": "2026/08/13 ~ 2026/08/17", "天數": "5 天"},
        {
            "目的地": "🇯🇵 日本岡山",
            "日期區間": "2026/10/03 ~ 2026/10/05",
            "天數": "3 天",
        },
        {
            "目的地": "🇯🇵 日本福岡",
            "日期區間": "2026/11/19 ~ 2026/11/24",
            "天數": "6 天",
        },
        {
            "目的地": "🇯🇵 日本熊本",
            "日期區間": "2027/01/09 ~ 2027/01/13",
            "天數": "5 天",
        },
        {
            "目的地": "🇯🇵 日本北海道",
            "日期區間": "2027/03/30 ~ 2027/04/03",
            "天數": "5 天",
        },
    ]
    st.table(pd.DataFrame(trips_data))

    st.divider()

    # 3. 5 張持有信用卡海外回饋與上限完整指南
    st.markdown("### 💳 5 張信用卡海外刷卡回饋與上限全解析")

    card_info_data = [
        {
            "信用卡名稱": "國泰長榮極致御璽卡",
            "海外/機票回饋": "$10/哩 (最優$5/哩)",
            "回饋上限": "無上限 👑",
            "最佳使用情境": "大額刷卡、購買長榮機票、日本在地大採購首選",
        },
        {
            "信用卡名稱": "國泰 CUBE 卡 (趣旅行)",
            "海外/機票回饋": "3% 小樹點",
            "回饋上限": "無上限 👑",
            "最佳使用情境": "海外實體商店、指定航空公司購票、彈性抵帳單",
        },
        {
            "信用卡名稱": "玉山 UNICARD",
            "海外/機票回饋": "3% ~ 4.5% (e point)",
            "回饋上限": "加碼上限 1,000~5,000點/月",
            "最佳使用情境": "切換任意選/UP選，每月刷卡額 $4萬~$14萬內最佳",
        },
        {
            "信用卡名稱": "永豐幣倍卡 (雙幣卡)",
            "海外/機票回饋": "最高 6% 現金回饋",
            "回饋上限": "精選4%加碼上限 800元/期",
            "最佳使用情境": "精選通路每月刷 NT$20,000 內拿滿 6% 高回饋",
        },
        {
            "信用卡名稱": "匯豐輕旅卡",
            "海外/機票回饋": "$20/哩",
            "回饋上限": "無上限",
            "最佳使用情境": "日常輔助累積哩程備用卡",
        },
    ]
    st.dataframe(pd.DataFrame(card_info_data), use_container_width=True)

    st.divider()

    # 4. 互動式購物清單與匯率換算器
    st.markdown("### 🛒 旅遊購物清單與即時台幣換算器")

    if "shopping_list" not in st.session_state:
        st.session_state.shopping_list = [
            {"品項": "日本藥妝/保健品", "幣別": "JPY", "預估外幣價格": 15000},
            {"品項": "韓國彩妝保養品", "幣別": "KRW", "預估外幣價格": 50000},
        ]

    c_add1, c_add2, c_add3 = st.columns(3)
    with c_add1:
        new_item = st.text_input("➕ 新增購物品項", "獺祭純米大吟釀")
    with c_add2:
        new_curr = st.selectbox("幣別", ["JPY (日圓)", "KRW (韓元)"])
    with c_add3:
        new_price = st.number_input("預估外幣單價", value=3500, step=500)

    if st.button("新增至購物清單"):
        curr_code = "JPY" if "JPY" in new_curr else "KRW"
        st.session_state.shopping_list.append(
            {"品項": "新品項", "幣別": curr_code, "預估外幣價格": new_price}
        )
        st.success("已新增至購物清單！")

    # 顯示購物清單
    if st.session_state.shopping_list:
        df_shop = pd.DataFrame(st.session_state.shopping_list)

        KRW_RATE = 0.024

        def calc_twd(row):
            if row["幣別"] == "JPY":
                return round(row["預估外幣價格"] * JPY_RATE)
            else:
                return round(row["預估外幣價格"] * KRW_RATE)

        df_shop["折合台幣 (TWD)"] = df_shop.apply(calc_twd, axis=1)

        st.markdown("#### 🛍️ 目前購物預算清單")
        st.dataframe(df_shop, use_container_width=True)

        total_twd = df_shop["折合台幣 (TWD)"].sum()
        st.metric("預算清單台幣總計", f"${total_twd:,.0f} 元")