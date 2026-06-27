import subprocess
import json
import sys
import os
import urllib.request
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

MODEL = "llama-3.3-70b-versatile"

# ============================================================
# TOOLS — fonctions que l'agent peut appeler
# ============================================================

def read_file(filepath: str) -> str:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"ERROR: fichier '{filepath}' introuvable"
    except Exception as e:
        return f"ERROR: {str(e)}"


def run_pylint(filepath: str) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "pylint", filepath, "--output-format=json"],
        capture_output=True, text=True
    )
    try:
        data = json.loads(result.stdout)
        if not data:
            return "No issues found by pylint."
        lines = []
        for r in data:
            lines.append(f"Line {r['line']} [{r['type'].upper()}] {r['message']} ({r['message-id']})")
        return "\n".join(lines)
    except Exception:
        return "pylint returned no output."


def run_bandit(filepath: str) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "bandit", filepath, "-f", "json", "-q"],
        capture_output=True, text=True
    )
    try:
        data = json.loads(result.stdout)
        results = data.get("results", [])
        if not results:
            return "No security issues found by bandit."
        lines = []
        for r in results:
            lines.append(
                f"Line {r['line_number']} [{r['issue_severity']}] {r['issue_text']} ({r['test_id']})"
            )
        return "\n".join(lines)
    except Exception:
        return "bandit returned no output."


def run_flake8(filepath: str) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "flake8", filepath],
        capture_output=True, text=True
    )
    output = result.stdout.strip()
    return output if output else "No style issues found by flake8."


def fetch_github_pr(pr_url: str) -> str:
    try:
        parts = pr_url.replace("https://github.com/", "").split("/")
        owner, repo, _, pr_number = parts[0], parts[1], parts[2], parts[3]
        api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        req = urllib.request.Request(
            api_url,
            headers={
                "Accept": "application/vnd.github.v3.diff",
                "User-Agent": "code-review-agent"
            }
        )
        with urllib.request.urlopen(req) as response:
            return response.read().decode("utf-8")
    except Exception as e:
        return f"ERROR: impossible de fetcher la PR — {str(e)}"


# ============================================================
# TOOL DEFINITIONS — ce qu'on donne au LLM
# ============================================================

TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a local Python file. Use this first to read the code before reviewing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to the Python file"}
                },
                "required": ["filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_pylint",
            "description": "Run Pylint on a Python file. Detects style issues, unused imports, bad practices.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to the Python file"}
                },
                "required": ["filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_bandit",
            "description": "Run Bandit on a Python file. Detects security vulnerabilities: hardcoded passwords, SQL injection, dangerous functions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to the Python file"}
                },
                "required": ["filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_flake8",
            "description": "Run Flake8 on a Python file. Detects PEP8 style violations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to the Python file"}
                },
                "required": ["filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_github_pr",
            "description": "Fetch the diff of a GitHub Pull Request. Use when input is a GitHub PR URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pr_url": {"type": "string", "description": "Full GitHub PR URL e.g. https://github.com/owner/repo/pull/123"}
                },
                "required": ["pr_url"]
            }
        }
    }
]


# ============================================================
# DISPATCHER — execute the tool the LLM chose
# ============================================================

def execute_tool(tool_name: str, tool_args: dict) -> str:
    print(f"    🔧 Calling tool: {tool_name}({tool_args})")
    if tool_name == "read_file":
        return read_file(tool_args["filepath"])
    elif tool_name == "run_pylint":
        return run_pylint(tool_args["filepath"])
    elif tool_name == "run_bandit":
        return run_bandit(tool_args["filepath"])
    elif tool_name == "run_flake8":
        return run_flake8(tool_args["filepath"])
    elif tool_name == "fetch_github_pr":
        return fetch_github_pr(tool_args["pr_url"])
    else:
        return f"ERROR: unknown tool '{tool_name}'"


# ============================================================
# AGENT LOOP — the LLM decides what to do next
# ============================================================

SYSTEM_PROMPT = """You are an expert senior software engineer performing a thorough code review.

You have access to tools: read_file, run_pylint, run_bandit, run_flake8, fetch_github_pr.

Your workflow:
1. If given a file path → use read_file, then run_pylint, run_bandit, run_flake8
2. If given a GitHub PR URL → use fetch_github_pr to get the diff
3. Analyze everything and produce a final structured report

Your final response MUST be a JSON object only, no markdown:
{
  "issues": [
    {
      "line": <int or null>,
      "severity": <"critical"|"high"|"medium"|"low">,
      "category": <"security"|"bug"|"performance"|"style"|"maintainability">,
      "title": <short title>,
      "explanation": <why this is a problem>,
      "suggestion": <concrete fix with code example>,
      "source": <"llm"|"pylint"|"bandit"|"flake8">
    }
  ],
  "summary": {
    "total": <int>,
    "critical": <int>,
    "high": <int>,
    "medium": <int>,
    "low": <int>,
    "overall_quality": <"poor"|"fair"|"good"|"excellent">,
    "top_concerns": [<3 most important issues>]
  }
}"""


def run_tool_calling_agent(input_path: str) -> dict:
    """
    Agentic loop: LLM decides which tools to call, we execute them,
    feed results back, until LLM produces the final report.
    """
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Please review this: {input_path}"}
    ]

    print("  🤖 Agent started — LLM is deciding what to do...\n")

    MAX_ITERATIONS = 10
    for iteration in range(MAX_ITERATIONS):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS_DEFINITIONS,
            tool_choice="auto",
            max_tokens=4000,
            temperature=0.2,
        )

        message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        # LLM wants to call tools
        if finish_reason == "tool_calls" and message.tool_calls:
            messages.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]
            })

            # Execute each tool the LLM requested
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                result = execute_tool(tool_name, tool_args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(result)
                })

        # LLM is done — extract final JSON report
        else:
            print("\n  ✅ Agent finished reasoning\n")
            content = message.content or ""
            # Clean markdown fences if present
            import re
            clean = re.sub(r"```(?:json)?", "", content).strip().rstrip("```").strip()
            try:
                return json.loads(clean)
            except Exception:
                match = re.search(r'(\{[\s\S]*\})', clean)
                if match:
                    return json.loads(match.group(1))
                return {"issues": [], "summary": {"overall_quality": "unknown", "total": 0}}

    return {"issues": [], "summary": {"overall_quality": "unknown", "total": 0}}


# Quick test
if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "examples/buggy_code.py"
    report = run_tool_calling_agent(target)
    print(json.dumps(report, indent=2))