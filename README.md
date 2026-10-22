# DuckDB 2.0 Book — Companion Code

> 配套代码：《DuckDB 实战：从单机分析到数据湖仓》（基于 DuckDB 2.0 LTS）
> Companion code repository. The book manuscript lives in a private repo; this repo holds everything you can run.

## 内容 / What's here

| 目录 | 内容 | 状态 |
|---|---|---|
| `dataset/` | **DuckShop 数据集生成器**——贯穿全书的虚构电商数据（订单 CSV / 埋点 JSONL / 商品 Parquet） | ✅ 实测（DuckDB 2.0.0） |
| `ch09/` | 扩展开发入门：`pinyin_initials` 的 SQL 宏教学版（+ Rust 扩展版结构说明） | ✅ 实测 |
| `ch14/` | 每日增量管道零依赖参考实现：raw→stg→mart 分层、增量水位、幂等重跑、质量断言 | ✅ 实测（backfill+幂等） |

## 快速开始

```bash
pip install "duckdb>=2.0.0"

# 1. 生成 DuckShop 数据集
cd dataset && python3 generate.py --rows 100000

# 2. 跑一遍增量管道（第 14 章）
cd ../ch14 && python3 pipeline.py --backfill && python3 pipeline.py  # 二次跑=幂等 0 行

# 3. 扩展开发第一课（第 9 章）
cd ../ch09 && duckdb < pinyin_macro.sql
```

## 环境要求

- Python 3.9+，`duckdb>=2.0.0`（2.0.0 于 2026-10-21 发布）
- 全部示例在本机 DuckDB 2.0.0 (linux_amd64) 上实测通过

## License

MIT
