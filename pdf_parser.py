"""PDF 解析 + 正则提取题目模块"""

import re
from typing import Optional

import pdfplumber


def extract_text_from_pdf(pdf_path: str) -> str:
    """从 PDF 文件中提取全部文本"""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def parse_questions(text: str) -> list[dict]:
    """从文本中用正则提取题目列表"""
    questions = []

    # 策略：先找到所有答案行，再向前找对应的题号
    # 答案行格式：答案：B / 答案：ACD / 答案：错误
    answer_pattern = re.compile(r'答案[：:]\s*(.+?)(?:\n|$)')
    answer_matches = list(answer_pattern.finditer(text))

    for i, answer_match in enumerate(answer_matches):
        # 当前答案行的位置
        answer_end = answer_match.end()
        # 上一道题答案行的位置（或文本开头）
        prev_end = answer_matches[i - 1].end() if i > 0 else 0

        # 在上一道题和当前答案行之间找题号
        block = text[prev_end:answer_end]
        answer_text = answer_match.group(1).strip()

        question = _parse_block(block, answer_text)
        if question:
            questions.append(question)

    return questions


def _parse_block(block: str, answer_text: str) -> Optional[dict]:
    """解析单个题目块（从上一题答案后到当前答案行）"""
    # 找题号：必须在行首出现 "数字+分隔符"
    id_match = re.search(r'(?:^|\n)(\d+)[、.．]\s*', block)
    if not id_match:
        return None

    q_id = int(id_match.group(1))
    # 跳过太大的题号（如 "2026" 来自标题 "2026.7"）
    if q_id > 10000:
        return None

    content = block[id_match.end():].strip()

    # 提取选项
    options = _extract_options(content)

    # 提取题干
    question_text = _extract_question_text(content)

    if not question_text:
        return None

    # 判断题目类型
    q_type, answer_list = _determine_type_and_answer(answer_text, options)

    result = {
        "id": q_id,
        "type": q_type,
        "question": question_text,
        "answer": answer_list,
    }

    if options:
        result["options"] = options

    return result


def _extract_options(text: str) -> dict[str, str]:
    """从题目文本中提取选项"""
    options = {}
    # 匹配选项: A、 B、 C、 D、 等
    option_pattern = re.compile(r'([A-Z])[、.．]\s*(.+?)(?=(?:\n\s*[A-Z][、.．])|$)', re.DOTALL)
    for match in option_pattern.finditer(text):
        key = match.group(1)
        value = match.group(2).strip().replace('\n', ' ')
        if key in 'ABCDEFGHIJKLMNOP':
            options[key] = value
    return options


def _extract_question_text(text: str) -> str:
    """提取题干（去掉选项部分）"""
    # 找到第一个选项的位置
    first_option = re.search(r'(?:^|\n)[A-Z][、.．]', text)
    if first_option:
        return text[:first_option.start()].strip().replace('\n', ' ')
    return text.strip().replace('\n', ' ')


def _determine_type_and_answer(answer_text: str, options: dict) -> tuple[str, list[str]]:
    """判断题目类型并规范化答案"""
    answer_text = answer_text.strip()

    # 判断题
    if answer_text in ('对', '正确', '√', 'T', 'true'):
        return 'true_false', ['对']
    if answer_text in ('错', '错误', '×', 'F', 'false'):
        return 'true_false', ['错']

    # 提取答案字母
    letters = re.findall(r'[A-Z]', answer_text.upper())

    if len(letters) > 1:
        return 'multiple', letters
    elif len(letters) == 1:
        return 'single', letters
    else:
        return 'single', [answer_text]
