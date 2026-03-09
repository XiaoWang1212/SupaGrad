from pathlib import Path
import os
import sys

from dotenv import load_dotenv
import psycopg


def main() -> int:
    load_dotenv()

    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        print("❌ 缺少 SUPABASE_DB_URL")
        print("請在 .env 設定，例如：")
        print("SUPABASE_DB_URL=postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres?sslmode=require")
        return 1

    sql_path = Path(__file__).with_name("init_db.sql")
    sql = sql_path.read_text(encoding="utf-8")

    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
        print("✅ 資料表初始化完成")
        return 0
    except Exception as exc:
        print(f"❌ 初始化失敗: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())