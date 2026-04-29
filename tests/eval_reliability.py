"""
Reliability evaluator for PawPal+ AI Agent.

Runs scored scenarios against every tool handler without making Claude API calls.
Each scenario specifies the tool to call, the inputs, and a check function that
returns True (pass) or False (fail) and a short explanation.

Run with:
    python tests/eval_reliability.py

The script prints a category-by-category breakdown and an overall score, then
writes the same report to logs/eval_report.txt for archival.
"""

import sys
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Dict, Any, List, Tuple

# Make sure the project root is on sys.path when running from any directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_agent import PawPalAgent
from pawpal_system import Owner, Scheduler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fresh_agent() -> PawPalAgent:
    """Return a new agent with an empty owner."""
    owner = Owner(name="Eval Owner", available_hours_per_day=8.0)
    return PawPalAgent(owner=owner, scheduler=Scheduler(owner))


def agent_with_buddy() -> PawPalAgent:
    """Return an agent that already has one pet (Buddy)."""
    ag = fresh_agent()
    ag._tool_create_pet(name="Buddy", age=3, breed="Golden Retriever")
    return ag


# ---------------------------------------------------------------------------
# Scenario type
# ---------------------------------------------------------------------------

Scenario = Dict[str, Any]
# Keys: "name", "category", "run" (callable -> result), "check" (result -> (bool, str))


def scenario(name: str, category: str,
             run: Callable, check: Callable) -> Scenario:
    return {"name": name, "category": category, "run": run, "check": check}


def passed(explanation: str = "") -> Tuple[bool, str]:
    return True, explanation


def failed(explanation: str = "") -> Tuple[bool, str]:
    return False, explanation


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

