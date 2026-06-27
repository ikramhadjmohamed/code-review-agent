import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

MODEL = "llama-3.3-70b-versatile"


def _get_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in .env")
    return Groq(api_key=api_key)


def _call_groq(client, system, user):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        temperature=0.2,
        max_tokens=4000,
    )
    return response.choices[0].message.content.strip()


def _extract_json(text):
    clean = re.sub(r"```(?:json)?", "", text).strip().rstrip("```").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r'(\[[\s\S]*\]|\{[\s\S]*\})', clean)
        if match:
            return json.loads(match.group(1))
        raise ValueError(f"Could not parse JSON from LLM response")


STEP1_SYSTEM = """You are a senior software engineer doing a code review.
Find ALL issues: bugs, security vulnerabilities, bad practices, logic errors, naming problems.

Respond ONLY with a JSON array. No markdown, no explanation.
Each element must have exactly:
{
  "line": <integer or null>,
  "severity": <"critical"|"high"|"medium"|"low">,
  "category": <"security"|"bug"|"performance"|"style"|"maintainability">,
  "title": <short title>,
  "explanation": <why this is a problem>,
  "suggestion": <concrete fix with code example>
}"""

STEP1_USER = """Review this Python code. 
Static analysis already found these (don't duplicate, just reference them):

{static_findings}

Code:
````python
{code}
```"""


STEP2_SYSTEM = """You are a senior software engineer doing a final review pass.
You have issues found in step 1. Your job:
1. Remove false positives
2. Make sure severity ratings are accurate
3. Ensure every issue has a clear actionable suggestion
4. Add "source": "llm" for issues you found

Respond ONLY with a JSON object:
{
  "issues": [...],
  "summary": {
    "total": <int>,
    "critical": <int>,
    "high": <int>,
    "medium": <int>,
    "low": <int>,
    "overall_quality": <"poor"|"fair"|"good"|"excellent">,
    "top_concerns": [<3 most important issues as short strings>]
  }
}"""

STEP2_USER = """Refine these issues and produce the final report.

Static analysis findings:
{static_findings}

Issues from step 1:
{llm_issues}"""


def run_agent(code, static_findings_text):
    client = _get_client()

    print("  [Step 1] LLM finding issues...")
    step1_response = _call_groq(
        client, STEP1_SYSTEM,
        STEP1_USER.format(static_findings=static_findings_text, code=code)
    )
    step1_issues = _extract_json(step1_response)

    print("  [Step 2] LLM refining and scoring...")
    step2_response = _call_groq(
        client, STEP2_SYSTEM,
        STEP2_USER.format(
            static_findings=static_findings_text,
            llm_issues=json.dumps(step1_issues, indent=2)
        )
    )
    final_report = _extract_json(step2_response)
    return final_report


# Quick test
if __name__ == "__main__":
    from backend.static_analysis import run_all, format_for_prompt

    filepath = "examples/buggy_code.py"
    with open(filepath, "r") as f:
        code = f.read()

    issues = run_all(filepath)
    static_text = format_for_prompt(issues)

    print("Running agent...\n")
    report = run_agent(code, static_text)
    print("\nFinal report:")
    print(json.dumps(report, indent=2))
