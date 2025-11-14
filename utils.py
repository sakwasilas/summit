import os
import re
from docx import Document
from docx.oxml.ns import qn
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import Table
from docx.text.paragraph import Paragraph
from urllib.parse import urlparse, parse_qs

DEFAULT_IMAGE_DIR = "static/question_images"


# ---------------------------------
# Table to HTML conversion
# ---------------------------------
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
    """Convert a docx table to HTML."""
    html = "<table border='1' cellspacing='0' cellpadding='5'>"
    for row in table.rows:
        html += "<tr>"
        for cell in row.cells:
            html += f"<td>{cell.text.strip()}</td>"
        html += "</tr>"
    html += "</table>"
    return html


def save_image_from_run(run, output_dir, image_counter):
    """Save images embedded in a run and return the filename."""
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


def iter_block_items(parent):
    """Iterate through paragraphs and tables in the document."""
    for child in parent.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def parse_docx_questions(file_stream, image_output_dir=DEFAULT_IMAGE_DIR):
    """Parse questions, options, answers, images, tables from a .docx file."""
    document = Document(file_stream)
    questions = []
    skipped = 0  # <--- initialize skipped here
    current_question = None
    extra_html_parts = []
    pre_question_buffer = []
    image_counter = 0

    os.makedirs(image_output_dir, exist_ok=True)

    for block in iter_block_items(document):

        if isinstance(block, Paragraph):
            para = block
            text = para.text.strip()

            # Extract images in paragraph runs
            for run in para.runs:
                image_name = save_image_from_run(run, image_output_dir, image_counter + 1)
                if image_name and current_question:
                    image_counter += 1
                    current_question["image"] = image_name

            if not text:
                continue

            # Case study / content before first question
            if current_question is None and not re.match(r"^\d+[\.\)]", text):
                pre_question_buffer.append(f"<p>{text}</p>")
                continue

            # Start of question
            if re.match(r"^\d+[\.\)]", text):

                # Close previous question
                if current_question:
                    if extra_html_parts:
                        if current_question["extra_content"]:
                            current_question["extra_content"] += ''.join(extra_html_parts)
                        else:
                            current_question["extra_content"] = ''.join(extra_html_parts)
                    extra_html_parts = []

                    if current_question.get("question") and current_question.get("answer") in ["a", "b", "c", "d"]:
                        questions.append(current_question)
                    else:
                        skipped += 1

                # Extract marks
                marks_match = re.search(r"\((\d+)\s?(?:mks|marks?)\)", text, re.IGNORECASE)
                marks = int(marks_match.group(1)) if marks_match else 1

                clean_text = re.sub(r"\s*\(\d+\s?(?:mks|marks?)\)", "", text)
                question_text = re.sub(r"^\d+[\.\)]\s*", "", clean_text)

                # Create new question
                current_question = {
                    "question": question_text,
                    "a": "", "b": "", "c": "", "d": "",
                    "answer": "",
                    "extra_content": None,
                    "image": None,
                    "marks": marks
                }

                # Attach pre-question content (case study)
                if pre_question_buffer:
                    current_question["extra_content"] = ''.join(pre_question_buffer)
                    pre_question_buffer = []

            # Options A-D
            elif re.match(r"^\(?[a-dA-D][\.\)]", text):
                match = re.match(r"^\(?([a-dA-D])[\.\)]\s*(.+)", text)
                if match and current_question:
                    label = match.group(1).lower()
                    current_question[label] = match.group(2).strip()

            # Answer line
            elif re.match(r"^(answer|correct answer):", text, re.IGNORECASE):
                match = re.search(r":\s*([a-dA-D])", text, re.IGNORECASE)
                if match and current_question:
                    current_question["answer"] = match.group(1).lower()

            # Extra content
            else:
                extra_html_parts.append(f"<p>{text}</p>")

        elif isinstance(block, Table):
            table_html = extract_table_html(block)

            if current_question:
                if current_question.get("extra_content"):
                    current_question["extra_content"] += table_html
                else:
                    current_question["extra_content"] = table_html
            else:
                pre_question_buffer.append(table_html)

    # Save last question
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


# ------------------------------
# Placeholder for Render deployment
# ------------------------------
def get_quiz_status(user_id):
    """Placeholder so import works on Render."""
    return "active"


# ------------------------------
# Google Drive helpers
# ------------------------------
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
