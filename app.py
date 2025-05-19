import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import matplotlib.pyplot as plt
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

class MerchantSimulator:
    def __init__(
            self,
            months=12,
            phone_cost=5000,
            lease_rate=0.3,
            repayment_period=9,
            first_payment_terms=2,
            service_fee_rate=0,
            bad_debt_rate=0,
            monthly_order_range=(19, 20)
    ):
        """
        初始化商户模拟器。

        参数说明：
        - months: 模拟的月数（例如12个月）
        - phone_cost: 每部手机的成本
        - lease_rate: 租赁利率，例如0.3表示总租金为成本的130%
        - repayment_period: 总的还款期数（例如9期）
        - first_payment_terms: 首月支付的期数（例如2期）
        - service_fee_rate: 服务费比例（以总租金为基准）
        - bad_debt_rate: 坏账率（0.02表示2%订单无法收回）
        - monthly_order_range: 每月订单范围（随机生成），例如(15, 20)
        """
        self.months = months
        self.phone_cost = phone_cost
        self.lease_rate = lease_rate
        self.repayment_period = repayment_period
        self.first_payment_terms = first_payment_terms
        self.service_fee_rate = service_fee_rate
        self.bad_debt_rate = bad_debt_rate
        self.monthly_order_range = monthly_order_range

        # 存储每月投资金额和订单对象列表
        self.monthly_investments = []
        self.orders = []
        self.monthly_order_count = []

    def simulate(self):
        """
        运行模拟过程：为每个月生成订单、计算投资、回款，并记录总现金流。
        """
        max_months = self.months + self.repayment_period - self.first_payment_terms  # 由于最长回款周期为8个月，最晚投资其实月份为最后一个月开始，故+7
        self.total_cashflow = [0] * max_months

        for month in range(1, self.months + 1): #month变量从1开始，遍历到12，所以是range(1, 13)
            # 随机生成订单数量
            n_orders = random.randint(*self.monthly_order_range)

            # 记录每月订单数量
            self.monthly_order_count.append(n_orders)

            # 每个订单服务费 = 总租金 * 3%
            service_fee_per_order = self.phone_cost * (1 + self.lease_rate) * self.service_fee_rate

            # 每个订单的投资金额 = 手机成本 + 服务费
            investment_per_order = self.phone_cost + service_fee_per_order
            investment_this_month = n_orders * investment_per_order
            self.monthly_investments.append(investment_this_month)

            for _ in range(n_orders):
                is_default = random.random() < self.bad_debt_rate  # 是否坏账，random.random() 生成一个在0到1之间的随机浮点数

                order = PhoneOrder(
                    start_month=month,
                    phone_cost=self.phone_cost,
                    lease_rate=self.lease_rate,
                    repayment_period=self.repayment_period,
                    first_payment_terms=self.first_payment_terms,
                    default=is_default
                )
                self.orders.append(order)

                # 获取该订单的现金流，并加总到总体现金流
                cashflow = order.get_monthly_cashflow()
                # print(cashflow)
                for i in range(len(cashflow)):
                    # if month + i < len(self.total_cashflow):
                    self.total_cashflow[i] += cashflow[i]
                    # print(self.total_cashflow)


    def get_net_cashflow(self):
        """
        计算每月净现金流（回款 - 投资）
        """
        net_cashflow = []
        for i in range(len(self.total_cashflow)):
            investment = self.monthly_investments[i] if i < len(self.monthly_investments) else 0
            net_cashflow.append(self.total_cashflow[i] - investment)
        return net_cashflow

    def get_cumulative_cashflow(self):
        """
        返回累计现金流
        """
        net = self.get_net_cashflow()
        cum = []
        total = 0
        for x in net:
            total += x
            cum.append(total)
        return cum

    def get_breakeven_month(self):
        """
        返回回本的月份（累计现金流转正）
        """
        cum = self.get_cumulative_cashflow()
        for i, val in enumerate(cum):
            if val >= 0:
                return i + 1  # 返回第几个月（从1开始计）
        return None  # 模拟期内未回本

    def get_cumulative_investment(self):
        """
        返回累计投资金额列表
        """
        cum = []
        total = 0
        for inv in self.monthly_investments:
            total += inv
            cum.append(total)
        # 为对齐回款月份长度，补 0
        cum += [cum[-1]] * (len(self.total_cashflow) - len(cum))
        return cum

    def get_actual_investment(self):
        """
        返回项目期间实际最大垫资金额（累计净现金流的最大负值）
        """
        cum_net = self.get_cumulative_cashflow()
        return abs(min(cum_net))  # 最大的负值的绝对值
    def estimate_steady_net_cashflow(self):
        """
        估算稳定期每月净现金流（基于理论公式）
        公式：订单数 × 成本 × [ (1 + 费率) × (1 - 坏账率 - 服务费率) - 1 ]
        """
        avg_orders = sum(self.monthly_order_range) / 2
        C = self.phone_cost
        r = self.lease_rate
        d = self.bad_debt_rate
        f = self.service_fee_rate

        monthly_net_cashflow = avg_orders * C * ((1 + r) * (1 - d - f) - 1)
        return monthly_net_cashflow



