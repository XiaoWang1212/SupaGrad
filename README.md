# SupaGrad Flask API (MVP)

這是 SupaGrad 的第一版後端骨架，採用清楚分層：

- `app.py`: 啟動入口
- `src/__init__.py`: Flask App Factory 與 Blueprint 註冊
- `src/config.py`: 環境設定
- `src/routes/`: API 路由層
- `src/services/`: 商業邏輯層

## 快速啟動

1. 建立 Python 3.11 虛擬環境並安裝套件（uv）

```bash
uv python install 3.11
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

1. 建立環境變數

```bash
cp .env.example .env
```

請填入：

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`

1. 啟動服務

```bash
python app.py
```

1. 測試 API

- 健康檢查：`GET /health`
- 畢業審查：`POST /api/v1/audit/<student_id>`

範例：

```bash
curl -X POST http://127.0.0.1:5001/api/v1/audit/s111111 \
  -H "Content-Type: application/json" \
  -d '{"completed_credits": 115, "required_credits": 128}'
```

若你有設定 Supabase，則可直接不帶 body：

```bash
curl -X POST http://127.0.0.1:5001/api/v1/audit/s111111
```

## Supabase 最小表結構

目前程式會查詢以下欄位：

- `students(id, required_credits)`
- `enrollments(student_id, course_id, passed, credits)`

> `enrollments.credits` 會直接加總為已修學分（僅 `passed=true`）。

## 下一步（你可接著做）

- 新增 `repositories/` 目錄，隔離 SQL 存取
- 將規章規則（program rules）做成資料表與版本化
- 再加上向量檢索模組處理模糊認列
