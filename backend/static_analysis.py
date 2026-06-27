import subprocess
import json
import re


def run_bandit(filepath):
    issues = []
    result = subprocess.run(
        ["bandit", "-f", "json", "-q", filepath],
        capture_output=True, text=True
    )
    if not result.stdout.strip():
        return issues
    data = json.loads(result.stdout)
    for r in data.get("results", []):
        issues.append({
            "line": r["line_number"],
            "severity": r["issue_severity"].lower(),
            "category": "security",
            "code": r["test_id"],
            "message": r["issue_text"],
            "tool": "bandit"
        })
    return issues


def run_pylint(filepath):
    issues = []
    result = subprocess.run(
        ["pylint", "--output-format=json", filepath],
        capture_output=True, text=True
    )
    if not result.stdout.strip():
        return issues
    data = json.loads(result.stdout)
    for r in data:
        issues.append({
            "line": r["line"],
            "severity": "high" if r["type"] == "error" else "medium" if r["type"] == "warning" else "low",
            "category": "bug" if r["type"] == "error" else "style",
            "code": r["message-id"],
            "message": r["message"],
            "tool": "pylint"
        })
    return issues


def run_flake8(filepath):
    issues = []
    result = subprocess.run(
        ["flake8", filepath],
        capture_output=True, text=True
    )
    for line in result.stdout.strip().splitlines():
        m = re.match(r".+:(\d+):\d+:\s+([A-Z]\d+)\s+(.+)", line)
        if m:
            ln, code, msg = m.groups()
            issues.append({
                "line": int(ln),
                "severity": "medium" if code.startswith("E") else "low",
                "category": "style",
                "code": code,
                "message": msg.strip(),
                "tool": "flake8"
            })
    return issues


def run_all(filepath):
    all_issues = run_bandit(filepath) + run_pylint(filepath) + run_flake8(filepath)
    return sorted(all_issues, key=lambda x: x["line"])


def format_for_prompt(issues):
    if not issues:
        return "No issues found by static analysis."
    lines = ["Static analysis findings:"]
    for i in issues:
        lines.append(f"  Line {i['line']} [{i['severity'].upper()}] [{i['tool']}/{i['code']}] {i['message']}")
    return "\n".join(lines)


# Quick test
if __name__ == "__main__":
    import sys
    filepath = sys.argv[1] if len(sys.argv) > 1 else "examples/buggy_code.py"
    issues = run_all(filepath)
    print(f"\nFound {len(issues)} issues:\n")
    for i in issues:
        print(f"  Line {i['line']} [{i['severity'].upper()}] {i['message']} ({i['tool']})")