import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import matplotlib.pyplot as plt
from matplotlib import font_manager
import random
import io

class PhoneOrder:
    def __init__(self, start_month, phone_cost, lease_rate, repayment_period, first_payment_terms, default=False):
        self.start_month = start_month
        self.phone_cost = phone_cost
        self.lease_rate = lease_rate
        self.repayment_period = repayment_period
        self.first_payment_terms = first_payment_terms
        self.default = default

        self.total_repayment = phone_cost * (1 + lease_rate)
        self.monthly_payment = self.total_repayment / repayment_period

    def get_monthly_cashflow(self):
        """返回从第 start_month 开始的回款列表（相对于整个项目周期）"""
        cashflows = [0] * (self.start_month - 1)
        if self.default:
            # 逾期订单没有任何回款
            cashflows += [0] * (self.repayment_period - self.first_payment_terms + 1)
        else:
            # 正常订单，8个月内回完9期
            repayments = [0] * (self.repayment_period - self.first_payment_terms + 1)
            repayments[0] = self.monthly_payment * self.first_payment_terms  # 第一个月两期
            for i in range(1, self.repayment_period - self.first_payment_terms + 1):
                repayments[i] = self.monthly_payment  # 后面7个月
            cashflows += repayments
        return cashflows

#混合产品租机模拟器
class MerchantSimulator3:
    def __init__(
            self,
            months=12,
            phone_cost=5000,
            lease_rate1=0.3,
            repayment_period1=9,
            first_payment_terms1=2,
            lease_rate2=0.4,
            repayment_period2=12,
            first_payment_terms2=3,
            product1_ratio=0.5,
            service_fee_rate=0,
            bad_debt_rate=0,
            monthly_order_range=(19, 20),
            investment_ratio=1.0,
            prepayment_rate=0.2
    ):
        self.months = months
        self.phone_cost = phone_cost
        self.lease_rate1 = lease_rate1
        self.repayment_period1 = repayment_period1
        self.first_payment_terms1 = first_payment_terms1
        self.lease_rate2 = lease_rate2
        self.repayment_period2 = repayment_period2
        self.first_payment_terms2 = first_payment_terms2
        self.product1_ratio = product1_ratio
        self.service_fee_rate = service_fee_rate
        self.bad_debt_rate = bad_debt_rate
        self.monthly_order_range = monthly_order_range
        self.investment_ratio = investment_ratio
        self.prepayment_rate = prepayment_rate

        self.monthly_investments = []
        self.total_cashflow = []
        self.orders = []
        self.monthly_order_count = []

    def simulate(self):
        max_months = self.months + max((self.repayment_period1 - self.first_payment_terms1), (self.repayment_period2 - self.first_payment_terms2))
        self.total_cashflow = [0] * max_months

        for month in range(1, self.months + 1):
            n_orders = random.randint(*self.monthly_order_range)
            self.monthly_order_count.append(n_orders)

            investment_this_month = 0

            for _ in range(n_orders):
                is_product1 = random.random() < self.product1_ratio

                if is_product1:
                    lease_rate = self.lease_rate1
                    repayment_period = self.repayment_period1
                    first_payment_terms = self.first_payment_terms1
                else:
                    lease_rate = self.lease_rate2
                    repayment_period = self.repayment_period2
                    first_payment_terms = self.first_payment_terms2

                adjusted_lease_rate = self.prepayment_rate * (lease_rate / 2) + (1 - self.prepayment_rate) * lease_rate
                service_fee = self.phone_cost * (1 + lease_rate) * self.service_fee_rate
                investment_per_order = (self.phone_cost + service_fee) * self.investment_ratio
                investment_this_month += investment_per_order

                order = PhoneOrder(
                    start_month=month,
                    phone_cost=self.phone_cost,
                    lease_rate=adjusted_lease_rate,
                    repayment_period=repayment_period,
                    first_payment_terms=first_payment_terms
                )
                self.orders.append(order)

                cashflow = order.get_monthly_cashflow()
                cashflow = [cf * (1 - self.bad_debt_rate) for cf in cashflow]
                for i in range(len(cashflow)):
                    self.total_cashflow[i] += cashflow[i] * self.investment_ratio

            self.monthly_investments.append(investment_this_month)
    def get_net_cashflow(self):
        net_cashflow = []
        for i in range(len(self.total_cashflow)):
            investment = self.monthly_investments[i] if i < len(self.monthly_investments) else 0
            net_cashflow.append(self.total_cashflow[i] - investment)
        return net_cashflow

    def get_cumulative_cashflow(self):
        net = self.get_net_cashflow()
        cum = []
        total = 0
        for x in net:
            total += x
            cum.append(total)
        return cum
    def get_cumulative_investment(self):
        cum = []
        total = 0
        for inv in self.monthly_investments:
            total += inv
            cum.append(total)
        # 为对齐回款月份长度，补 0
        cum += [cum[-1]] * (len(self.total_cashflow) - len(cum))
        return cum

    def get_actual_investment(self):
        cum_net = self.get_cumulative_cashflow()
        return abs(min(cum_net))
    def get_breakeven_month(self):
        cum = self.get_cumulative_cashflow()
        for i, val in enumerate(cum):
            if val >= 0:
                return i + 1  # 返回第几个月（从1开始计）
        return None


