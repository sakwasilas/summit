import os
import re
import logging
from docx import Document
from docx.oxml.ns import qn
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import Table
from docx.text.paragraph import Paragraph
from urllib.parse import urlparse, parse_qs

logging.basicConfig(level=logging.INFO)

DEFAULT_IMAGE_DIR = "static/question_images"

# ---------------------
# Helper: table -> html
# ---------------------
def extract_table_html(table: Table) -> str:
    html = "<table border='1' cellspacing='0' cellpadding='5'>"
    for row in table.rows:
        html += "<tr>"
        for cell in row.cells:
            html += f"<td>{cell.text.strip()}</td>"
        html += "</tr>"
    html += "</table>"
    return html

# --------------------------------
# Helper: save image from a run
# --------------------------------
def save_image_from_run(run, output_dir, image_counter):
    blip_elements = run._element.findall('.//a:blip', namespaces={
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
    })

    if not blip_elements:
        return None

    rId = blip_elements[0].get(qn('r:embed'))
    image_part = run.part.related_parts.get(rId)
    if not image_part:
        return None

    image_data = image_part.blob
    image_filename = f"question_image_{image_counter}.png"
    os.makedirs(output_dir, exist_ok=True)
    image_path = os.path.join(output_dir, image_filename)
    with open(image_path, 'wb') as f:
        f.write(image_data)

    return image_filename

# --------------------------------
# Helper: iterate blocks in order
# --------------------------------
def iter_block_items(parent):
    for child in parent.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)

