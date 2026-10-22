-- ch09 · pinyin_initials 的 SQL 宏教学版（在 DuckDB 2.0.0 上实测通过）
-- 完整 2 万+ 字声母表请用 Rust 扩展版（见同目录 README）——本文件只演示「macro 能做到哪、何时该升级成扩展」

-- 逐字拆行：regexp_split_to_array(s, '')（教学：string_split(s, NULL) 不拆行，实测坑）
CREATE OR REPLACE MACRO pinyin_initials(s) AS (
    SELECT string_agg(initial, '') AS initials
    FROM (
        SELECT coalesce(
            (SELECT i FROM (VALUES
                ('杭','h'),('州','z'),('猿','y'),('通','t'),
                ('北','b'),('上','s'),('广','g'),('深','s'),
                ('电','d'),('数','s'),('据','j'),('库','k'),
                ('手','s'),('机','j'),('脑','n')
            ) t(c, i) WHERE c = ch),
            '') AS initial
        FROM unnest(regexp_split_to_array(s, '')) t(ch)
    )
);

-- 冒烟
SELECT pinyin_initials('杭州猿通')  AS a;   -- hzyt
SELECT pinyin_initials('数据库')    AS b;   -- sjk
