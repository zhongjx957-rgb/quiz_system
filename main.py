"""FastAPI 主入口"""

import json
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from pdf_parser import extract_text_from_pdf, parse_questions

app = FastAPI(title="自测题目系统")

# 目录配置
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"
QUESTIONS_FILE = DATA_DIR / "questions.json"

UPLOAD_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)


def _save_questions(questions: list[dict]):
    """保存题目到 JSON 文件"""
    with open(QUESTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)


def _load_questions() -> list[dict]:
    """从 JSON 文件加载题目"""
    if not QUESTIONS_FILE.exists():
        return []
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/", response_class=HTMLResponse)
async def index():
    """返回前端页面"""
    html_path = BASE_DIR / "static" / "index.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="前端页面未找到")
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """上传 PDF 文件，解析并返回题目"""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="只支持 PDF 文件")

    # 保存上传文件
    file_id = uuid.uuid4().hex[:8]
    pdf_path = UPLOAD_DIR / f"{file_id}_{file.filename}"
    content = await file.read()
    with open(pdf_path, "wb") as f:
        f.write(content)

    # 解析 PDF
    try:
        text = extract_text_from_pdf(str(pdf_path))
        questions = parse_questions(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 解析失败: {str(e)}")

    if not questions:
        raise HTTPException(status_code=400, detail="未能从 PDF 中提取到任何题目")

    # 保存题目
    _save_questions(questions)

    return {"count": len(questions), "questions": questions}


@app.get("/api/questions")
async def get_questions():
    """获取已提取的题目"""
    questions = _load_questions()
    if not questions:
        return {"count": 0, "questions": []}
    return {"count": len(questions), "questions": questions}


@app.post("/api/parse-local")
async def parse_local_pdf():
    """解析项目目录下已有的 PDF 文件"""
    pdf_files = list(BASE_DIR.glob("*.pdf"))
    if not pdf_files:
        raise HTTPException(status_code=404, detail="未找到 PDF 文件")

    all_questions = []
    for pdf_path in pdf_files:
        try:
            text = extract_text_from_pdf(str(pdf_path))
            questions = parse_questions(text)
            all_questions.extend(questions)
        except Exception as e:
            print(f"解析 {pdf_path.name} 失败: {e}")

    if not all_questions:
        raise HTTPException(status_code=400, detail="未能从 PDF 中提取到任何题目")

    _save_questions(all_questions)

    return {"count": len(all_questions), "questions": all_questions}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
