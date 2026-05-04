import os
import re

try:
    import openai
except ImportError:  # pragma: no cover
    openai = None

try:
    import google.generativeai as gemini
except ImportError:  # pragma: no cover
    gemini = None


def _normalize_text_lines(text: str) -> list[str]:
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        cleaned = re.sub(r"^[\-•\*\d\.\)\s]+", "", line)
        if cleaned:
            lines.append(cleaned)
    return lines


def _build_prompts(parsed_result: dict, required_credits: int) -> tuple[str, str]:
    student = parsed_result.get("student", {}) or {}
    department = student.get("department") or ""
    completed = parsed_result.get("credit_summary", {}).get(
        "completed_credits_calculated", 0
    )
    emi_credits = parsed_result.get("credit_summary", {}).get(
        "emi_earned_credits_calculated"
    )
    total_courses = parsed_result.get("passed_course_count", 0)
    missing_credits = max(required_credits - completed, 0)

    system_prompt = (
        "你是大學學分審查助理，請根據以下成績單摘要提供完整建議。"
        "用中文條列出需要補修的學分、系所必要注意事項、EMI 及必修課程建議。"
    )

    user_prompt = (
        "成績單摘要：\n"
        f"學號：{student.get('student_id')}\n"
        f"姓名：{student.get('student_name')}\n"
        f"系所：{department}\n"
        f"已修學分：{completed}\n"
        f"畢業需求學分：{required_credits}\n"
        f"缺少學分：{missing_credits}\n"
        f"EMI 學分：{emi_credits}\n"
        f"通過課程數：{total_courses}\n"
        "請直接給出最重要的 3-5 點建議。"
    )

    return system_prompt, user_prompt


def _gemini_response_to_text(response) -> str:
    if response is None:
        return ""

    if hasattr(response, "last"):
        last = response.last
        if isinstance(last, str):
            return last.strip()
        content = getattr(last, "content", None)
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text") or item.get("content")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts).strip()

    try:
        return str(response).strip()
    except Exception:
        return ""


def _run_gemini(parsed_result: dict, required_credits: int) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    model = os.environ.get("GEMINI_MODEL", "gemini-1.5-pro")

    if not api_key or gemini is None:
        return {
            "advice": "無法使用 Gemini，未設定 GEMINI_API_KEY 或未安裝 google-generativeai。",
            "suggestions": [
                "請確認 .env 已設定 GEMINI_API_KEY，並安裝 google-generativeai 套件。"
            ],
            "source": "fallback",
        }

    gemini.configure(api_key=api_key)
    system_prompt, user_prompt = _build_prompts(parsed_result, required_credits)
    response = gemini.chat.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
    )

    content = _gemini_response_to_text(response)
    suggestions = _normalize_text_lines(content) or [content]
    return {
        "advice": content,
        "suggestions": suggestions,
        "source": "gemini",
        "model": model,
    }


def _run_openai(parsed_result: dict, required_credits: int) -> dict:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")

    if not api_key or openai is None:
        return {
            "advice": "無法使用 OpenAI，未設定 OPENAI_API_KEY 或未安裝 openai。",
            "suggestions": ["請確認 .env 已設定 OPENAI_API_KEY，並安裝 openai 套件。"],
            "source": "fallback",
        }

    openai.api_key = api_key
    system_prompt, user_prompt = _build_prompts(parsed_result, required_credits)
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=400,
    )

    content = ""
    if response and response.choices:
        content = response.choices[0].message.content.strip()

    return {
        "advice": content,
        "suggestions": _normalize_text_lines(content) or [content],
        "source": "openai",
        "model": model,
    }


def generate_llm_analysis(parsed_result: dict, required_credits: int) -> dict:
    provider = os.environ.get("LLM_PROVIDER", "openai").strip().lower()

    if provider == "gemini":
        return _run_gemini(parsed_result, required_credits)

    return _run_openai(parsed_result, required_credits)
