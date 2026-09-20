# okx-scalper-v3 风险说明书（硬门）

**策略 ID：** `okx-scalper-v3`  
**规格版本：** `3.0.0`  
**原则：** 硬门不可豁免、不可被软参覆盖、不可被 MACD / 形态 / 「这次不一样」绕过。日亏 5% **没有** 例外通道。

实现锁在 `okx_scalper_v3.hard_gates`。pytest 同时锁 **数值** 与 **边界开闭**；放宽任一扇门必须让 CI 变红。

---

## 1. 硬门一览

| 硬门 | 合同 | 拒绝码 | 边界 |
| --- | --- | --- | --- |
| 并行仓位 | `parallel ≤ 3` | `REJECT_PARALLEL` | 已开 3 仓时第 4 笔拒绝 |
| 单笔风险 | `per-trade ≤ 2%` | `REJECT_PER_TRADE_RISK` | `2.00%` 过，`> 2%` 拒 |
| 合计风险 | `aggregate ≤ 5%` | `REJECT_AGGREGATE_RISK` | 已开 + 本笔 `> 5%` 拒 |
| 日亏损 | `daily loss 5%`，无豁免 | `REJECT_DAILY_LOSS` | 日亏 `≥ 5%` 即停新开；`exemption=True` 仍拒 |
| 盈亏比 | `MIN_RR ≥ 1.5` | `REJECT_MIN_RR` | `1.5` 过，`< 1.5` 拒 |
| 追价 | **Chase ban** | `REJECT_CHASE` | 多头不得高于信号价，空头不得低于信号价 |
| 止损地板 | `SL floor ≥ 1.2%` | `REJECT_SL_FLOOR` | `1.2%` 过，`< 1.2%` 拒 |
| 冷却 | `90m` | `REJECT_COOLDOWN` | 距上次止损 `< 90` 分钟拒，满 90 分钟过 |
| Giveback | 仅激活后 + 费用感知不亏 | `REJECT_GIVEBACK_*` | 见第 3 节 |
| 混沌 | chaos = **只禁止新开**，不 flatten-all / 不强平已有仓 | `REJECT_CHAOS` | 无新开例外；已开仓不因此强平 |

常量（不得改大、不得关掉）：

```
MAX_PARALLEL                  = 3
MAX_PER_TRADE_RISK            = 0.02
MAX_AGGREGATE_RISK            = 0.05
MAX_DAILY_LOSS                = 0.05
DAILY_LOSS_EXEMPTIONS_ALLOWED = False
MIN_RR                        = 1.5
MIN_SL_PCT                    = 0.012
CHASE_BANNED                  = True
COOLDOWN_MINUTES              = 90
CHAOS_BLOCKS_NEW_OPENS        = True
GIVEBACK_REQUIRES_ACTIVATION  = True
GIVEBACK_FEE_AWARE_NO_LOSS    = True
```

`CHAOS_BLOCKS_NEW_OPENS` 的语义是 **block new opens only**。chaos 不是 flatten-all，不是 force-close，也不改写已有仓的 SL / TP / giveback。已开仓继续按原几何与持仓硬门管理，直到各自离场。

---

## 2. 资金与日亏

- **单笔风险** = 该候选单若打到止损，占权益的比例。脚手架默认 `risk_pct = sl_pct`（名义等于权益）；调用方可传入已按杠杆换算的 `risk_pct`，但 **2% 硬顶不变**。
- **合计风险** = 已开仓风险之和 + 本笔。两者都按同一口径。
- **日亏 5%**：`daily_loss_pct = −daily_pnl / day_start_equity`。触及或越过 5% 后当日禁止一切新开。
  - `AccountState.exemption` 被忽略。
  - `DAILY_LOSS_EXEMPTIONS_ALLOWED` 必须为 `False`。若有人把它改成 `True`，门控自身失败。
- 日亏停机 **不能** 用「补一单摊平」解除。冷却与日亏是两道独立门。

