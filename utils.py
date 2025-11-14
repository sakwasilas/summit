import os
import re
from docx import Document
from docx.oxml.ns import qn
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import Table
from docx.text.paragraph import Paragraph

DEFAULT_IMAGE_DIR = "static/question_images"

# ----------------------------
# Helper functions
# ----------------------------
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

def iter_block_items(parent):
    """Yield paragraphs and tables from a document body"""
    for child in parent.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)

# ----------------------------
# Main parsing function
# ----------------------------
def parse_docx_questions(file_stream, image_output_dir=DEFAULT_IMAGE_DIR):
    document = Document(file_stream)
    questions = []
    skipped = 0
    current_question = None
    extra_html_parts = []
    pre_question_buffer = []  # Case study / content before first question
    image_counter = 0

    os.makedirs(image_output_dir, exist_ok=True)

    for block in iter_block_items(document):

        if isinstance(block, Paragraph):
            text = block.text.strip()
            if not text:
                continue

            # Handle images in the paragraph
            for run in block.runs:
                image_name = save_image_from_run(run, image_output_dir, image_counter + 1)
                if image_name and current_question:
                    image_counter += 1
                    current_question["image"] = image_name

            # Case study / content before first question
            if current_question is None and not re.match(r"^\d+[\.\)]", text):
                pre_question_buffer.append(f"<p>{text}</p>")
                continue

            # Start of a new question
            if re.match(r"^\d+[\.\)]", text):

                # Save previous question
                if current_question:
                    if extra_html_parts:
                        current_question["extra_content"] = (current_question.get("extra_content") or '') + ''.join(extra_html_parts)
                    extra_html_parts = []

                    if current_question.get("question") and current_question.get("answer") in ["a", "b", "c", "d"]:
                        questions.append(current_question)
                    else:
                        skipped += 1

                # Extract marks
                marks_match = re.search(r"\((\d+)\s?(?:mks|marks?)\)", text, re.IGNORECASE)
                marks = int(marks_match.group(1)) if marks_match else 1

                # Clean question text
                clean_text = re.sub(r"\s*\(\d+\s?(?:mks|marks?)\)", "", text)
                question_text = re.sub(r"^\d+[\.\)]\s*", "", clean_text)

                current_question = {
                    "question": question_text,
                    "a": "", "b": "", "c": "", "d": "",
                    "answer": "",
                    "extra_content": ''.join(pre_question_buffer) if pre_question_buffer else None,
                    "image": None,
                    "marks": marks
                }
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
                current_question["extra_content"] = (current_question.get("extra_content") or '') + table_html
            else:
                pre_question_buffer.append(table_html)

    # Save final question
    if current_question:
        if extra_html_parts:
            current_question["extra_content"] = (current_question.get("extra_content") or '') + ''.join(extra_html_parts)
        if current_question.get("question") and current_question.get("answer") in ["a", "b", "c", "d"]:
            questions.append(current_question)
        else:
            skipped += 1

    return questions, skipped