# --------------------------------------------------
# Main parser: robust to inline options + inline answers
# --------------------------------------------------
def parse_docx_questions(file_stream, image_output_dir=DEFAULT_IMAGE_DIR):
    """
    Parse a .docx file into:
      - case_study_html: everything before question 1 (paragraphs + tables + images)
      - questions: list of dicts: {question, a,b,c,d, answer, extra_content, image, marks}
    Works with:
      - questions where options are inline: "1. What... (2mks) A. optA B. optB C. optC D. optD Answer: B"
      - questions where options are on separate lines
      - Answer: X either inline or on its own line
    """
    document = Document(file_stream)

    os.makedirs(image_output_dir, exist_ok=True)

    case_study_html = ""
    questions = []
    current_question = None
    extra_html_parts = []
    image_counter = 0
    skipped = 0

    # helper: commit current_question into questions list
    def commit_current():
        nonlocal current_question, extra_html_parts, skipped
        if not current_question:
            return
        # attach accumulated extra_html_parts if any
        if extra_html_parts:
            existing = current_question.get("extra_content") or ""
            current_question["extra_content"] = existing + ''.join(extra_html_parts)
        # validate answer
        if current_question.get("question") and current_question.get("answer") in ["a","b","c","d"]:
            questions.append(current_question)
        else:
            skipped += 1
        current_question = None
        extra_html_parts = []

    # iterate through blocks
    for block in iter_block_items(document):
        # -------------------------
        # Paragraph handling
        # -------------------------
        if isinstance(block, Paragraph):
            para = block
            text = para.text.strip()

            # extract images in this paragraph (attach to case study or current question)
            for run in para.runs:
                image_name = save_image_from_run(run, image_output_dir, image_counter + 1)
                if image_name:
                    image_counter += 1
                    # if we haven't started questions yet -> case study
                    if current_question is None:
                        case_study_html += f"<img src='/static/question_images/{image_name}' /><br>"
                    else:
                        # attach to the question (if not set yet, set as first image)
                        if not current_question.get("image"):
                            current_question["image"] = image_name
                        else:
                            # multiple images: append to extra_content
                            current_question["extra_content"] = (current_question.get("extra_content") or '') + f"<img src='/static/question_images/{image_name}' /><br>"

            if not text:
                continue

            # If the paragraph contains a numbered question at any point (start)
            q_match = re.match(r"^\s*(\d+)[\.\)]\s*(.*)", text)
            if q_match:
                # commit previous question
                commit_current()

                # full text after the leading number
                after_num = q_match.group(2).strip()

                # extract marks if present, e.g. (2mks) or (2 marks)
                marks_match = re.search(r"\((\d+)\s*(?:mks|marks?)\)", after_num, re.IGNORECASE)
                marks = int(marks_match.group(1)) if marks_match else 1
                # remove marks from the text for question content
                if marks_match:
                    after_num = after_num[:marks_match.start()] + after_num[marks_match.end():]
                    after_num = after_num.strip()

                # prepare new question dict
                current_question = {
                    "question": None,
                    "a": "", "b": "", "c": "", "d": "",
                    "answer": "",
                    "extra_content": "",
                    "image": None,
                    "marks": marks
                }

                # -- Now handle possibility that options & answer appear inline in the same paragraph.
                # Example inline: "What is a computer (2mks) A. Digital machine B. ... Answer: A"
                # Strategy:
                # 1. Find any 'Answer: X' tokens and extract the correct answer.
                inline_answer_match = re.search(r"(?:Answer|Correct Answer)\s*[:\-]\s*([A-Da-d])", after_num, re.IGNORECASE)
                if inline_answer_match:
                    current_question["answer"] = inline_answer_match.group(1).lower()
                    # remove the Answer: token from the text so it doesn't pollute options
                    after_num = re.sub(r"(?:Answer|Correct Answer)\s*[:\-]\s*[A-Da-d]\s*", "", after_num, flags=re.IGNORECASE).strip()

                # 2. Find option markers (A., B., C., D.) and split content between them.
                # Use regex to find all option label positions
                option_iter = list(re.finditer(r"\b([A-Da-d])\.\s*", after_num))
                if option_iter:
                    # the part before the first option is the question text
                    first_opt_pos = option_iter[0].start()
                    question_text = after_num[:first_opt_pos].strip()
                    current_question["question"] = question_text if question_text else ""
                    # now extract option bodies by slicing between option markers
                    for i, m in enumerate(option_iter):
                        label = m.group(1).lower()
                        start = m.end()
                        end = option_iter[i+1].start() if i+1 < len(option_iter) else len(after_num)
                        opt_text = after_num[start:end].strip()
                        # remove any stray inline "Answer: X" within option text
                        opt_text = re.sub(r"(?:Answer|Correct Answer)\s*[:\-]\s*[A-Da-d]\s*", "", opt_text, flags=re.IGNORECASE).strip()
                        current_question[label] = opt_text
                else:
                    # no inline options: the whole after_num is the question text
                    current_question["question"] = after_num

                continue  # done with this paragraph

            # --------------------------------------------------
            # Option line on its own (e.g., "A. Option text")
            # --------------------------------------------------
            opt_match = re.match(r"^\s*\(?([A-Da-d])[\.\)]\s*(.+)", text)
            if opt_match and current_question:
                label = opt_match.group(1).lower()
                content = opt_match.group(2).strip()
                # strip any inline 'Answer: X' from option content
                content = re.sub(r"(?:Answer|Correct Answer)\s*[:\-]\s*[A-Da-d]\s*", "", content, flags=re.IGNORECASE).strip()
                current_question[label] = content
                continue

            # --------------------------------------------------
            # Answer line on its own (e.g., "Answer: B")
            # --------------------------------------------------
            ans_match = re.search(r"(?:Answer|Correct Answer)\s*[:\-]\s*([A-Da-d])", text, re.IGNORECASE)
            if ans_match:
                if current_question:
                    current_question["answer"] = ans_match.group(1).lower()
                else:
                    # If found before any question, treat it as noise: append to case study
                    case_study_html += f"<p>{text}</p>"
                continue

            # --------------------------------------------------
            # Paragraphs before first question -> case study
            # --------------------------------------------------
            if current_question is None:
                case_study_html += f"<p>{text}</p>"
                continue

            # --------------------------------------------------
            # anything else while inside a question -> extra content
            # --------------------------------------------------
            if current_question:
                extra_html_parts.append(f"<p>{text}</p>")
                continue

        # -------------------------
        # Table handling
        # -------------------------
        elif isinstance(block, Table):
            table_html = extract_table_html(block)
            if current_question is None:
                case_study_html += table_html
            else:
                current_question["extra_content"] = (current_question.get("extra_content") or '') + table_html
            continue

    # end for blocks

    # commit last question
    if current_question:
        # attach leftover extra_html_parts
        if extra_html_parts:
            current_question["extra_content"] = (current_question.get("extra_content") or '') + ''.join(extra_html_parts)
        if current_question.get("question") and current_question.get("answer") in ["a","b","c","d"]:
            questions.append(current_question)
        else:
            skipped += 1

    logging.info(f"Parsed {len(questions)} valid questions. Skipped: {skipped}")
    # return both case study and questions for caller
    return {"case_study_html": case_study_html, "questions": questions}

# -------------------------------
# Google Drive helpers (unchanged)
# -------------------------------
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
    except Exception:
        pass
    return None

def get_drive_embed_url(file_id: str):
    return f"https://drive.google.com/file/d/{file_id}/preview"
