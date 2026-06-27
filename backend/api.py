import os
import sys
import tempfile
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from backend.tools_agent import run_tool_calling_agent

app = FastAPI(title="Code Review Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CodeRequest(BaseModel):
    code: str
    filename: Optional[str] = "snippet.py"


class PRRequest(BaseModel):
    pr_url: str


@app.get("/health")
def health():
    return {"status": "ok", "model": "llama-3.3-70b-versatile"}


@app.post("/review/code")
async def review_code(request: CodeRequest):
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty")

    # Write to temp file so tools can run on it
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(request.code)
        tmp_path = tmp.name

    try:
        report = run_tool_calling_agent(tmp_path)
    finally:
        os.unlink(tmp_path)

    report["meta"] = {"filename": request.filename}
    return report


@app.post("/review/pr")
async def review_pr(request: PRRequest):
    if "github.com" not in request.pr_url:
        raise HTTPException(status_code=400, detail="Invalid GitHub PR URL")
    report = run_tool_calling_agent(request.pr_url)
    report["meta"] = {"pr_url": request.pr_url}
    return report


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000, reload=True)