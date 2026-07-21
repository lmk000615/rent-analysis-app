import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import matplotlib.pyplot as plt
from matplotlib import font_manager
import random
import io
import time


class PhoneOrder:
    """单台手机的租机订单。

    现金流模型（押金首付 + 租金费率模式）：
        押金首付 deposit      = phone_cost × deposit_rate      （首月一次性收齐，第1月不付月供）
        应收总租金 total      = phone_cost × (1 + lease_rate)
        实收总租金 effective  = total × (1 - prepayment_loss_rate)   （提前还款损失已应用）
        月供 monthly_payment  = (effective - deposit) / (repayment_period - 1)
        第 1 月现金流 = deposit             （仅押金首付）
        后续 N-1 月    = monthly_payment
        N 期总和       = effective          （守恒，可作不变量校验）
    """

    def __init__(self, start_month, phone_cost, lease_rate, repayment_period,
                 deposit_rate, effective_total=None, default=False):
        self.start_month = start_month
        self.phone_cost = phone_cost
        self.lease_rate = lease_rate
        self.repayment_period = repayment_period
        self.deposit_rate = deposit_rate
        self.default = default

        self.deposit = phone_cost * deposit_rate
        self.total_repayment = phone_cost * (1 + lease_rate)
        self.effective_total = effective_total if effective_total is not None else self.total_repayment
        # 月供不能为负（极端情况下押金首付已超过实收总租金时兜底）
        # 第 1 月只付押金不付月供，所以月供按 (repayment_period - 1) 期分摊
        divisor = repayment_period - 1 if repayment_period > 1 else 1
        self.monthly_payment = max(0.0, (self.effective_total - self.deposit)) / divisor

    def get_monthly_cashflow(self):
        """返回从第 start_month 开始的回款列表（相对于整个项目周期）。"""
        cashflows = [0] * (self.start_month - 1)
        if self.default:
            # 坏账订单：押金首付也不收（保守口径）
            cashflows += [0] * self.repayment_period
        else:
            repayments = [0] * self.repayment_period
            repayments[0] = self.deposit  # 第1月仅收押金首付，不收月供
            for i in range(1, self.repayment_period):
                repayments[i] = self.monthly_payment
            cashflows += repayments
        return cashflows