SCENARIOS: List[Scenario] = [

    # ── Category 1: Input Handling ─────────────────────────────────────────

    scenario(
        name="Create pet returns 'created' status",
        category="Input Handling",
        run=lambda: fresh_agent()._tool_create_pet("Luna", 2, "Siamese"),
        check=lambda r: passed() if r.get("status") == "created" else failed(f"got {r}"),
    ),
    scenario(
        name="Duplicate pet name blocked",
        category="Input Handling",
        run=lambda: (lambda ag: (
            ag._tool_create_pet("Buddy", 3, "Lab"),
            ag._tool_create_pet("Buddy", 3, "Lab")
        )[-1])(fresh_agent()),
        check=lambda r: passed() if r.get("status") == "already_exists" else failed(f"got {r}"),
    ),
    scenario(
        name="Duplicate check is case-insensitive",
        category="Input Handling",
        run=lambda: (lambda ag: (
            ag._tool_create_pet("Buddy", 3, "Lab"),
            ag._tool_create_pet("buddy", 3, "Lab")
        )[-1])(fresh_agent()),
        check=lambda r: passed() if r.get("status") == "already_exists" else failed(f"got {r}"),
    ),
    scenario(
        name="Valid task accepted (HH:MM time format)",
        category="Input Handling",
        run=lambda: agent_with_buddy()._tool_add_task(
            "Buddy", "Walk", "07:30", 0.5, 4, "daily"
        ),
        check=lambda r: passed() if r.get("status") == "added" else failed(f"got {r}"),
    ),
    scenario(
        name="Invalid time format rejected ('8am')",
        category="Input Handling",
        run=lambda: agent_with_buddy()._tool_add_task(
            "Buddy", "Walk", "8am", 0.5, 4, "daily"
        ),
        check=lambda r: passed() if "error" in r else failed("should have returned error"),
    ),
    scenario(
        name="Out-of-range hour rejected ('25:00')",
        category="Input Handling",
        run=lambda: agent_with_buddy()._tool_add_task(
            "Buddy", "Walk", "25:00", 0.5, 4, "daily"
        ),
        check=lambda r: passed() if "error" in r else failed("should have returned error"),
    ),
    scenario(
        name="Add task to unknown pet returns error",
        category="Input Handling",
        run=lambda: fresh_agent()._tool_add_task(
            "Ghost", "Walk", "08:00", 0.5, 4, "daily"
        ),
        check=lambda r: passed() if "error" in r else failed("should have returned error"),
    ),
    scenario(
        name="Boundary time 23:59 accepted",
        category="Input Handling",
        run=lambda: agent_with_buddy()._tool_add_task(
            "Buddy", "Late Meds", "23:59", 0.1, 5, "daily"
        ),
        check=lambda r: passed() if r.get("status") == "added" else failed(f"got {r}"),
    ),

    # ── Category 2: Core Scheduling Logic ─────────────────────────────────

    scenario(
        name="sort_by_time returns tasks in chronological order",
        category="Core Scheduling Logic",
        run=lambda: (lambda ag: (
            ag._tool_add_task("Buddy", "Evening Walk", "18:00", 0.5, 3, "daily"),
            ag._tool_add_task("Buddy", "Breakfast",    "08:00", 0.25, 4, "daily"),
            ag._tool_add_task("Buddy", "Morning Walk", "07:30", 0.5, 4, "daily"),
            [t.scheduled_time for t in ag.scheduler.sort_by_time()]
        )[-1])(agent_with_buddy()),
        check=lambda r: passed() if r == sorted(r) else failed(f"order was {r}"),
    ),
    scenario(
        name="filter_by_pet returns only that pet's tasks",
        category="Core Scheduling Logic",
        run=lambda: (lambda ag: (
            ag._tool_create_pet("Whiskers", 2, "Siamese"),
            ag._tool_add_task("Buddy",    "Walk",       "08:00", 0.5, 4, "daily"),
            ag._tool_add_task("Whiskers", "Litter Box", "09:00", 0.5, 4, "daily"),
            [t.name for t in ag.scheduler.filter_by_pet("Buddy")]
        )[-1])(agent_with_buddy()),
        check=lambda r: (
            passed() if r == ["Walk"] else failed(f"got {r}")
        ),
    ),
    scenario(
        name="filter_by_status separates pending from completed",
        category="Core Scheduling Logic",
        run=lambda: (lambda ag: (
            ag._tool_add_task("Buddy", "Walk", "08:00", 0.5, 4, "daily"),
            ag._tool_add_task("Buddy", "Feed", "12:00", 0.25, 4, "daily"),
            ag._tool_mark_task_done("Buddy", "Walk"),
            len(ag.scheduler.filter_by_status(completed=True)),
        )[-1])(agent_with_buddy()),
        check=lambda r: passed() if r == 1 else failed(f"expected 1 completed, got {r}"),
    ),
    scenario(
        name="Daily recurrence creates task due tomorrow",
        category="Core Scheduling Logic",
        run=lambda: (lambda ag: (
            ag._tool_add_task("Buddy", "Meds", "08:00", 0.1, 5, "daily"),
            ag._tool_mark_task_done("Buddy", "Meds")
        )[-1])(agent_with_buddy()),
        check=lambda r: (
            passed() if r.get("next_occurrence_due") == str(date.today() + timedelta(days=1))
            else failed(f"got {r}")
        ),
    ),
    scenario(
        name="Weekly recurrence creates task due in 7 days",
        category="Core Scheduling Logic",
        run=lambda: (lambda ag: (
            ag._tool_add_task("Buddy", "Grooming", "10:00", 1.0, 3, "weekly"),
            ag._tool_mark_task_done("Buddy", "Grooming")
        )[-1])(agent_with_buddy()),
        check=lambda r: (
            passed() if r.get("next_occurrence_due") == str(date.today() + timedelta(weeks=1))
            else failed(f"got {r}")
        ),
    ),
    scenario(
        name="Monthly task does not auto-recur",
        category="Core Scheduling Logic",
        run=lambda: (lambda ag: (
            ag._tool_add_task("Buddy", "Flea Treatment", "09:00", 0.25, 5, "monthly"),
            ag._tool_mark_task_done("Buddy", "Flea Treatment")
        )[-1])(agent_with_buddy()),
        check=lambda r: (
            passed() if "next_occurrence_due" not in r
            else failed("monthly should not create next occurrence")
        ),
    ),
    scenario(
        name="Schedule respects owner hour cap",
        category="Core Scheduling Logic",
        run=lambda: (lambda ag: (
            [ag._tool_add_task("Buddy", f"Task {i}", "08:00", 1.0, 3, "daily") for i in range(12)],
            ag._tool_generate_schedule()["total_hours"]
        )[-1])(agent_with_buddy()),
        check=lambda r: passed() if r <= 8.0 else failed(f"total hours {r} exceeded cap of 8"),
    ),
    scenario(
        name="Highest-priority task is scheduled first",
        category="Core Scheduling Logic",
        run=lambda: (lambda ag: (
            ag._tool_add_task("Buddy", "Low",  "08:00", 0.5, 1, "daily"),
            ag._tool_add_task("Buddy", "High", "08:00", 0.5, 5, "daily"),
            ag._tool_generate_schedule()["schedule"][0]["task"]
        )[-1])(agent_with_buddy()),
        check=lambda r: passed() if r == "High" else failed(f"first task was '{r}'"),
    ),

    # ── Category 3: Conflict Detection ────────────────────────────────────

    scenario(
        name="Same start time flagged as conflict",
        category="Conflict Detection",
        run=lambda: (lambda ag: (
            ag._tool_add_task("Buddy", "A", "09:00", 0.5, 3, "daily"),
            ag._tool_add_task("Buddy", "B", "09:00", 0.5, 3, "daily"),
            ag._tool_check_conflicts()["conflict_count"]
        )[-1])(agent_with_buddy()),
        check=lambda r: passed() if r >= 1 else failed("expected at least 1 conflict"),
    ),
    scenario(
        name="Overlapping windows flagged as conflict",
        category="Conflict Detection",
        run=lambda: (lambda ag: (
            ag._tool_add_task("Buddy", "Vet",     "10:00", 1.5, 5, "weekly"),
            ag._tool_add_task("Buddy", "Grooming","11:00", 1.0, 3, "weekly"),
            ag._tool_check_conflicts()["conflict_count"]
        )[-1])(agent_with_buddy()),
        check=lambda r: passed() if r >= 1 else failed("overlapping windows should conflict"),
    ),
    scenario(
        name="Adjacent tasks are NOT flagged as conflict",
        category="Conflict Detection",
        run=lambda: (lambda ag: (
            ag._tool_add_task("Buddy", "Walk", "08:00", 1.0, 4, "daily"),
            ag._tool_add_task("Buddy", "Feed", "09:00", 0.5, 4, "daily"),
            ag._tool_check_conflicts()["conflict_count"]
        )[-1])(agent_with_buddy()),
        check=lambda r: passed() if r == 0 else failed(f"adjacent tasks gave {r} conflicts"),
    ),
    scenario(
        name="Completed tasks excluded from conflict check",
        category="Conflict Detection",
        # Use monthly frequency so mark_task_done does NOT create a new occurrence.
        # After completion, only B remains pending -- no conflict.
        run=lambda: (lambda ag: (
            ag._tool_add_task("Buddy", "A", "09:00", 1.0, 3, "monthly"),
            ag._tool_add_task("Buddy", "B", "09:00", 1.0, 3, "daily"),
            ag._tool_mark_task_done("Buddy", "A"),
            ag._tool_check_conflicts()["conflict_count"]
        )[-1])(agent_with_buddy()),
        check=lambda r: passed() if r == 0 else failed(f"completed task should not conflict, got {r}"),
    ),
    scenario(
        name="Cross-pet conflicts detected",
        category="Conflict Detection",
        run=lambda: (lambda ag: (
            ag._tool_create_pet("Whiskers", 2, "Siamese"),
            ag._tool_add_task("Buddy",    "Vet",     "10:00", 2.0, 5, "weekly"),
            ag._tool_add_task("Whiskers", "Groom",   "11:00", 1.0, 3, "weekly"),
            ag._tool_check_conflicts()["conflict_count"]
        )[-1])(agent_with_buddy()),
        check=lambda r: passed() if r >= 1 else failed("cross-pet overlap not detected"),
    ),
    scenario(
        name="Conflict warnings are non-empty strings",
        category="Conflict Detection",
        run=lambda: (lambda ag: (
            ag._tool_add_task("Buddy", "A", "09:00", 1.0, 3, "daily"),
            ag._tool_add_task("Buddy", "B", "09:00", 1.0, 3, "daily"),
            ag._tool_check_conflicts()["conflicts"]
        )[-1])(agent_with_buddy()),
        check=lambda r: (
            passed() if r and all(isinstance(w, str) and len(w) > 0 for w in r)
            else failed(f"warnings were: {r}")
        ),
    ),

    # ── Category 4: Error Handling and Guardrails ──────────────────────────

    scenario(
        name="Unknown tool name returns error dict (no exception)",
        category="Error Handling",
        run=lambda: fresh_agent()._dispatch("totally_fake_tool", {}),
        check=lambda r: passed() if "error" in r else failed("should return error dict"),
    ),
    scenario(
        name="mark_task_done with unknown pet returns error dict",
        category="Error Handling",
        run=lambda: fresh_agent()._tool_mark_task_done("Ghost", "Walk"),
        check=lambda r: passed() if "error" in r else failed("should return error dict"),
    ),
    scenario(
        name="mark_task_done with unknown task returns error dict",
        category="Error Handling",
        run=lambda: agent_with_buddy()._tool_mark_task_done("Buddy", "Nonexistent"),
        check=lambda r: passed() if "error" in r else failed("should return error dict"),
    ),
    scenario(
        name="Dispatch catches exception and returns error dict",
        category="Error Handling",
        run=lambda: agent_with_buddy()._dispatch("add_task", {
            "pet_name": "Buddy", "task_name": "Walk",
            "scheduled_time": "bad-time", "duration_hours": 0.5,
            "priority": 3, "frequency": "daily",
        }),
        check=lambda r: passed() if "error" in r else failed("should return error dict"),
    ),
    scenario(
        name="generate_schedule with no tasks returns info key (no crash)",
        category="Error Handling",
        run=lambda: fresh_agent()._tool_generate_schedule(),
        check=lambda r: passed() if "info" in r else failed(f"got {r}"),
    ),

    # ── Category 5: Logging ────────────────────────────────────────────────

    scenario(
        name="Agent writes to log file after tool call via _dispatch",
        category="Logging",
        run=lambda: (lambda ag: (
            ag._dispatch("create_pet", {"name": "LogTest", "age": 1, "breed": "Mixed"}),
            Path("logs/agent.log").exists() and Path("logs/agent.log").stat().st_size > 0
        )[-1])(fresh_agent()),
        check=lambda r: passed() if r is True else failed("logs/agent.log is empty or missing"),
    ),
    scenario(
        name="Log file contains tool name and args",
        category="Logging",
        run=lambda: (lambda ag: (
            ag._dispatch("create_pet", {"name": "LogTest2", "age": 1, "breed": "Mixed"}),
            "LogTest2" in Path("logs/agent.log").read_text()
        )[-1])(fresh_agent()),
        check=lambda r: passed() if r is True else failed("tool call record not found in log"),
    ),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_eval() -> str:
    results: List[Dict] = []

    for sc in SCENARIOS:
        try:
            result = sc["run"]()
            ok, detail = sc["check"](result)
        except Exception as exc:
            ok, detail = False, f"EXCEPTION: {exc}"

        results.append({
            "category": sc["category"],
            "name": sc["name"],
            "passed": ok,
            "detail": detail,
        })

    # Build report
    lines = []
    lines.append("=" * 66)
    lines.append("  PawPal+ Reliability Evaluation Report")
    lines.append("=" * 66)

    categories: Dict[str, List[Dict]] = {}
    for r in results:
        categories.setdefault(r["category"], []).append(r)

    total_pass = 0
    total_all = 0

    for cat, items in categories.items():
        cat_pass = sum(1 for i in items if i["passed"])
        cat_all  = len(items)
        total_pass += cat_pass
        total_all  += cat_all

        lines.append(f"\n{cat}  ({cat_pass}/{cat_all})")
        lines.append("-" * 50)
        for item in items:
            icon = "PASS" if item["passed"] else "FAIL"
            line = f"  [{icon}]  {item['name']}"
            if not item["passed"] and item["detail"]:
                line += f"\n           -> {item['detail']}"
            lines.append(line)

    pct = round(100 * total_pass / total_all) if total_all else 0

    lines.append("\n" + "=" * 66)
    lines.append(f"  OVERALL: {total_pass}/{total_all} scenarios passed ({pct}%)")
    lines.append("=" * 66)

    # Category summary table
    lines.append("\nCategory breakdown:")
    for cat, items in categories.items():
        cat_pass = sum(1 for i in items if i["passed"])
        cat_all  = len(items)
        bar = "#" * cat_pass + "." * (cat_all - cat_pass)
        lines.append(f"  {cat:<32} {cat_pass:>2}/{cat_all}  [{bar}]")

    report = "\n".join(lines)
    return report


if __name__ == "__main__":
    report = run_eval()
    print(report)

    # Write to file for archival
    log_path = Path("logs/eval_report.txt")
    log_path.parent.mkdir(exist_ok=True)
    log_path.write_text(report)
    print(f"\nReport saved to {log_path}")
