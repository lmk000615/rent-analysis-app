# CLAUDE.md — Claude Code 工作约定

本文件给 Claude Code（或任何 AI 编程助手）看，用于理解项目约定、避免破坏性修改。

## 项目本质

- 这是**单文件 Streamlit 应用**，整个逻辑都在 `app.py` 里。
- **禁止**为了"代码整洁"拆分 `app.py` 成多文件。如果要拆，必须先和用户讨论。
- 项目没有任何测试框架、没有任何 lint 配置。验证主要靠：启动 streamlit + 手工核对公式。

## 核心类职责

### `PhoneOrder`（单台手机订单）

- 输入：`start_month`、`phone_cost`、`lease_rate`、`repayment_period`、`deposit_rate`、`default`。
- 计算并缓存：`total_repayment`、`monthly_payment`、`deposit`。
- 核心方法 `get_monthly_cashflow()`：返回从 `start_month` 开始的回款列表（长度 = `repayment_period`）。
- **公式**：
  - `deposit = phone_cost × deposit_rate`
  - `total_repayment = phone_cost × (1 + lease_rate)`
  - `monthly_payment = (total_repayment - deposit) / repayment_period`
  - 第 1 月 = `deposit + monthly_payment`，后续每月 = `monthly_payment`

### `MerchantSimulator3`（模拟器主体）

- 输入：业务参数集（详见 README 参数表）。
- 核心方法：
  - `simulate()`：执行模拟，填充 `total_cashflow`、`monthly_investments`、`monthly_company_fees`。
  - `get_net_cashflow()`：每月（回款 - 投资）。
  - `get_cumulative_cashflow()`：累计净现金流。
  - `get_cumulative_investment()`：累计投资金额。
  - `get_actual_investment()`：最大垫资 = `abs(min(cumulative_cashflow))`。
  - `get_breakeven_month()`：累计净现金流首次 ≥ 0 的月份。
  - `get_average_investment()`：月均垫资 = `mean(max(0, -月度累计净现金流))`。
  - `get_breakeven_bad_debt_rate()`：在其他参数固定时，使净利润 = 0 的坏账率。

## 修改规则（强制）

### 1. 改公式前必须先验证小数据

涉及 `PhoneOrder` 或 `MerchantSimulator3` 的现金流逻辑修改，必须先用最小规模（如 `months=1, order_count=1`）打印 `total_cashflow`，肉眼比对每一项。**禁止**直接调大规模（`order_count=300`）跑完整模拟来"验证"。

### 2. 改参数体系前必须复述确认

涉及侧边栏 slider 的增删改，必须先把"新参数表 + 受影响的代码段"以文字形式复述给用户，等确认后再动。

### 3. 密码模块不要动

`CORRECT_PASSWORD` 及验证逻辑（app.py 顶部）是访问控制，**禁止**为了"快速测试"注释掉或绕过。

### 4. 字体依赖

matplotlib 中文显示依赖 `SourceHanSansCN-Regular.ttf`，文件必须与 `app.py` 同目录。`font_path` 是相对路径，依赖工作目录——**禁止**改成绝对路径。

### 5. 涉及删除/大规模移动必须先确认

删除文件、批量重命名、跨目录移动等操作，必须先请求用户确认。

## 模拟器内部逻辑要点

### 提前还款损失率

- **旧定义**（已废弃）：按订单比例近似 `adjusted_lease_rate = prepayment_rate × (lease_rate / 2) + (1 - prepayment_rate) × lease_rate`。
- **新定义**：直接按"总租金损失率"，即 `effective_total = total_repayment × (1 - prepayment_loss_rate)`。
- 修改时不要混淆两种定义。

### 坏账处理

按月对回款打折：`monthly_cashflow × (1 - bad_debt_rate)`。这是简化模型，不是按订单级别判定逾期。

### 公司费用

按月扣除，扣的是设备款投资 × 公司费用率（不是回款 × 费用率）。

### 底线坏账率算法

扫描法：坏账率从 0% 扫到 20%（步长 0.5%），找净利润由正转负的临界点。若全为正返回 ">20%"，若全为负返回 "<0%"。**禁止**用二分法替代（除非确认净利润随坏账率严格单调）。

## 验证流程

任何修改完成后，必须执行：

1. **小数据 assert**（Python REPL）：
   ```python
   from app import PhoneOrder
   o = PhoneOrder(start_month=1, phone_cost=5000, lease_rate=0.25,
                  repayment_period=9, deposit_rate=0.2)
   cf = o.get_monthly_cashflow()
   assert len(cf) == 9
   assert abs(cf[0] - 1583.33) < 0.01
   assert abs(sum(cf) - 6250) < 0.01
   ```

2. **streamlit 启动**：
   ```bash
   streamlit run app.py
   ```
   输入密码，调一组参数，点击「运行模型」，目测所有图表正常。

3. **公式核对**：手工算一组小数据（押金首付、月供、第1月、总和），与程序输出比对。

## 不要做的事

- ❌ 拆分 `app.py` 成多文件（除非用户明确要求）
- ❌ 引入测试框架（pytest/unittest）—— 项目刻意保持简洁
- ❌ 引入数据库、缓存、外部 API
- ❌ 改密码模块
- ❌ 改字体文件 / 改 `font_path` 为绝对路径
- ❌ 删除 Excel 导出 / 累计净现金流图 / 回本点标注
- ❌ `git push --force` 或 `git reset --hard`
- ❌ `pip install` 重装依赖（先判断是代码/环境/网络/配置问题）

## 当前进度（2026-07-20 更新）

模型已完成从"9付2/12付3"模式到"押金首付率 + 平均租金费率"模式的重构：
- 移除产品1/产品2 双产品结构
- 提前还款改为总租金损失率（1%-5%）
- 新增底线坏账率输出
- 新增平均资金投资收益率
- 月订单量上限从 3000 提升到 5000