---

## 3. Giveback（回吐保护）

Giveback 不是开仓门，是持仓管理门。

1. **必须先激活。** 激活条件：`MFE / sl_distance ≥ giveback_activation_r`（软参，默认 `1.0R`，边界 `[0.8, 1.5]`）。未激活禁止把止损改成保护价。
2. **费用感知不亏。** 往返费 = `2 × fee_pct_one_way`。
   - 多头盈亏平衡 = `entry × (1 + 2f)`，保护止损必须 `≥` 该价。
   - 空头盈亏平衡 = `entry × (1 − 2f)`，保护止损必须 `≤` 该价。
   - 把止损只挪到入场价（未覆盖手续费）视为亏损锁定，拒绝。
3. 软参可以 **更晚** 激活（在分析师边界内），不能取消激活要求，也不能取消费用地板。

---

## 4. 追价禁令

硬门，不是软阈值。

- 多：`entry ≤ signal_price`
- 空：`entry ≥ signal_price`

任何「市价追突破」「信号后再滑去更差的价」都是 chase。本脚手架不提供 chase 白名单。

---

## 5. 冷却 90 分钟

`now - last_stop_ts < 90 minutes` → `REJECT_COOLDOWN`。  
`last_stop_ts is None` 视为无冷却。满 90.0 分钟允许评估下一笔（仍要过其它硬门）。

---

## 6. 软参

软参边界（不能覆盖硬门）。STRATEGY 交叉引用本节为「RISK §软参」。

允许调节的键与闭区间：

| 键 | 下限 | 上限 | 默认 |
| --- | --- | --- | --- |
| `atr_period` | 7 | 21 | 14 |
| `chaos_atr_pct` | 0.012 | 0.040 | 0.022 |
| `chaos_eff_max` | 0.12 | 0.28 | 0.20 |
| `chaos_width_min` | 0.020 | 0.080 | 0.035 |
| `trend_eff_min` | 0.32 | 0.55 | 0.38 |
| `trend_slope_min` | 0.00015 | 0.0020 | 0.00035 |
| `range_width_max` | 0.015 | 0.060 | 0.030 |
| `macd_fast` | 8 | 16 | 12 |
| `macd_slow` | 21 | 30 | 26 |
| `macd_signal` | 7 | 12 | 9 |
| `giveback_activation_r` | 0.8 | 1.5 | 1.0 |
| `fee_pct_one_way` | 0.0001 | 0.0010 | 0.0005 |

`macd_enabled` 是开关，不是数值边界。  
下列别名一旦出现在软参里，直接 `REJECT_SOFT_PARAM`：

`max_parallel`, `per_trade_risk`, `max_per_trade_risk`, `aggregate_risk`, `max_aggregate_risk`, `daily_loss`, `max_daily_loss`, `min_rr`, `sl_floor`, `min_sl_pct`, `cooldown_minutes`, `chase_banned`, `feature_n`, `exemption`, `daily_loss_exemption`

MACD 即使打开：

- 只许 `trend_*`
- `SL ≥ 1.2%`，否则拒绝
- 不能提高并行、放大风险、缩短冷却、允许追价

---

## 7. 门控顺序（开仓）

1. 软参合法性  
2. K 线数量  
3. 几何 / 追价 / SL 地板 / MIN_RR  
4. 可选 MACD 的 regime 约束  
5. chaos 禁新开（不 flatten-all）  
6. 日亏  
7. 冷却  
8. 并行  
9. 单笔风险  
10. 合计风险  

任一失败立即返回对应原因码。

---

## 8. 本仓库不做的风险动作

- 不发 OKX 订单，不改杠杆，不自动减仓到交易所
- 不因 chaos flatten-all / 强平已有仓（只拦新开）
- 不提供「管理员 override」或环境变量松绑硬门
- 不把密钥、`.env`、成交日志提交进 git