# 押金首付 + 租金费率模式的租机模拟器
class MerchantSimulator3:
    def __init__(
            self,
            months=12,
            phone_cost=5000,
            deposit_rate=0.25,
            avg_lease_rate=0.25,
            repayment_period=9,
            prepayment_loss_rate=0.03,
            bad_debt_rate=0.05,
            service_fee_rate=0.02,
            company_fee_rate=0.0,
            monthly_order_range=(300, 300),
            investment_ratio=1.0
    ):
        self.months = months
        self.phone_cost = phone_cost
        self.deposit_rate = deposit_rate
        self.avg_lease_rate = avg_lease_rate
        self.repayment_period = repayment_period
        self.prepayment_loss_rate = prepayment_loss_rate
        self.bad_debt_rate = bad_debt_rate
        self.service_fee_rate = service_fee_rate
        self.company_fee_rate = company_fee_rate
        self.monthly_order_range = monthly_order_range
        self.investment_ratio = investment_ratio

        self.monthly_investments = []      # 月度出资金额（含服务费）
        self.monthly_company_fees = []     # 月度公司费用
        self.total_cashflow = []           # 月度总现金流（含投资、回款、费用）
        self.orders = []
        self.monthly_order_count = []

    def simulate(self):
        max_months = self.months + self.repayment_period
        self.total_cashflow = [0] * max_months

        for month in range(1, self.months + 1):
            n_orders = random.randint(*self.monthly_order_range)
            self.monthly_order_count.append(n_orders)

            investment_this_month = 0    # 含服务费的出资
            investment_device_only = 0   # 仅设备款，用于算公司费用

            for _ in range(n_orders):
                # 服务费 = 总租金 × 服务费率（保留原口径）
                service_fee = self.phone_cost * (1 + self.avg_lease_rate) * self.service_fee_rate
                investment_per_order = (self.phone_cost + service_fee) * self.investment_ratio
                investment_this_month += investment_per_order

                investment_device_only += self.phone_cost

                # 提前还款损失率：在总租金上直接打折
                effective_total = (self.phone_cost
                                   * (1 + self.avg_lease_rate)
                                   * (1 - self.prepayment_loss_rate))

                order = PhoneOrder(
                    start_month=month,
                    phone_cost=self.phone_cost,
                    lease_rate=self.avg_lease_rate,
                    repayment_period=self.repayment_period,
                    deposit_rate=self.deposit_rate,
                    effective_total=effective_total,
                    default=False
                )
                self.orders.append(order)

                cashflow = order.get_monthly_cashflow()
                # 坏账率：按月对回款打折（保留原口径）
                cashflow = [cf * (1 - self.bad_debt_rate) for cf in cashflow]
                for i in range(len(cashflow)):
                    self.total_cashflow[i] += cashflow[i] * self.investment_ratio

            # 添加投资与公司费用
            self.monthly_investments.append(investment_this_month)
            company_fee = investment_device_only * self.company_fee_rate
            self.monthly_company_fees.append(company_fee)
            self.total_cashflow[month - 1] -= company_fee  # 从现金流中扣除

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
        # 为对齐回款月份长度，补末值
        cum += [cum[-1]] * (len(self.total_cashflow) - len(cum))
        return cum

    def get_actual_investment(self):
        cum_net = self.get_cumulative_cashflow()
        return abs(min(cum_net))

    def get_breakeven_month(self):
        cum = self.get_cumulative_cashflow()
        for i, val in enumerate(cum):
            if val >= 0:
                return i + 1  # 返回第几个月（从1开始）
        return None

    def get_average_investment(self):
        """月均垫资：每月 max(0, -累计净现金流) 的算术平均。"""
        cum = self.get_cumulative_cashflow()
        deficits = [max(0, -v) for v in cum]
        if not deficits:
            return 0.0
        return sum(deficits) / len(deficits)

    def get_breakeven_bad_debt_rate(self):
        """在其他参数固定时，使净利润 = 0 的坏账率。

        用扫描法，范围 0%-30%，步长 0.5%。
        返回值约定：
            正常值：坏账率（0~0.30 之间的小数）
            -1.0   ：当前参数下任何坏账率都亏损（含 0%）
            -2.0   ：坏账率到 30% 仍盈利
        """
        rates = np.linspace(0.0, 0.30, 61)
        profits = []
        for rate in rates:
            sim = MerchantSimulator3(
                months=self.months,
                phone_cost=self.phone_cost,
                deposit_rate=self.deposit_rate,
                avg_lease_rate=self.avg_lease_rate,
                repayment_period=self.repayment_period,
                prepayment_loss_rate=self.prepayment_loss_rate,
                bad_debt_rate=rate,
                service_fee_rate=self.service_fee_rate,
                company_fee_rate=self.company_fee_rate,
                monthly_order_range=self.monthly_order_range,
                investment_ratio=self.investment_ratio
            )
            sim.simulate()
            profits.append(sim.get_cumulative_cashflow()[-1])

        if profits[0] <= 0:
            return -1.0
        if profits[-1] >= 0:
            return -2.0

        for i in range(1, len(profits)):
            if profits[i - 1] > 0 and profits[i] <= 0:
                r0, r1 = rates[i - 1], rates[i]
                p0, p1 = profits[i - 1], profits[i]
                if p0 == p1:
                    return r0
                return r0 + (0 - p0) * (r1 - r0) / (p1 - p0)
        return -2.0


# 设置密码
CORRECT_PASSWORD = "zhiliaozu26"

# 如果尚未验证通过
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.header("🔐 访问权限验证")
    password = st.text_input("请输入访问密码：", type="password")
    if password == CORRECT_PASSWORD:
        st.session_state["authenticated"] = True
        st.success("验证成功！请继续使用模拟器。")
        time.sleep(1.0)
        st.rerun()
    elif password != "":
        st.error("密码错误，请重试。")
    st.stop()


st.title("📊 知了租项目盈利分析模拟器")

# 侧边栏输入参数
st.sidebar.header("📥 参数设置")

