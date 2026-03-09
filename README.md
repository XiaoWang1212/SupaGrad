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
- 手動上傳審查頁：`GET /`
- 手動上傳審查 API：`POST /api/v1/manual/audit`
- HTML 上傳解析頁：`GET /html-upload`
- HTML 上傳解析 API：`POST /api/v1/html/analyze`

HTML 解析 API 會嘗試：

- 從 iNCU 另存網頁解析學號、累計學分、EMI學分、學期課程明細
- 計算各類學分（依課程屬性）與課號前綴學分（例如 IM/GS/CC）
- 寫入 Supabase：`students` 與 `enrollments`

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

## 手動上傳審查（先給自己用）

你可以先不用 Vue。現在前端是 Flask 內建頁面 + 原生 JavaScript。

1. 開啟 `http://127.0.0.1:5001/`
1. 上傳成績單 `transcript_file`（必填）
1. 上傳抵免檔 `transfer_file`（可選）
1. 輸入需求學分與必修課號清單

### CSV 格式

`transcript_file` 與 `transfer_file` 都支援以下欄位：

- `course_id`：課號（建議填）
- `credits`：學分（必填）
- `passed`：是否通過（可選，預設視為通過；可填 `1/0/true/false/yes/no/passed`）

最小範例：

```csv
course_id,credits,passed
IM1010,3,true
CC1001,2,1
EE2001,3,false
```

### API 範例

```bash
curl -X POST http://127.0.0.1:5001/api/v1/manual/audit \
  -F "student_id=s111111" \
  -F "required_credits=128" \
  -F "required_courses=IM1010,IM2030" \
  -F "transcript_file=@./data/transcript.csv" \
  -F "transfer_file=@./data/transfer.csv"
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
