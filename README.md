# 🔍 Code Review Agent

An AI-powered code review agent that analyzes Python code like a senior developer would combining static analysis tools with a tool-calling LLM agent to produce structured, actionable feedback.

---

## 🧠 How It Works

Instead of just asking an LLM "find bugs in this code", this agent uses a **tool-calling architecture**:

1. The LLM receives the file path or GitHub PR URL
2. It **decides by itself** which tools to call and in what order
3. Tools run: `read_file` → `run_pylint` → `run_bandit` → `run_flake8`
4. The LLM reasons over all results and produces a structured report
5. A post-processing layer enforces correct severity levels
Input (file path or GitHub PR URL)

│

▼

Tool-Calling Agent (Groq — llama-3.3-70b-versatile)

│

├── 🔧 read_file        → reads the source code

├── 🔧 run_pylint       → style, unused vars, bad practices

├── 🔧 run_bandit       → security vulnerabilities

└── 🔧 run_flake8       → PEP8 violations

│

▼

Structured Report (severity + explanation + fix)

---

## 🛠️ Tools & Technologies

| Layer | Technology |
|---|---|
| LLM | Groq API — `llama-3.3-70b-versatile` |
| Agent architecture | Tool calling (function calling) |
| Security scanner | Bandit |
| Linter | Pylint + Flake8 |
| Backend API | FastAPI |
| Frontend | HTML + Vanilla JS |
| CLI | Python argparse |

---

## 🚀 How to Run

### 1. Clone the repo
```bash
git clone https://github.com/ikramhadjmohamed/code-review-agent.git
cd code-review-agent
```

### 2. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up your API key
Create a `.env` file:
GROQ_API_KEY=your_groq_api_key_here

### 5. Run via CLI
```bash
python review.py examples/buggy_code.py
```

### 6. Run via Web UI
Terminal 1:
```bash
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8001
```
Terminal 2:
```bash
python -m http.server 3000
```
Open: `http://localhost:3000/report.html`

---

## 📊 Example Report

**Input:** `examples/buggy_code.py`

**Output:**
Overall Quality: POOR

🔴 Critical: 1  🟠 High: 1  🟡 Medium: 0  🔵 Low: 5
🔴 [CRITICAL] SQL Injection Vulnerability — Line 9

The query is built using string concatenation, making it vulnerable.

↳ Fix: Use parameterized queries: cursor.execute(query, (username,))
🟠 [HIGH] Hardcoded Password — Line 4

PASSWORD = "admin123" is exposed in source code.

↳ Fix: Use os.environ.get("PASSWORD") instead
🔵 [LOW] Bare Except — Line 23

Catches all exceptions, masking real bugs.

↳ Fix: Use except ZeroDivisionError: instead

---

## 📁 Project Structure
code-review-agent/

├── backend/

│   ├── tools_agent.py    # Tool-calling agent (main logic)

│   ├── static_analysis.py # Pylint + Flake8 + Bandit runners

│   └── api.py            # FastAPI backend

├── examples/

│   └── buggy_code.py     # Example file with intentional bugs

├── review.py             # CLI entrypoint

├── report.html           # Web UI

├── .env                  # API keys (not committed)

└── README.md

---

## ⚡ What Makes It "Agentic"

The key difference from a simple LLM wrapper:

- **The LLM decides which tools to call** — it's not hardcoded
- **Tool results feed back into the conversation** — multi-turn reasoning
- **Post-processing layer** enforces severity consistency
- **Supports GitHub PRs** via `fetch_github_pr` tool

---

## 🔧 Challenges & Improvements

**Challenges:**
- LLM severity ratings were inconsistent → solved with keyword-based post-processing
- CORS issues between frontend and backend → solved with FastAPI middleware
- Tool-calling loop needed careful message history management

**With more time:**
- Add support for JavaScript, Java, and other languages
- GitHub Action that comments directly on PRs
- Fine-tune severity classification with a dedicated ML model
- Add a diff view showing exactly where issues appear in the code