phone_cost = st.sidebar.slider("机器成本", 1000, 15000, 5000, step=100, format="%d元")
order_count = st.sidebar.slider("每月订单量", 10, 5000, 300, step=10)

repayment_period = st.sidebar.selectbox(
    "还款期数", options=list(range(6, 16)), index=3,  # 默认 9 期
    help="每个订单的回款总期数（含押金首付月）"
)

deposit_rate_percent = st.sidebar.slider(
    "押金首付率", 10.0, 60.0, 25.0, step=1.0,
    format="%.1f%%",
    help="押金首付率 = 客户首月支付的押金首付 ÷ 零售价（零售价=机器成本）"
)
deposit_rate = deposit_rate_percent / 100

avg_lease_rate_percent = st.sidebar.slider(
    "平均租金费率", 10.0, 40.0, 25.0, step=0.5,
    format="%.1f%%",
    help="平均租金费率 = 总租金 ÷ 零售价 - 1，即零售价加价费率"
)
avg_lease_rate = avg_lease_rate_percent / 100

prepayment_loss_percent = st.sidebar.slider(
    "提前还款损失率", 1.0, 5.0, 3.0, step=0.1,
    format="%.1f%%",
    help="提前还款损失率 = 因客户提前结清损失的总租金 ÷ 应收总租金"
)
prepayment_loss_rate = prepayment_loss_percent / 100

bad_debt_percent = st.sidebar.slider(
    "坏账率", 0.0, 10.0, 5.0, step=0.1,
    format="%.1f%%",
    help="坏账率 = 总逾期账款 ÷ 总租金"
)
bad_debt_rate = bad_debt_percent / 100

service_fee_percent = st.sidebar.slider(
    "服务费率", 0.0, 10.0, 2.0, step=0.1,
    format="%.1f%%",
    help="服务费率 = 机器服务费 ÷ [机器成本 × (1 + 租赁费率)]"
)
service_fee_rate = service_fee_percent / 100

investment_percent = st.sidebar.slider(
    "投资比例", 0.0, 100.0, 100.0, step=5.0,
    format="%.0f%%"
)
investment_ratio = investment_percent / 100

months = st.sidebar.slider(
    "投资月份数", 6, 36, 12, step=1,
    format="%d月",
    help="固定投资月份数，超过此月份后持续回款，但不再继续投资"
)

company_fee_percent = st.sidebar.slider(
    "公司费用率", 0.0, 15.0, 0.0, step=0.1,
    format="%.1f%%",
    help="公司费用率 = 公司运营成本 ÷ 机器成本"
)
company_fee_rate = company_fee_percent / 100


# 设置中文字体
font_path = "SourceHanSansCN-Regular.ttf"  # 字体文件路径
my_font = font_manager.FontProperties(fname=font_path)


