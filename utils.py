import os
import re
from docx import Document
from docx.oxml.ns import qn
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import Table
from docx.text.paragraph import Paragraph

DEFAULT_IMAGE_DIR = "static/question_images"


def extract_fake_table(text):
    """Convert tab/space-separated lines into an HTML table."""
    lines = text.split("\n")
    rows = [re.split(r"\s{2,}|\t", line.strip()) for line in lines if line.strip()]

    html = "<table border='1' cellspacing='0' cellpadding='5'>"
    for row in rows:
        html += "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
    html += "</table>"
    return html


def extract_table_html(table):
    html = "<table border='1' cellspacing='0' cellpadding='5'>"
    for row in table.rows:
        html += "<tr>"
        for cell in row.cells:
            html += f"<td>{cell.text.strip()}</td>"
        html += "</tr>"
    html += "</table>"
    return html


def save_image_from_run(run, output_dir, image_counter):
    blip_elements = run._element.findall(
        './/a:blip',
        namespaces={'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
    )
    if not blip_elements:
        return None

    rId = blip_elements[0].get(qn('r:embed'))
    image_part = run.part.related_parts[rId]
    data = image_part.blob

    filename = f"question_image_{image_counter}.png"
    path = os.path.join(output_dir, filename)

    with open(path, "wb") as f:
        f.write(data)

    return filename


def iter_block_items(parent):
    for child in parent.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def parse_docx_questions(file_stream, image_output_dir=DEFAULT_IMAGE_DIR):
    document = Document(file_stream)
    questions = []
    current_question = None
    image_counter = 0
    in_case_study = False
    case_study_buffer = []
    extra_after_question = []

    os.makedirs(image_output_dir, exist_ok=True)

    for block in iter_block_items(document):

        # ----------------------------- TABLES -------------------------
        if isinstance(block, Table):
            table_html = extract_table_html(block)

            if in_case_study:
                case_study_buffer.append(table_html)
            else:
                extra_after_question.append(table_html)
            continue

        # ----------------------------- PARAGRAPHS ---------------------
        para = block
        text = para.text.strip()

        # skip empty
        if not text:
            continue

        # Images
        for run in para.runs:
            img = save_image_from_run(run, image_output_dir, image_counter + 1)
            if img and current_question:
                image_counter += 1
                current_question["image"] = img

        # --------------------- Detect Case Study START --------------------
        if (text.lower().startswith("use the") or text.lower().startswith("use information")
            or "answer questions" in text.lower()):

            in_case_study = True
            case_study_buffer.append(f"<p>{text}</p>")
            continue

        # --------------------- Still inside case study ---------------------
        if in_case_study and not re.match(r"^\d+[\.\)]", text):
            if "\t" in text or "  " in text:
                case_study_buffer.append(extract_fake_table(text))
            else:
                case_study_buffer.append(f"<p>{text}</p>")
            continue

        # --------------------- QUESTION START ----------------------------
        if re.match(r"^\d+[\.\)]", text):

            # Close previous question
            if current_question:
                current_question["extra_content"] = ''.join(extra_after_question) or None
                questions.append(current_question)
                extra_after_question = []

            # Extract marks
            marks_match = re.search(r"\((\d+)\s?mks|\((\d+)\s?marks?\)", text, re.IGNORECASE)
            marks = int(marks_match.group(1)) if marks_match else 1

            clean = re.sub(r"\(\d+\s?(?:mks|marks?)\)", "", text)
            q_text = re.sub(r"^\d+[\.\)]\s*", "", clean)

            current_question = {
                "question": q_text,
                "a": "", "b": "", "c": "", "d": "",
                "answer": "",
                "extra_content": ''.join(case_study_buffer) if case_study_buffer else None,
                "image": None,
                "marks": marks
            }

            case_study_buffer = []
            in_case_study = False
            continue

        # ----------------------- OPTIONS A-D ------------------------------
        if re.match(r"^\(?[a-dA-D][\.\)]", text):
            label, content = re.match(r"^\(?([a-dA-D])[\.\)]\s*(.+)", text).groups()
            current_question[label.lower()] = content.strip()
            continue

        # ----------------------- ANSWER -------------------------------
        if text.lower().startswith("answer"):
            m = re.search(r":\s*([a-dA-D])", text)
            if m:
                current_question["answer"] = m.group(1).lower()
            continue

        # -------------------- ANY OTHER TEXT AFTER QUESTION ----------------
        extra_after_question.append(f"<p>{text}</p>")

    # ---------------------- Final question ------------------------
    if current_question:
        current_question["extra_content"] = ''.join(extra_after_question) or current_question["extra_content"]
        questions.append(current_question)

    return questions
