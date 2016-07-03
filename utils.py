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



# ---------------------------------
# Table to HTML conversion
# ---------------------------------
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
    blip_elements = run._element.findall('.//a:blip', namespaces={
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
    })

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



# ---------------------------------
# Iterate paragraphs + tables
# ---------------------------------
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
    extra_html_parts = []
    pre_question_buffer = []     # NEW (case study BEFORE question)
    image_counter = 0
    in_case_study = False
    case_study_buffer = []
    extra_after_question = []

    os.makedirs(image_output_dir, exist_ok=True)

    for block in iter_block_items(document):

        # --------------------------- PARAGRAPH ----------------------------
        if isinstance(block, Paragraph):
            para = block
            text = para.text.strip()

            # extract images within runs
            for run in para.runs:
                image_name = save_image_from_run(run, image_output_dir, image_counter + 1)
                if image_name and current_question:
                    image_counter += 1
                    current_question["image"] = image_name

            if not text:
                continue

            # ------------------ CASE STUDY BEFORE FIRST QUESTION ------------------
            if current_question is None and not re.match(r"^\d+[\.\)]", text):
                pre_question_buffer.append(f"<p>{text}</p>")
                continue

            # --------------------------- START OF QUESTION --------------------------
            if re.match(r"^\d+[\.\)]", text):

                # close previous question
                if current_question:
                    # merge any extra content collected after question
                    if extra_html_parts:
                        if current_question["extra_content"]:
                            current_question["extra_content"] += ''.join(extra_html_parts)
                        else:
                            current_question["extra_content"] = ''.join(extra_html_parts)
                    extra_html_parts = []

                    # validate and save
                    if current_question.get("question") and current_question.get("answer") in ["a", "b", "c", "d"]:
                        questions.append(current_question)
                    else:
                        skipped += 1

                # extract marks
                marks_match = re.search(r"\((\d+)\s?(?:mks|marks?)\)", text, re.IGNORECASE)
                marks = int(marks_match.group(1)) if marks_match else 1

                clean_text = re.sub(r"\s*\(\d+\s?(?:mks|marks?)\)", "", text)
                question_text = re.sub(r"^\d+[\.\)]\s*", "", clean_text)

                # create new question
                current_question = {
                    "question": question_text,
                    "a": "", "b": "", "c": "", "d": "",
                    "answer": "",
                    "extra_content": None,
                    "image": None,
                    "marks": marks
                }

                # ATTACH CASE STUDY BEFORE QUESTION
                if pre_question_buffer:
                    current_question["extra_content"] = ''.join(pre_question_buffer)
                    pre_question_buffer = []

            # --------------------------- OPTION (A,B,C,D) ---------------------------
            elif re.match(r"^\(?[a-dA-D][\.\)]", text):
                match = re.match(r"^\(?([a-dA-D])[\.\)]\s*(.+)", text)
                if match and current_question:
                    label = match.group(1).lower()
                    current_question[label] = match.group(2).strip()

            # --------------------------- ANSWER LINE ------------------------------
            elif re.match(r"^(answer|correct answer):", text, re.IGNORECASE):
                match = re.search(r":\s*([a-dA-D])", text, re.IGNORECASE)
                if match and current_question:
                    current_question["answer"] = match.group(1).lower()

            # --------------------------- EXTRA CONTENT -----------------------------
            else:
                extra_html_parts.append(f"<p>{text}</p>")

        # ------------------------------ TABLE --------------------------------
        elif isinstance(block, Table):
            table_html = extract_table_html(block)

            if current_question:
                if current_question.get("extra_content"):
                    current_question["extra_content"] += table_html
                else:
                    current_question["extra_content"] = table_html
            else:
                # Table before question → case study
                pre_question_buffer.append(table_html)

    # ---------------------- FINAL QUESTION SAVE --------------------------
    if current_question:
        if extra_html_parts:
            if current_question["extra_content"]:
                current_question["extra_content"] += ''.join(extra_html_parts)
            else:
                current_question["extra_content"] = ''.join(extra_html_parts)

        if current_question.get("question") and current_question.get("answer") in ["a", "b", "c", "d"]:
            questions.append(current_question)
        else:
            skipped += 1

    return questions


# ==========================================================
# FIX FOR RENDER: Missing get_quiz_status()
# ==========================================================
def get_quiz_status(user_id):
    """Simple placeholder so imports do NOT break Render."""
    return "active"


# ==========================================================
# Google Drive Helpers
# ==========================================================
from urllib.parse import urlparse, parse_qs

def extract_drive_id(url: str):
    if not url:
        return None

    m = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    if m:
        return m.group(1)

    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        if 'id' in qs:
            return qs['id'][0]
    except:
        pass

    return None


def get_drive_embed_url(file_id: str):
    return f"https://drive.google.com/file/d/{file_id}/preview"
