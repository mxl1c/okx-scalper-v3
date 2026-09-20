# okx-scalper-v3

签名策略脚手架：**regime 分类 + 几何检查 + 硬风控门 + 软参边界**。

- **不下单。** 没有 OKX 私有交易客户端，没有 live order 路径。
- **硬门不可放宽。** 数值与边界由 pytest 锁死，CI 在每次 push 上跑。
- **软参** 只能落在分析师区间内，且不能覆盖硬门。MACD 可选，仅 `trend_*`，止损仍须 `≥ 1.2%`。

规格正文：

- [`STRATEGY.md`](STRATEGY.md) — chaos → trend → range，5m / N=48 特征，拒绝带，多空对称，离线标签字典
- [`RISK.md`](RISK.md) — 并行 ≤3、单笔 ≤2%、合计 ≤5%、日亏 5% 无豁免、MIN_RR ≥1.5、追价禁令、SL 地板 ≥1.2%、冷却 90 分钟、giveback 规则

## 安装与测试

```bash
python -m pip install -e ".[dev]"
pytest -q
```

需要 Python 3.11+。包本身无运行时第三方依赖。

## 包结构

```
okx_scalper_v3/
  hard_gates.py    签名常量
  features.py      atr_pct / width / slope / eff / brk
  regime.py        chaos → trend → range
  geometry.py      SL / RR / chase / 对称
  risk.py          资金与冷却硬门
  giveback.py      激活后、费用感知不亏
  soft_params.py   分析师边界
  labels.py        离线字段字典
  evaluate.py      离线候选评估入口
```

评估一个候选（纯本地对象，无网络）：

```python
from okx_scalper_v3.evaluate import evaluate_candidate

decision = evaluate_candidate(bars, geometry, account)
# decision.ok, decision.reason
```

## 安全

不要把 API key、`.env`、成交日志提交进仓库。见 `.gitignore`。
