#!/usr/bin/env python3
"""DuckShop 数据集生成器 v2——埋点事件每行形状真实不同（喂 VARIANT 章）
产出：orders.csv / events.jsonl / products.parquet
用法：python3 generate.py [--rows 1000000]   依赖：duckdb>=2.0.0（仅用它造数据，写出用 Python 保证每行形状）
"""
import argparse, json, os

import duckdb

HERE = os.path.dirname(os.path.abspath(__file__))

def gen_events(con, n, path):
    """4 种事件类型，每行只含自己的键——真实埋点形态"""
    rows = con.execute(f"""
        SELECT e % 4 AS kind,
               strftime(TIMESTAMP '2026-01-01' + INTERVAL ((e * 53 % 25000000)::INTEGER) SECOND, '%Y-%m-%d %H:%M:%S') AS ts,
               's' || (e * 611953 % 200000)::VARCHAR AS s,
               1 + (e * 7919 % 10000) AS pid,
               (ARRAY ['/home','/search','/cart','/me'])[1 + e % 4] AS ref,
               e % 800 AS x, (e * 7 % 600) AS y,
               (ARRAY ['btn-buy','btn-cart','link-detail','tab-review'])[1 + e % 4] AS tgt,
               (ARRAY ['手机','笔记本电脑','连衣裙','咖啡豆','乐高','跑鞋'])[1 + e % 6] AS q,
               e % 120 AS r,
               1 + (e % 1000000) AS oid,
               round(10 + (e * 13 % 990) / 10.0, 2) AS amt,
               (ARRAY ['app','web','miniapp'])[1 + e % 3] AS ch
        FROM range({n}) t(e)
    """).fetchall()
    with open(path, "w") as f:
        for kind, ts, s, pid, ref, x, y, tgt, q, r, oid, amt, ch in rows:
            if kind == 0:
                o = {"event": "page_view", "ts": ts, "session": s, "page_url": f"/item/{pid}", "referrer": ref}
            elif kind == 1:
                o = {"event": "click", "ts": ts, "session": s, "x": x, "y": y, "target": tgt}
            elif kind == 2:
                o = {"event": "search", "ts": ts, "session": s, "query": q, "results": r}
            else:
                o = {"event": "purchase", "ts": ts, "session": s, "order_id": oid, "amount": amt, "channel": ch}
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    return len(rows)

def main(rows: int):
    con = duckdb.connect(":memory:")

    con.execute("""
        CREATE TABLE products AS
        SELECT i + 1 AS product_id,
               'P' || lpad((i + 1)::VARCHAR, 5, '0') AS sku,
               (1000 + (i * 7919) % 9000)::DOUBLE / 100 AS price,
               (ARRAY ['图书','数码','家居','服饰','食品','美妆','运动','母婴'])[1 + i % 8] AS category,
               (i % 100 = 0) AS is_test
        FROM range(10000) t(i)
    """)

    con.execute(f"""
        CREATE TABLE orders AS
        SELECT o + 1 AS id,
               1 + (o * 7919) % 50000 AS customer_id,
               1 + (o * 104729) % 10000 AS product_id,
               round(10 + (o * 31 % 4990) / 10.0, 2) AS amount,
               (DATE '2026-01-01' + INTERVAL ((o * 17 % 290)::INTEGER) DAY)::DATE AS order_date,
               CASE o % 10 WHEN 0 THEN 'new' WHEN 1 THEN 'paid' WHEN 2 THEN 'shipped'
                    WHEN 3 THEN 'done' WHEN 4 THEN 'cancelled' ELSE 'done' END AS status,
               (o % 500 = 0) AS is_test
        FROM range({rows}) t(o)
    """)

    con.execute(f"COPY products TO '{HERE}/products.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)")
    con.execute(f"COPY orders   TO '{HERE}/orders.csv' (FORMAT CSV, HEADER)")
    n_ev = gen_events(con, max(rows // 2, 1), f"{HERE}/events.jsonl")

    print(f"OK: products.parquet(10000) orders.csv({rows}) events.jsonl({n_ev})")
    print("冒烟:", con.execute(f"SELECT count(*), min(order_date), max(order_date) FROM '{HERE}/orders.csv'").fetchall())

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=1_000_000)
    main(ap.parse_args().rows)
