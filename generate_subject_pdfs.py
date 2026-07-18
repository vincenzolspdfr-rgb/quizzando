from html import escape
from pathlib import Path
import json
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


BASE = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE / "pdf_materie"
QUESTIONS_JS = BASE / "app" / "questions.js"


STYLES = getSampleStyleSheet()
TITLE_STYLE = ParagraphStyle(
    "TitleStyle",
    parent=STYLES["Title"],
    fontName="Helvetica-Bold",
    fontSize=19,
    leading=23,
    alignment=TA_CENTER,
    textColor=colors.HexColor("#172026"),
    spaceAfter=12,
)
TOPIC_STYLE = ParagraphStyle(
    "TopicStyle",
    parent=STYLES["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=13,
    leading=16,
    textColor=colors.HexColor("#0e6f68"),
    spaceBefore=10,
    spaceAfter=8,
)
CELL_STYLE = ParagraphStyle(
    "CellStyle",
    parent=STYLES["BodyText"],
    fontName="Helvetica",
    fontSize=8.2,
    leading=10.5,
)
HEADER_STYLE = ParagraphStyle(
    "HeaderStyle",
    parent=CELL_STYLE,
    fontName="Helvetica-Bold",
    textColor=colors.white,
)


def load_data():
    raw = QUESTIONS_JS.read_text(encoding="utf-8")
    prefix = "window.GEOMETRIA_DATA = "
    if not raw.startswith(prefix):
        raise ValueError(f"Formato non riconosciuto: {QUESTIONS_JS}")
    return json.loads(raw[len(prefix):].rstrip().rstrip(";"))


def clean_filename(value):
    value = re.sub(r"[^A-Za-z0-9À-ÿ _-]+", "", value)
    value = re.sub(r"\s+", "_", value.strip())
    return value or "Materia"


def paragraph(text, style=CELL_STYLE):
    return Paragraph(escape(str(text)), style)


def make_table(rows, col_widths=None):
    table = Table(rows, colWidths=col_widths or [1.9 * cm, 15.2 * cm, 9.2 * cm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0e6f68")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d8cdbb")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fffaf0")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def roman_to_number(value):
    mapping = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    chars = value.upper()
    for index, char in enumerate(chars):
        current = mapping.get(char, 0)
        next_value = mapping.get(chars[index + 1], 0) if index + 1 < len(chars) else 0
        total += -current if current < next_value else current
    return total


def extract_date_info(question):
    if question["subject"] not in ["Storia", "Letteratura"]:
        return None

    text = f"{question['question']} {question['answer']}"
    has_date_context = re.search(
        r"\b(anno|anni|data|date|secolo|nacque|nato|morì|morto|visse|governò|regnò|dal|al|nel|tra|fino|avvenne|avvenuto|fondata|fondato|incoronato|combattuta|combattuto|periodo|età|concilio|battaglia|guerra|pace|impero|imperatore)\b",
        text,
        re.IGNORECASE,
    )
    year_match = re.search(r"\b(\d{3,4})\s*(a\.c\.|a\. c\.|avanti cristo|d\.c\.|d\. c\.|dopo cristo)?\b", text, re.IGNORECASE)
    if year_match and has_date_context:
        raw_year = int(year_match.group(1))
        suffix = year_match.group(2) or ""
        is_before_christ = re.search(r"a\.\s*c\.|avanti cristo", suffix, re.IGNORECASE)
        label = f"{year_match.group(1)} {suffix}".strip()
        return {"value": -raw_year if is_before_christ else raw_year, "label": re.sub(r"\s+", " ", label)}

    century_match = re.search(
        r"\b([IVXLCDM]{1,6})\s*(?:°|º)?\s*(secolo|sec\.)\s*(a\.c\.|a\. c\.|avanti cristo|d\.c\.|d\. c\.|dopo cristo)?\b",
        text,
        re.IGNORECASE,
    )
    if century_match:
        century = roman_to_number(century_match.group(1))
        suffix = century_match.group(3) or ""
        midpoint = ((century - 1) * 100) + 50
        is_before_christ = re.search(r"a\.\s*c\.|avanti cristo", suffix, re.IGNORECASE)
        label = f"{century_match.group(1)} secolo {suffix}".strip()
        return {"value": -midpoint if is_before_christ else midpoint, "label": re.sub(r"\s+", " ", label)}

    return None


def get_date_timeline_questions(questions):
    dated_questions = []
    for question in questions:
        date_info = extract_date_info(question)
        if date_info:
            dated_questions.append((question, date_info))
    dated_questions.sort(key=lambda item: (item[1]["value"], int(item[0]["id"])))
    return dated_questions


def build_subject_pdf(data, subject):
    subject_questions = [question for question in data["questions"] if question["subject"] == subject]
    output_path = OUTPUT_DIR / f"{clean_filename(subject)}.pdf"
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(A4),
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
        topMargin=1.1 * cm,
        bottomMargin=1.1 * cm,
        title=f"{subject} - Quizzando",
        author="Quizzando",
    )

    story = [
        Paragraph(f"Quizzando - {escape(subject)}", TITLE_STYLE),
        Paragraph(f"Domande totali: {len(subject_questions)}", CELL_STYLE),
        Spacer(1, 8),
    ]

    date_timeline = get_date_timeline_questions(subject_questions)
    if subject in ["Storia", "Letteratura"] and date_timeline:
        story.append(Paragraph(f"Solo date - linea temporale ({len(date_timeline)})", TOPIC_STYLE))
        rows = [[
            Paragraph("Data", HEADER_STYLE),
            Paragraph("N", HEADER_STYLE),
            Paragraph("Testo della domanda", HEADER_STYLE),
            Paragraph("Risposta corretta", HEADER_STYLE),
        ]]
        for question, date_info in date_timeline:
            rows.append([
                paragraph(date_info["label"]),
                paragraph(question["id"]),
                paragraph(question["question"]),
                paragraph(question["answer"]),
            ])
        story.append(make_table(rows, [2.4 * cm, 1.6 * cm, 14.0 * cm, 8.2 * cm]))
        story.append(Spacer(1, 12))

    for topic in data["topicsBySubject"].get(subject, []):
        topic_questions = [question for question in subject_questions if question["topic"] == topic]
        if not topic_questions:
            continue
        story.append(Paragraph(f"{escape(topic)} ({len(topic_questions)})", TOPIC_STYLE))
        rows = [[
            Paragraph("N", HEADER_STYLE),
            Paragraph("Testo della domanda", HEADER_STYLE),
            Paragraph("Risposta corretta", HEADER_STYLE),
        ]]
        for question in topic_questions:
            rows.append([
                paragraph(question["id"]),
                paragraph(question["question"]),
                paragraph(question["answer"]),
            ])
        story.append(make_table(rows))
        story.append(Spacer(1, 10))

    doc.build(story)
    return output_path, len(subject_questions)


def main():
    data = load_data()
    OUTPUT_DIR.mkdir(exist_ok=True)
    generated = []
    for subject in data["subjects"]:
        generated.append(build_subject_pdf(data, subject))
    for path, count in generated:
        print(f"{path.name}: {count} domande")
    print(f"PDF creati in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