st.title("📊 租机项目盈利分析模拟器")

# 侧边栏输入参数
st.sidebar.header("📥 参数设置")

phone_cost = st.sidebar.slider("机器成本", 1000, 15000, 5000, step=100, format="%d元")
order_count = st.sidebar.slider("每月订单量", 10, 1500, 300, step=10)

# 🔸 产品1 和 产品2 还款期数
col3, col4 = st.sidebar.columns(2)
with col3:
    repayment_period1 = st.selectbox("产品1还款期数", options=list(range(8, 13)), index=1)
with col4:
    repayment_period2 = st.selectbox("产品2还款期数", options=list(range(8, 13)), index=4)

# 🔸 产品1 和 产品2 首期支付期数
col5, col6 = st.sidebar.columns(2)
with col5:
    first_payment_terms1 = st.selectbox("产品1首付期数", options=list(range(0, 5)), index=2)
with col6:
    first_payment_terms2 = st.selectbox("产品2首付期数", options=list(range(0, 5)), index=3)

# 🔸 产品1 和 产品2 租赁费率（百分比显示）
col1, col2 = st.sidebar.columns(2)
with col1:
    lease_rate1_percent = st.slider(
        "产品1租赁费率", 0, 60, 23, step=1,
        format="%.1f%%"
    )
    lease_rate1 = lease_rate1_percent / 100
with col2:
    lease_rate2_percent = st.slider(
        "产品2租赁费率", 0, 60, 30, step=1,
        format="%.1f%%"
    )
    lease_rate2 = lease_rate2_percent / 100

# 🔸 产品1 占比（百分比显示）
product1_percent = st.sidebar.slider(
    "产品1占比", 0, 100, 33, step=1,
    format="%.1f%%",
    help="产品1占比 = 产品1订单量 ÷ 总订单量；产品2占比 = 1 - 产品1占比"
)
product1_ratio = product1_percent / 100

# 🔸 坏账率（百分比显示）
bad_debt_percent = st.sidebar.slider(
    "坏账率", 0.0, 10.0, 5.0, step=0.5,
    format="%.1f%%",
    help="坏账率 = 每月逾期账款 ÷ [月订单量 × 机器成本 × (1 + 租赁费率)]"
)
bad_debt_rate = bad_debt_percent / 100

# 🔸 服务费率（百分比显示）
service_fee_percent = st.sidebar.slider(
    "服务费率", 0.0, 10.0, 2.0, step=0.1,
    format="%.1f%%",
    help="服务费率 = 机器服务费 ÷ [机器成本 × (1 + 租赁费率)]"
)
service_fee_rate = service_fee_percent / 100

# 🔸 提前还款率（百分比显示）
prepayment_percent = st.sidebar.slider(
    "提前还款率", 0.0, 50.0, 0.0, step=1.0,
    format="%.1f%%",
    help="提前还款率表示用户提前结清比例，收益按原租赁费率的一半计算"
)
prepayment_rate = prepayment_percent / 100

