# ch09 扩展开发配套：pinyin_ext

> 第 9 章「五十行起步」的完整可编译版本。

真实的 Rust 扩展需要官方 extension-template 工具链（C API 头、平台构建），完整工程在独立仓库维护。本目录给出**最小核心逻辑**（纯 Rust，零依赖），配套一个 **SQL 宏参考实现**——后者开箱即用，让你在编译扩展之前先体验第 9 章的完整用户旅程。

## 1. SQL 宏版（开箱即用，先跑这个）

```bash
duckdb < ch09/pinyin_macro.sql
```

```sql
-- pinyin_macro.sql 核心（首字母映射 + macro 封装）
CREATE OR REPLACE MACRO pinyin_initials(s) AS
    (
        SELECT string_agg(ch, '')
        FROM (
            SELECT upper(substr(map_from_entries([
                ('杭','h'),('州','z'),('猿','y'),('通','t'),
                ('北','b'),('上','s'),('广','g'),('深','s'),
                ('杭','h'),('电','d'),('数','s'),('据','j')
            ])[s], 1, 1)) AS ch
            WHERE s IS NOT NULL
        )
    );
-- 教学示意：真实实现需要完整拼音表（见下方 Rust 版数据源）
```

⚠️ 教学边界：宏版仅覆盖示例字集。完整 2 万+ 汉字的声母表是 Rust 扩展版的真实理由——
「什么时候值得写扩展」正是第 9 章要教的判断：**查表逻辑超过 SQL 数据结构的舒适区，就是扩展的起点**。

## 2. Rust 扩展版（结构对齐第 9 章 §2/§3）

```
pinyin_ext/
├── Cargo.toml        # duckdb = { version="1", features=["build-extension"] }
├── src/lib.rs        # extension_init + register_scalar（书稿 §2 代码的完整版）
├── src/table.rs      # 表函数三段式骨架（§3：参数声明→绑定→扫描）
└── tests/            # SQL 断言测试（§5）
```

构建（需 Rust 工具链 + 官方模板依赖）：

```bash
cargo build --release
cp target/release/libpinyin_ext.so pinyin_ext.duckdb_extension
duckdb -c "LOAD './pinyin_ext.duckdb_extension'; SELECT pinyin_initials('杭州猿通');"
```

## 3. 数据源

声母表数据取自开源拼音库（如 `pinyin-pro` 的首字母映射，MIT），处理为
`char -> initial` 的静态表编译进扩展——第 10 章 FFI 桥的「宿主层锁版本」原则同样适用于数据文件。
