import argparse
import sys
import os
import json
from dotenv import load_dotenv

load_dotenv()

from backend.static_analysis import run_all, format_for_prompt
from backend.agent import run_agent

# ANSI colors
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
GREEN  = "\033[92m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

SEVERITY_ICON = {
    "critical": "🔴",
    "high":     "🟠",
    "medium":   "🟡",
    "low":      "🔵",
}

SEVERITY_COLOR = {
    "critical": RED,
    "high":     RED,
    "medium":   YELLOW,
    "low":      BLUE,
}

QUALITY_COLOR = {
    "poor":      RED,
    "fair":      YELLOW,
    "good":      GREEN,
    "excellent": GREEN,
}


def print_report(report, filename):
    issues  = report.get("issues", [])
    summary = report.get("summary", {})
    quality = summary.get("overall_quality", "unknown")

    print(f"\n{BOLD}{'═' * 60}{RESET}")
    print(f"{BOLD}  CODE REVIEW — {os.path.basename(filename)}{RESET}")
    print(f"{BOLD}{'═' * 60}{RESET}\n")

    q_color = QUALITY_COLOR.get(quality, RESET)
    print(f"  {BOLD}Overall Quality:{RESET} {q_color}{quality.upper()}{RESET}")
    print(f"  {BOLD}Issues:{RESET} {summary.get('total', len(issues))}  "
          f"({RED}Critical: {summary.get('critical',0)}{RESET}  "
          f"{RED}High: {summary.get('high',0)}{RESET}  "
          f"{YELLOW}Medium: {summary.get('medium',0)}{RESET}  "
          f"{BLUE}Low: {summary.get('low',0)}{RESET})")

    concerns = summary.get("top_concerns", [])
    if concerns:
        print(f"\n  {BOLD}Top Concerns:{RESET}")
        for c in concerns:
            print(f"    • {c}")

    print(f"\n{BOLD}{'─' * 60}{RESET}")
    print(f"{BOLD}  ISSUES FOUND{RESET}")
    print(f"{BOLD}{'─' * 60}{RESET}\n")

    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_issues = sorted(issues, key=lambda x: order.get(x.get("severity", "low"), 4))

    for issue in sorted_issues:
        sev     = issue.get("severity", "low")
        icon    = SEVERITY_ICON.get(sev, "⚪")
        color   = SEVERITY_COLOR.get(sev, RESET)
        line    = issue.get("line")
        cat     = issue.get("category", "")
        title   = issue.get("title", "")
        explain = issue.get("explanation", "")
        suggest = issue.get("suggestion", "")

        line_str = f"Line {line}" if line else "General"

        print(f"  {icon} {BOLD}{color}[{sev.upper()}]{RESET} {BOLD}{title}{RESET}")
        print(f"     {DIM}{line_str} · {cat}{RESET}")
        print(f"     {explain}")
        if suggest:
            print(f"     {CYAN}↳ Fix:{RESET} {suggest}")
        print()

    print(f"{BOLD}{'═' * 60}{RESET}\n")


def main():
    parser = argparse.ArgumentParser(description="AI Code Review Agent")
    parser.add_argument("file", help="Python file to review")
    parser.add_argument("--json", action="store_true", help="Also save JSON report")
    args = parser.parse_args()

    filepath = os.path.abspath(args.file)
    if not os.path.exists(filepath):
        print(f"Error: file not found: {filepath}")
        sys.exit(1)

    print(f"\n🔍 Reviewing: {filepath}")
    print("─" * 50)

    print("⚙️  Running static analysis...")
    static_issues = run_all(filepath)
    print(f"   → {len(static_issues)} issues found")

    static_text = format_for_prompt(static_issues)

    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()

    print("🤖 Running AI agent...")
    report = run_agent(code, static_text)

    print_report(report, filepath)

    if args.json:
        os.makedirs("reports", exist_ok=True)
        out = f"reports/{os.path.splitext(os.path.basename(filepath))[0]}_review.json"
        with open(out, "w") as f:
            json.dump(report, f, indent=2)
        print(f"📄 JSON saved: {out}")


if __name__ == "__main__":
    main()