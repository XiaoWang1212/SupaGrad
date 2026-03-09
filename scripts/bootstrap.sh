#!/usr/bin/env bash
set -euo pipefail

echo "==> SupaGrad bootstrap start"

if [ ! -f ".env" ]; then
  echo "❌ 找不到 .env，請先建立 .env 並填入 SUPABASE_DB_URL"
  exit 1
fi

if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

if command -v uv >/dev/null 2>&1; then
  echo "==> 安裝依賴（uv）"
  uv pip install -r requirements.txt
else
  echo "==> 安裝依賴（pip）"
  python -m pip install -r requirements.txt
fi

echo "==> 初始化資料庫"
python scripts/init_db.py

echo "✅ Bootstrap 完成"