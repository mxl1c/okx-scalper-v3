# okx-scalper-v3 策略说明书（签名脚手架）

**策略 ID：** `okx-scalper-v3`  
**规格版本：** `3.0.0`  
**执行范围：** 仅离线分类 / 几何 / 风控门评估。本仓库 **不下真实订单**，不调用 OKX 下单 API。

本文与 `RISK.md`、`okx_scalper_v3.hard_gates` 构成同一份签名合同。软参只能在分析师边界内调节，**不能**改写硬门。

---

## 1. 市场状态机：chaos → trend → range

分类优先级固定为：

1. **chaos**（先判）
2. **trend**（再判，拆成 `trend_up` / `trend_down`）
3. **range**（其余）

混沌一旦成立，即使斜率很大也不得改判为趋势。

**chaos = 只禁止新开仓，不是 flatten-all，也不是强平已有仓。** 已开仓继续走各自的 SL / TP / giveback，本脚手架不因 chaos 发出平仓指令。见 `RISK.md`。

| 状态 | 含义 | 新开仓 | 已有仓 |
| --- | --- | --- | --- |
| `chaos` | 波动扩张且方向效率差，或 ATR% 越过混沌阈值 | 禁止 | **不** flatten-all / 不强平 |
| `trend_up` | 非混沌，效率与斜率同时达标，斜率为正 | 允许（过硬门后） | 不因 regime 强平 |
| `trend_down` | 同上，斜率为负 | 允许（过硬门后） | 不因 regime 强平 |
| `range` | 非混沌且未达趋势门槛 | 允许（过硬门后） | 不因 regime 强平 |

### 1.1 特征窗口（签名）

- 周期：`5m`
- 回看：`N = 48`（4 小时）
- 特征五元组（必须同时产出，写入离线标签）：

| 字段 | 定义 |
| --- | --- |
| `atr_pct` | 窗口内 ATR（默认周期 14，软参）÷ 最新收盘价 |
| `width` | （窗口最高 − 窗口最低）÷ 最新收盘价 |
| `slope` | 收盘价 OLS 斜率（每根 K）÷ 最新收盘价 |
| `eff` | Kaufman 效率：`|close[-1] − close[-N]| / Σ|Δclose|` |
| `brk` | 最新收盘相对 **前 N−1 根** 高低的突破幅度 ÷ 收盘；未突破为 0；向下为负 |

`N` 与周期不是软参。传入其它窗口直接拒绝。

### 1.2 默认判定（软参，受分析师边界约束）

- **chaos** 若以下任一成立：
  - `atr_pct >= chaos_atr_pct`
  - `eff <= chaos_eff_max` **且** `width >= chaos_width_min`
- **trend_*** 若非 chaos 且：
  - `eff >= trend_eff_min` **且** `|slope| >= trend_slope_min`
  - `slope >= 0 → trend_up`，否则 `trend_down`
- 否则 **range**

`range_width_max` 仅作研究标注与软参边界，不参与硬门。

数值边界见 RISK §软参。STRATEGY 不重复抄写上下限，以免与 RISK 漂移。

---

## 2. 拒绝带（reject zones）与原因码

任何候选单只返回 **一个主原因码**。通过则为 `OK`。

### 2.1 开仓拒绝带

| 原因码 | 触发带 |
| --- | --- |
| `REJECT_CHAOS` | 当前 regime = chaos，禁止新开 |
| `REJECT_PARALLEL` | 已开仓数量 ≥ 3，第 4 笔拒绝 |
| `REJECT_PER_TRADE_RISK` | 本笔账户风险 > 2% |
| `REJECT_AGGREGATE_RISK` | 已开风险 + 本笔风险 > 5% |
| `REJECT_DAILY_LOSS` | 当日亏损 ≥ 5%（无豁免） |
| `REJECT_MIN_RR` | `rr < 1.5` |
| `REJECT_CHASE` | 追价：多头 `entry > signal_price` 或空头 `entry < signal_price` |
| `REJECT_SL_FLOOR` | `sl_pct < 1.2%` |
| `REJECT_COOLDOWN` | 距上次止损不足 90 分钟 |
| `REJECT_GEOMETRY` | 止盈/止损方向错误、非正价格、零距离 |
| `REJECT_MACD_REGIME` | 启用 MACD 但 regime 不是 `trend_*` |
| `REJECT_SOFT_PARAM` | 软参越界、未知键、或试图覆盖硬门 |
| `REJECT_SIDE` | `side` 不是 `long` / `short` |
| `REJECT_INSUFFICIENT_BARS` | K 线不足 48 根 |

### 2.2 持仓管理拒绝带（giveback）

