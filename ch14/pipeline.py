#!/usr/bin/env python3
"""DuckShop 每日增量管道（第 14 章配套 · 纯 DuckDB 自包含版）

书里讲 dbt+dlt+Dagster 三件套；本脚本是零依赖参考实现——
同样的分层（raw→stg→mart）、增量水位、幂等重跑、质量断言，
只用 duckdb 一个依赖，方便读者先理解管道骨架再上工具链。

用法：
  python3 pipeline.py            # 跑一轮「今日」增量
  python3 pipeline.py --backfill # 全量重跑
依赖：duckdb>=2.0.0；数据来自 ../dataset/（先生成）
"""
import argparse, os, sys, datetime
import duckdb

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "shop.duckdb")
DS = os.path.join(HERE, "..", "dataset")
SOURCE = os.path.join(DS, "events.jsonl")

def con() -> duckdb.DuckDBPyConnection:
    c = duckdb.connect(DB)
    c.execute("CREATE SEQUENCE IF NOT EXISTS runseq")
    c.execute("""
        CREATE TABLE IF NOT EXISTS _pipeline_runs(
            run_id INTEGER PRIMARY KEY DEFAULT nextval('runseq'),
            started_at TIMESTAMP DEFAULT now(),
            rows_ingested BIGINT, status VARCHAR);
        CREATE TABLE IF NOT EXISTS raw_events(
            payload VARIANT, ingested_at TIMESTAMP DEFAULT now());
        CREATE TABLE IF NOT EXISTS _watermark(k VARCHAR PRIMARY KEY, v VARCHAR);
        CREATE TABLE IF NOT EXISTS _assert_failures(
            run_id INTEGER, assertion VARCHAR, detail VARCHAR);
    """)
    return c

def ingest(c, backfill: bool) -> int:
    """增量摄取：水位=已摄取行数（教学用；生产用水位列/文件 mtime）"""
    if backfill:
        c.execute("DELETE FROM raw_events")
        c.execute("DELETE FROM _watermark")
    row = c.execute(
        "SELECT CAST(coalesce(v,'0') AS BIGINT) FROM _watermark WHERE k='events_lines'"
    ).fetchone()
    already = int(row[0]) if row else 0
    c.execute(f"""
        INSERT INTO raw_events (payload)
        SELECT to_json(src)::VARIANT
        FROM (
            SELECT * FROM read_json_auto('{SOURCE}')
            LIMIT 9223372036854775807 OFFSET {already}
        ) src
    """)
    n = c.execute("SELECT count(*) FROM raw_events").fetchone()[0] - already
    c.execute("INSERT OR REPLACE INTO _watermark VALUES ('events_lines', ?)", [str(already + n)])
    return n

def transform(c):
    """stg → int → mart 分层（对应 code/ch14/models/ 的 dbt 版本）"""
    c.execute("""
        CREATE OR REPLACE TABLE stg_events AS
        SELECT payload.event AS event_name,
               payload.session AS session_id,
               TRY_CAST(payload.ts AS TIMESTAMP) AS ts,
               TRY_CAST(payload.order_id AS BIGINT)  AS order_id,
               TRY_CAST(payload.amount AS DOUBLE)    AS amount,
               payload.channel AS channel,
               payload
        FROM raw_events;

        CREATE OR REPLACE TABLE int_session_actions AS
        SELECT session_id, event_name, ts,
               row_number() OVER (PARTITION BY session_id ORDER BY ts) AS step
        FROM stg_events WHERE session_id IS NOT NULL;

        CREATE OR REPLACE TABLE mart_daily_metrics AS
        SELECT CAST(ts AS DATE) AS d,
               count(DISTINCT session_id)                    AS sessions,
               count(*) FILTER (WHERE event_name='search')   AS searches,
               count(*) FILTER (WHERE event_name='purchase') AS purchases,
               coalesce(sum(amount) FILTER (WHERE event_name='purchase'), 0) AS gmv
        FROM stg_events
        WHERE ts IS NOT NULL
        GROUP BY 1;
    """)

def assert_quality(c, run_id: int):
    """质量断言（dbt test 的对应物）：失败不阻断本轮，但记录在案"""
    checks = [
        ("session 非空占比>=99%",
         "SELECT count(*) FILTER (WHERE session_id IS NULL) * 100.0 / greatest(count(*),1) > 1 FROM stg_events"),
        ("purchase 均价在 [1, 1000]",
         "SELECT count(*) FROM stg_events WHERE event_name='purchase' AND (amount < 1 OR amount > 1000) > 0"),
    ]
    for name, sql in checks:
        bad = c.execute(f"SELECT ({sql})").fetchone()[0]
        if bad:
            c.execute("INSERT INTO _assert_failures VALUES (?,?,?)", [run_id, name, "see query"])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill", action="store_true")
    args = ap.parse_args()
    if not os.path.exists(SOURCE):
        sys.exit(f"数据不存在：先跑 {DS}/generate.py")
    c = con()
    run_row = c.execute(
        "INSERT INTO _pipeline_runs (rows_ingested, status) VALUES (0,'running') RETURNING run_id"
    ).fetchone()
    run_id = run_row[0] if run_row else 0
    n = ingest(c, args.backfill)
    transform(c)
    assert_quality(c, run_id)
    c.execute("UPDATE _pipeline_runs SET status='ok', rows_ingested=? WHERE run_id=?", [n, run_id])
    head = c.execute("SELECT * FROM mart_daily_metrics ORDER BY d LIMIT 3").fetchall()
    total = c.execute("SELECT sum(gmv) FROM mart_daily_metrics").fetchone()[0]
    c.close()
    print(f"run #{run_id}: 摄取 {n} 行（幂等水位已推进）")
    print(f"mart_daily_metrics 前 3 行: {head}")
    print(f"累计 GMV: {total:,.2f}")

if __name__ == "__main__":
    main()