# 页面标题
st.title("📊 租机项目盈利分析模拟器")

# 侧边栏输入参数
st.sidebar.header("📥 参数设置")

phone_cost = st.sidebar.slider("机器成本", 1000, 15000, 5000, step=100)
order_count = st.sidebar.slider("每月订单量", 10, 1500, 300, step=10)
lease_rate = st.sidebar.slider("租赁费率", 0.0, 0.6, 0.3, step=0.01)
bad_debt_rate = st.sidebar.slider("坏账率", 0.0, 0.1, 0.05, step=0.01)
service_fee_rate = st.sidebar.slider("服务费率", 0.0, 0.1, 0.02, step=0.01)
repayment_period = st.sidebar.slider("还款期数", 8, 12, 9, step=1)
first_payment_terms = st.sidebar.slider("首期支付期数", 0, 4, 2, step=1)
months = st.sidebar.slider("投资月份数", 6, 24, 12, step=1)

# 设置中文字体（如使用 SimHei）
plt.rcParams['font.sans-serif'] = ['SimHei']  # 或 'Microsoft YaHei'
plt.rcParams['axes.unicode_minus'] = False    # 正确显示负号

# 点击按钮运行模拟器
if st.sidebar.button("运行模型"):

    # 初始化并运行模拟器
    simulator = MerchantSimulator(
        months=months,
        phone_cost=phone_cost,
        lease_rate=lease_rate,
        repayment_period=repayment_period,
        first_payment_terms=first_payment_terms,
        service_fee_rate=service_fee_rate,
        bad_debt_rate=bad_debt_rate,
        monthly_order_range=(order_count, order_count)
    )
    simulator.simulate()

    # 获取结果数据
    cashflow = simulator.get_cumulative_cashflow()
    net_cf = simulator.get_net_cashflow()
    irr_monthly = npf.irr(net_cf)
    irr_annual = (1 + irr_monthly) ** 12 - 1
    max_deficit = simulator.get_actual_investment()
    breakeven = simulator.get_breakeven_month()

    repayments = simulator.total_cashflow
    orders = simulator.monthly_order_count + [0]*(simulator.repayment_period - simulator.first_payment_terms)
    investments = simulator.monthly_investments + [0]*(simulator.repayment_period - simulator.first_payment_terms)
    cumulative_investments = simulator.get_cumulative_investment()
    net_cashflow = simulator.get_net_cashflow()
    cumulative_cashflow = simulator.get_cumulative_cashflow()   # 累计现金流
    actual_investment = simulator.get_actual_investment()

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
    st.dataframe(df.style.format(precision=1), use_container_width=True)

    # 导出为 Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Sheet1', index=False)
        writer.save()
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
    ax.set_xlabel("月份")
    ax.set_ylabel("现金流（万元）")
    ax.grid(True)
    ax.legend()
    st.pyplot(fig)

    # 💰 显示关键指标
    st.subheader("📌 核心指标")
    st.markdown(f"""
    - 总投资月份：**{months}**
    - 每月订单量：**{order_count} 单**
    - 总订单量：**{order_count * months} 单**
    - 最大垫资：**{max_deficit / 10000:,.2f} 万元**
    - 总回款金额：**{max(cashflow) / 10000:,.2f} 万元**
    - 总收益率：**{max(cashflow) / max_deficit:.2%}**
    - 平稳期月度净现金流：**{simulator.estimate_steady_net_cashflow() / 10000:.2f} 万元**
    - 回本周期：**{breakeven} 个月**
    - IRR（月度）：**{irr_monthly:.2%}**
    - IRR（年化）：**{irr_annual:.2%}**
    """)

    def run_bad_debt_sensitivity(bad_debt_rates, fixed_params):
        results = []
        for rate in bad_debt_rates:
            sim = MerchantSimulator(
                months=fixed_params['months'],
                phone_cost=fixed_params['phone_cost'],
                lease_rate=fixed_params['lease_rate'],
                repayment_period=fixed_params['repayment_period'],
                first_payment_terms=fixed_params['first_payment_terms'],
                service_fee_rate=fixed_params['service_fee_rate'],
                bad_debt_rate=rate,
                monthly_order_range=fixed_params['monthly_order_range']
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
        "lease_rate": lease_rate,
        "repayment_period": repayment_period,
        "first_payment_terms": first_payment_terms,
        "service_fee_rate": service_fee_rate,
        "monthly_order_range": (order_count, order_count)
    }

    # 生成结果
    df_sens = run_bad_debt_sensitivity(bad_debt_range, fixed_params)

    # 绘图
    fig, ax = plt.subplots()
    ax.plot(df_sens["坏账率"], df_sens["回款总额（万元）"], marker='o')
    ax.set_xlabel("坏账率")
    ax.set_ylabel("回款总额（万元）")
    ax.set_title("坏账率对回款金额的敏感性分析")
    ax.grid(True)

    st.pyplot(fig)

else:
    st.info("👈 请在左侧选择参数，然后点击运行")