# 点击按钮运行模拟器
if st.sidebar.button("运行模型"):

    # 初始化并运行模拟器
    simulator = MerchantSimulator3(
        months=months,
        phone_cost=phone_cost,
        deposit_rate=deposit_rate,
        avg_lease_rate=avg_lease_rate,
        repayment_period=repayment_period,
        prepayment_loss_rate=prepayment_loss_rate,
        bad_debt_rate=bad_debt_rate,
        service_fee_rate=service_fee_rate,
        company_fee_rate=company_fee_rate,
        monthly_order_range=(order_count, order_count),
        investment_ratio=investment_ratio
    )
    simulator.simulate()

    # 获取结果数据
    cashflow = simulator.get_cumulative_cashflow()
    net_cf = simulator.get_net_cashflow()
    max_deficit = simulator.get_actual_investment()
    average_investment = simulator.get_average_investment()
    breakeven_bad_debt = simulator.get_breakeven_bad_debt_rate()

    repayments = simulator.total_cashflow
    # 对齐长度：补 repayment_period 个 0
    pad_len = simulator.repayment_period
    orders = simulator.monthly_order_count + [0] * pad_len
    investments = simulator.monthly_investments + [0] * pad_len
    cumulative_investments = simulator.get_cumulative_investment()
    monthly_company_fees = simulator.monthly_company_fees + [0] * pad_len
    net_cashflow = simulator.get_net_cashflow()
    cumulative_cashflow = simulator.get_cumulative_cashflow()
    breakeven = simulator.get_breakeven_month()

    # 统一截断/补齐到等长
    max_len = max(len(orders), len(investments), len(repayments),
                  len(cumulative_investments), len(monthly_company_fees),
                  len(net_cashflow), len(cumulative_cashflow))

    def _pad(lst, n, fill=0):
        return lst + [fill] * (n - len(lst))

    orders = _pad(orders, max_len)
    investments = _pad(investments, max_len)
    repayments = _pad(repayments, max_len)
    cumulative_investments = _pad(cumulative_investments, max_len)
    monthly_company_fees = _pad(monthly_company_fees, max_len)
    net_cashflow = _pad(net_cashflow, max_len)
    cumulative_cashflow = _pad(cumulative_cashflow, max_len)

    # 构造DataFrame表格
    df = pd.DataFrame({
        '月份': list(range(1, max_len + 1)),
        '订单量': orders,
        '投资金额': investments,
        '累计投资金额': cumulative_investments,
        '公司运行成本': monthly_company_fees,
        '回款金额': repayments,
        '净现金流': net_cashflow,
        '累计净现金流': cumulative_cashflow
    })

    st.subheader("📋 每月现金流明细表")
    st.dataframe(df.style.format(precision=1), use_container_width=True, hide_index=True)

    # 导出为 Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Sheet1', index=False)

    processed_data = output.getvalue()
    st.download_button(
        label="📥 下载表格为 Excel",
        data=processed_data,
        file_name='租机项目分析明细.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    # 📈 绘制累计净现金流图
    st.subheader("📈 累计净现金流曲线")
    fig, ax = plt.subplots()
    months_list = list(range(1, len(cashflow) + 1))
    ax.plot(months_list, [x / 10000 for x in cashflow], label="累计净现金流（万元）", linewidth=2)
    ax.set_xticks(months_list)
    ax.axhline(0, linestyle='--', color='gray')
    if breakeven:
        ax.axvline(breakeven, linestyle='--', color='red', label=f"回本点：{breakeven}月")
        ax.scatter(breakeven, cashflow[breakeven - 1] / 10000, color='red')
    ax.set_xlabel("月份", fontproperties=my_font)
    ax.set_ylabel("现金流（万元）", fontproperties=my_font)
    ax.legend(prop=my_font)
    ax.grid(True)
    st.pyplot(fig)

    # 💰 显示关键指标
    st.subheader("📌 核心指标")

    # 底线坏账率展示
    if breakeven_bad_debt == -1.0:
        breakeven_bad_debt_str = "< 0%（当前参数下任何坏账率都亏损）"
    elif breakeven_bad_debt == -2.0:
        breakeven_bad_debt_str = "> 30%（当前参数下坏账率到 30% 仍盈利）"
    else:
        breakeven_bad_debt_str = f"{breakeven_bad_debt * 100:.1f}%"

    # 平均资金投资收益率
    if average_investment > 0:
        avg_return_rate = cashflow[-1] / average_investment
        avg_return_str = f"{avg_return_rate:.2%}"
    else:
        avg_return_str = "N/A（无垫资）"

    st.markdown(f"""
    - 总投资月份：**{months}**
    - 每月订单量：**{order_count} 单**
    - 总订单量：**{order_count * months} 单**
    - 最大垫资：**{max_deficit / 10000:,.2f} 万元**（滚动投资下累计现金流的最小值）
    - 累计投资金额：**{max(cumulative_investments) / 10000:,.2f} 万元**（累计投资金额为设备款总投入）
    - 月均垫资：**{average_investment / 10000:,.2f} 万元**（每月 max(0, -累计净现金流) 的算术平均）
    - 净利润：**{cashflow[-1] / 10000:,.2f} 万元**
    - 实际投资收益率：**{cashflow[-1] / max(cumulative_investments):.2%}**（净利润÷累计投资金额）
    - 总收益率：**{cashflow[-1] / max_deficit:.2%}**（净利润÷最大垫资）
    - **平均资金投资收益率**：**{avg_return_str}**（净利润÷月均垫资）
    - **底线坏账率**：**{breakeven_bad_debt_str}**（其他参数固定时使净利润归零的坏账率）
    - 回本周期：**{breakeven} 个月**（现金流首次为正所需时间）

    注：本模型测算结果不包含公司运营成本、人工成本、税费以及资金成本等其他费用，仅供参考。
    """)

    # ---------- 敏感性分析（通用扫描 + 绘图） ----------

    base_params = {
        'months': months,
        'phone_cost': phone_cost,
        'deposit_rate': deposit_rate,
        'avg_lease_rate': avg_lease_rate,
        'repayment_period': repayment_period,
        'prepayment_loss_rate': prepayment_loss_rate,
        'bad_debt_rate': bad_debt_rate,
        'service_fee_rate': service_fee_rate,
        'company_fee_rate': company_fee_rate,
        'monthly_order_range': (order_count, order_count),
        'investment_ratio': investment_ratio
    }

    def run_sensitivity(vary_param, values, base):
        """扫描 vary_param 在 values 列表中的取值，返回 DataFrame。"""
        col_name = {
            'bad_debt_rate': '坏账率',
            'prepayment_loss_rate': '提前还款损失率',
            'deposit_rate': '押金首付率',
            'avg_lease_rate': '平均租金费率'
        }[vary_param]
        results = []
        for v in values:
            params = dict(base)
            params[vary_param] = v
            sim = MerchantSimulator3(**params)
            sim.simulate()
            profit = sim.get_cumulative_cashflow()[-1] / 10000  # 万元
            results.append((v, profit))
        return pd.DataFrame(results, columns=[col_name, '净利润（万元）'])

    def plot_sensitivity(df_sens, current_value, title, x_label):
        x = df_sens.iloc[:, 0]
        y = df_sens['净利润（万元）']
        fig, ax = plt.subplots()
        ax.plot(x, y, marker='o', label="模拟结果", color='steelblue')
        for i in range(len(y)):
            ax.annotate(f"{y.iloc[i]:.1f}", (x.iloc[i], y.iloc[i]),
                        textcoords='offset points', xytext=(0, 5),
                        ha='center', fontsize=9)
        # 当前模型红点（线性插值）
        current_y = float(np.interp(current_value, x, y))
        ax.scatter(current_value, current_y, color='red', s=80, zorder=5, label="当前模型")
        ax.annotate(f"{current_y:.1f}", (current_value, current_y),
                    textcoords='offset points', xytext=(0, -12),
                    ha='center', fontsize=9, color='red')
        ax.set_xlabel(x_label, fontproperties=my_font)
        ax.set_ylabel("净利润（万元）", fontproperties=my_font)
        ax.set_title(title, fontproperties=my_font)
        ax.grid(True)
        ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5), prop=my_font)
        return fig

    # 1. 坏账率敏感性
    st.markdown("---")
    st.header("📉 坏账率敏感性分析")
    df_bad = run_sensitivity('bad_debt_rate', np.linspace(0.0, 0.10, 11), base_params)
    st.pyplot(plot_sensitivity(df_bad, bad_debt_rate, "坏账率对净利润的影响", "坏账率"))

    # 2. 提前还款损失率敏感性
    st.markdown("---")
    st.header("📉 提前还款损失率敏感性分析")
    df_prepay = run_sensitivity('prepayment_loss_rate', np.linspace(0.0, 0.08, 9), base_params)
    st.pyplot(plot_sensitivity(df_prepay, prepayment_loss_rate,
                               "提前还款损失率对净利润的影响", "提前还款损失率"))

    # 3. 平均租金费率敏感性
    st.markdown("---")
    st.header("📉 平均租金费率敏感性分析")
    df_lease = run_sensitivity('avg_lease_rate', np.linspace(0.15, 0.35, 11), base_params)
    st.pyplot(plot_sensitivity(df_lease, avg_lease_rate,
                               "平均租金费率对净利润的影响", "平均租金费率"))

else:
    st.info("👈 请在左侧选择参数，然后点击运行模型")