# 🔸 投资比例（百分比显示）
investment_percent = st.sidebar.slider(
    "投资比例", 0.0, 100.0, 100.0, step=5.0,
    format="%.0f%%"
)
investment_ratio = investment_percent / 100

# 投资时长
months = st.sidebar.slider(
    "投资月份数", 6, 24, 12, step=1,
    format="%d月",
    help="固定投资月份数，超过此月份后持续回款，但不再继续投资")




# 设置中文字体
font_path = "SourceHanSansCN-Regular.ttf"  # 字体文件路径
my_font = font_manager.FontProperties(fname=font_path)

# 点击按钮运行模拟器
if st.sidebar.button("运行模型"):

    # 初始化并运行模拟器
    simulator = MerchantSimulator3(
        months=months,
        phone_cost=phone_cost,
        lease_rate1=lease_rate1,
        lease_rate2=lease_rate2,
        repayment_period1=repayment_period1,
        repayment_period2=repayment_period2,
        first_payment_terms1=first_payment_terms1,
        first_payment_terms2=first_payment_terms2,
        product1_ratio=product1_ratio,
        service_fee_rate=service_fee_rate,
        bad_debt_rate=bad_debt_rate,
        monthly_order_range=(order_count, order_count),
        investment_ratio=investment_ratio,
        prepayment_rate=prepayment_rate
    )
    simulator.simulate()

    # 获取结果数据
    cashflow = simulator.get_cumulative_cashflow()
    net_cf = simulator.get_net_cashflow()
    # irr_monthly = npf.irr(net_cf)
    # irr_annual = (1 + irr_monthly) ** 12 - 1
    max_deficit = simulator.get_actual_investment()
    repayments = simulator.total_cashflow
    orders = simulator.monthly_order_count + [0]*max(
        simulator.repayment_period1 - simulator.first_payment_terms1,
        simulator.repayment_period2 - simulator.first_payment_terms2)
    investments = simulator.monthly_investments + [0]*max(
        simulator.repayment_period1 - simulator.first_payment_terms1,
        simulator.repayment_period2 - simulator.first_payment_terms2)
    cumulative_investments = simulator.get_cumulative_investment()
    net_cashflow = simulator.get_net_cashflow()
    cumulative_cashflow = simulator.get_cumulative_cashflow()   # 累计现金流
    breakeven = simulator.get_breakeven_month()  # 回本月份

    # 构造DataFrame表格
    df = pd.DataFrame({
        '月份': list(range(1, len(repayments)+1)),
        '订单量': orders,
        '投资金额': investments,
        '累计投资金额': cumulative_investments,
        '回款金额': repayments,
        '净现金流': net_cashflow,
        '累计净现金流': cumulative_cashflow
    })

    st.subheader("📋 每月现金流明细表")

    # 显示表格
    st.dataframe(df.style.format(precision=1), use_container_width=True, hide_index=True)

    # 导出为 Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Sheet1', index=False)

    processed_data = output.getvalue()

    # 下载按钮
    st.download_button(
        label="📥 下载表格为 Excel",
        data=processed_data,
        file_name='租机项目分析明细.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


    # 📈 绘制累计净现金流图
    st.subheader("📈 累计净现金流曲线")
    fig, ax = plt.subplots()
    months_list = list(range(1, len(cashflow)+1))
    ax.plot(months_list, [x / 10000 for x in cashflow], label="累计净现金流（万元）", linewidth=2)
    # 横坐标设置为整数月份
    ax.set_xticks(months_list)
    ax.axhline(0, linestyle='--', color='gray')
    if breakeven:
        ax.axvline(breakeven, linestyle='--', color='red', label=f"回本点：{breakeven}月")
        ax.scatter(breakeven, cashflow[breakeven-1]/10000, color='red')
    ax.set_xlabel("月份", fontproperties=my_font)
    ax.set_ylabel("现金流（万元）", fontproperties=my_font)
    ax.legend(prop=my_font)
    ax.grid(True)
    
    st.pyplot(fig)

    # 💰 显示关键指标
    st.subheader("📌 核心指标")
    st.markdown(f"""
    - 总投资月份：**{months}**
    - 每月订单量：**{order_count} 单**
    - 总订单量：**{order_count * months} 单**
    - 最大垫资：**{max_deficit / 10000:,.2f} 万元**（滚动投资下累计现金流的最小值）
    - 累计投资金额：**{max(cumulative_investments) / 10000:,.2f} 万元**（累计投资金额为设备款总投入）
    - 净利润：**{cashflow[-1] / 10000:,.2f} 万元**
    - 实际投资收益率：**{cashflow[-1]/max(cumulative_investments):.2%}**（净利润÷累计投资金额）
    - 总收益率：**{cashflow[-1] / max_deficit:.2%}**（净利润÷最大垫资）
    - 回本周期：**{breakeven} 个月**（现金流首次为正所需时间）
    """)

    def run_bad_debt_sensitivity(bad_debt_rates, fixed_params):
        results = []
        for rate in bad_debt_rates:
            sim = MerchantSimulator3(
                months=fixed_params['months'],
                phone_cost=fixed_params['phone_cost'],
                lease_rate1=fixed_params['lease_rate1'],
                repayment_period1=fixed_params['repayment_period1'],
                first_payment_terms1=fixed_params['first_payment_terms1'],
                lease_rate2=fixed_params['lease_rate2'],
                repayment_period2=fixed_params['repayment_period2'],
                first_payment_terms2=fixed_params['first_payment_terms2'],
                service_fee_rate=fixed_params['service_fee_rate'],
                bad_debt_rate=rate,
                monthly_order_range=fixed_params['monthly_order_range'],
                investment_ratio=fixed_params['investment_ratio'],
                product1_ratio=fixed_params['product1_ratio'],
                prepayment_rate=fixed_params['prepayment_rate']
            )
            sim.simulate()
            total_repayment = max(sim.get_cumulative_cashflow()) / 10_000  # 转为万元
            results.append((rate, total_repayment))
        return pd.DataFrame(results, columns=["坏账率", "回款总额（万元）"])

    st.markdown("---")
    st.header("📉 坏账率敏感性分析")

    # 设置分析参数范围
    bad_debt_range = np.linspace(0.0, 0.08, 9)

    # 固定参数（来自当前页面设置）
    fixed_params = {
        "months": months,
        "phone_cost": phone_cost,
        "lease_rate1": lease_rate1,
        "repayment_period1": repayment_period1,
        "first_payment_terms1": first_payment_terms1,
        "lease_rate2": lease_rate2,
        "repayment_period2": repayment_period2,
        "first_payment_terms2": first_payment_terms2,
        "product1_ratio": product1_ratio,
        "service_fee_rate": service_fee_rate,
        "monthly_order_range": (order_count, order_count),
        "investment_ratio": investment_ratio,
        "prepayment_rate": prepayment_rate
    }

    # 生成结果
    df_sens = run_bad_debt_sensitivity(bad_debt_range, fixed_params)
    df_sens = df_sens.sort_values("坏账率")
    delta_x = df_sens["坏账率"].iloc[0] - df_sens["坏账率"].iloc[-1]   # 坏账率变化
    delta_y = df_sens["回款总额（万元）"].iloc[0] - df_sens["回款总额（万元）"].iloc[-1]  # 回款变化
    slope = delta_y / (delta_x * 100)  # 每下降 1 个百分点带来的提升

    # 绘图：坏账率对回款金额的敏感性分析
    fig, ax = plt.subplots()
    x = df_sens["坏账率"]
    y = df_sens["回款总额（万元）"]
    ax.plot(x, y, marker='o')

    # 添加每个点的数值标签
    for i, txt in enumerate(y):
        ax.annotate(f"{txt:.1f}", (x[i], y[i]), textcoords="offset points", xytext=(0, 5), ha='center', fontsize=9)

    # 设置中文标签字体
    ax.set_xlabel("坏账率", fontproperties=my_font)
    ax.set_ylabel("回款总额（万元）", fontproperties=my_font)
    ax.set_title("坏账率对回款金额的敏感性分析", fontproperties=my_font)
    
    ax.grid(True)
    st.pyplot(fig)



    st.markdown(
        f"📌 根据当前模拟结果，坏账率每下降 1 个百分点，回款总额约提升 **{-slope:.1f} 万元**。",
        unsafe_allow_html=True
    )


# 📉 提前还款率敏感性分析
    def run_prepayment_sensitivity(prepayment_rates, fixed_params):
        results = []
        for rate in prepayment_rates:
            sim = MerchantSimulator3(
                months=fixed_params['months'],
                phone_cost=fixed_params['phone_cost'],
                lease_rate1=fixed_params['lease_rate1'],
                repayment_period1=fixed_params['repayment_period1'],
                first_payment_terms1=fixed_params['first_payment_terms1'],
                lease_rate2=fixed_params['lease_rate2'],
                repayment_period2=fixed_params['repayment_period2'],
                first_payment_terms2=fixed_params['first_payment_terms2'],
                service_fee_rate=fixed_params['service_fee_rate'],
                bad_debt_rate=fixed_params['bad_debt_rate'],
                monthly_order_range=fixed_params['monthly_order_range'],
                investment_ratio=fixed_params['investment_ratio'],
                product1_ratio=fixed_params['product1_ratio'],
                prepayment_rate=rate
            )
            sim.simulate()
            total_repayment = max(sim.get_cumulative_cashflow()) / 10_000
            results.append((rate, total_repayment))
        return pd.DataFrame(results, columns=["提前还款率", "回款总额（万元）"])


    st.markdown("---")
    st.header("📉 提前还款率敏感性分析")

    # 设置分析参数范围（0% 到 25%，步长 2.5%）
    prepayment_range = np.linspace(0.0, 0.25, 11)

    # 复用固定参数（只改变 prepayment_rate）
    fixed_params_for_prepay = {
        "months": months,
        "phone_cost": phone_cost,
        "lease_rate1": lease_rate1,
        "repayment_period1": repayment_period1,
        "first_payment_terms1": first_payment_terms1,
        "lease_rate2": lease_rate2,
        "repayment_period2": repayment_period2,
        "first_payment_terms2": first_payment_terms2,
        "product1_ratio": product1_ratio,
        "service_fee_rate": service_fee_rate,
        "bad_debt_rate": bad_debt_rate,
        "monthly_order_range": (order_count, order_count),
        "investment_ratio": investment_ratio,
    }

    # 生成结果
    df_prepay = run_prepayment_sensitivity(prepayment_range, fixed_params_for_prepay)
    df_prepay = df_prepay.sort_values("提前还款率")
    delta_x2 = df_prepay["提前还款率"].iloc[-1] - df_prepay["提前还款率"].iloc[0]
    delta_y2 = df_prepay["回款总额（万元）"].iloc[0] - df_prepay["回款总额（万元）"].iloc[-1]

    slope2 = delta_y2 / (delta_x2 * 100)

    fig2, ax2 = plt.subplots()
    x2 = df_prepay["提前还款率"]
    y2 = df_prepay["回款总额（万元）"]
    ax2.plot(x2, y2, marker='o')

    # 添加每个点的数值标签
    for i, txt in enumerate(y2):
        ax2.annotate(f"{txt:.1f}", (x2[i], y2[i]), textcoords="offset points", xytext=(0, 5), ha='center', fontsize=9)
    ax2.set_xlabel("提前还款率", fontproperties=my_font)
    ax2.set_ylabel("回款总额（万元）", fontproperties=my_font)
    ax2.set_title("提前还款率对回款金额的敏感性分析", fontproperties=my_font)
    ax2.grid(True)

    st.pyplot(fig2)

    st.markdown(
        f"📌 根据模拟结果，提前还款率每下降 1 个百分点，回款总额大约提升 **{slope2:.1f} 万元**。",
        unsafe_allow_html=True
    )


else:
    st.info("👈 请在左侧选择参数，然后点击运行模型")

#%%
