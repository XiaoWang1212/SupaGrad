from dataclasses import asdict, dataclass


@dataclass(slots=True)
class ParsedCourse:
    term: str | None
    course_id: str
    course_type: str
    credits: int
    score_text: str
    note: str
    passed: bool


@dataclass(slots=True)
class ParsedStudent:
    student_id: str | None
    student_name: str | None
    department: str | None
    accumulated_credits_from_html: int | None
    emi_credits_from_html: int | None


@dataclass(slots=True)
class CreditSummary:
    completed_credits_calculated: int
    completed_credits_from_html: int | None
    emi_earned_credits_calculated: int
    credits_by_course_type: dict[str, int]
    credits_by_prefix: dict[str, int]


@dataclass(slots=True)
class ParsedHtmlTranscript:
    filename: str
    byte_size: int
    char_size: int
    table_count: int
    row_count: int
    cell_count: int
    student: ParsedStudent
    credit_summary: CreditSummary
    courses: list[ParsedCourse]
    passed_course_count: int
    text_preview: str

    def to_dict(self) -> dict:
        return asdict(self)