| 原因码 | 触发带 |
| --- | --- |
| `REJECT_GIVEBACK_NOT_ARMED` | 未激活（MFE 未达激活 R）就试图上移/下移保护止损 |
| `REJECT_GIVEBACK_FEE_LOSS` | 激活后的保护价仍低于（多）/高于（空）含往返手续费的盈亏平衡 |

`OK` 表示该动作被脚手架接受，**不是**实盘成交回执。

---

## 3. 多空对称

多空共用同一套阈值、同一套原因码、同一套硬门。

对任意多头几何 `(signal, entry, sl, tp)`，以其 `signal_price` 为轴做镜像：

```
entry' = 2S − entry
sl'    = 2S − sl
tp'    = 2S − tp
side'  = short
```

必须满足：

- `sl_pct`、`tp_pct`、`rr` 数值相等
- `check_geometry` 与 `evaluate_candidate` 的 `ok` / `reason` 相同（regime 方向字段可按趋势符号翻转）

禁止「只做多、空头放宽止损 / 放宽 RR / 允许追价」的不对称实现。

---

## 4. 可选 MACD

- 默认关闭。
- **仅** `trend_up` / `trend_down` 允许作为确认过滤。
- `range` 与 `chaos` 启用 MACD → `REJECT_MACD_REGIME`。
- MACD 不得把止损压到 `1.2%` 以下；否则 `REJECT_SL_FLOOR`。
- 快/慢/信号周期必须落在分析师边界，且 `macd_fast < macd_slow`。数值边界见 RISK §软参。

---

## 5. 离线标签字段字典

研究表必须使用下列字段名。取值一律写成字符串，便于 CSV / parquet 对齐。

| 字段 | 说明 |
| --- | --- |
| `ts_utc` | 决策 K 收盘 UTC，ISO-8601 |
| `symbol` | 标的，如 `BTC-USDT-SWAP` |
| `timeframe` | 固定 `5m` |
| `feature_n` | 固定 `48` |
| `atr_pct` | ATR / close |
| `width` | 窗口振幅 / close |
| `slope` | 标准化 OLS 斜率 |
| `eff` | 效率比 |
| `brk` | 有符号突破幅度 |
| `regime` | `chaos` / `trend_up` / `trend_down` / `range` |
| `side` | `long` / `short` |
| `signal_price` | 信号参考价（追价基准） |
| `entry` | 拟入场价 |
| `sl` | 止损价 |
| `tp` | 止盈价 |
| `sl_pct` | 止损距离 / entry |
| `tp_pct` | 止盈距离 / entry |
| `rr` | 盈亏比 |
| `risk_pct` | 本笔账户风险占比 |
| `open_positions` | 决策时已开仓数 |
| `open_risk_pct` | 已开仓风险合计 |
| `daily_loss_pct` | 当日已亏 / 日初权益 |
| `reason_code` | 主原因码 |
| `accepted` | `1` 通过 / `0` 拒绝 |
| `macd_used` | 是否请求 MACD 确认 |
| `giveback_armed` | giveback 是否已激活 |
| `mfe_pct` | 入场后最大有利偏移 / entry |
| `mae_pct` | 入场后最大不利偏移 / entry |
| `fee_pct_rt` | 往返手续费比例 |
| `outcome` | `open` / `tp` / `sl` / `giveback` / `timeout` / `reject`（保留；**不**替代 `exit_class`） |
| `pnl_pct` | 毛收益 / entry（有符号；保留；**不**替代 `y_r`） |
| `net_pnl_pct` | `pnl_pct − fee_pct_rt`（保留；`y_r` 是它的 1R 口径） |
| `y_r` | 费用感知净盈亏 / 1R；`1R = sl_pct`。未实现盈亏时留空 |
| `exit_class` | 单选离场类：`sl` / `invalidate` / `reverse` / `tp` / `stale_half` / `stale_flat` / `replace` / `manual` / `other` / `reject` |
| `fail_tag` | 多选失败标签，`|` 拼接：`stop_out` / `fake_break` / `regime_wrong` / `chase` / `fee_grind` / `early_lock` / `other` |
| `label_horizon_bars` | 离线标注前瞻根数 |
| `spec_version` | 签名规格版本，当前 `3.0.0` |

`outcome` / `pnl_pct` / `net_pnl_pct` 继续保留，供旧回放对齐；研究主标签改用 `y_r` + `exit_class` + `fail_tag`，三者不得互相顶替。

实现见 `okx_scalper_v3.labels.LABEL_FIELD_DICTIONARY`。未知列名不得写入。

---

## 6. 明确不做的事

- 不连接 OKX 私有下单接口
- 不提交市价/限价实盘单
- 不把软参写成「覆盖硬门」的配置项
- 不在 chaos 下开「例外单」
- 不因 chaos 对已有仓位 flatten-all / 强平（只拦新开）
