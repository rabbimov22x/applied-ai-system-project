# PawPal+ (Module 2 Project)

A smart pet care scheduling assistant built with Python and Streamlit.

## Features

- **Multi-pet support** — manage any number of pets, each with their own task list
- **Priority-based scheduling** — tasks are ordered by priority (1–5) then duration, so the most critical care always happens first
- **Sort by time** — view all tasks in chronological order using `Scheduler.sort_by_time()`
- **Filter by pet or status** — instantly scope the task list to one pet or to pending/completed tasks
- **Conflict detection** — window-overlap algorithm flags any two tasks whose time ranges clash; warnings appear in the sidebar, the Conflicts tab, and before schedule generation
- **Recurring task automation** — marking a `daily` or `weekly` task complete automatically creates the next occurrence with the correct due date (`timedelta`)
- **Schedule explanation** — the app explains why tasks were ordered the way they were
- **Hour-cap enforcement** — tasks that would exceed the owner's daily availability are excluded from the generated schedule
- **🤖 AI Assistant (Agentic Workflow)** — describe your pets and care needs in plain English; the AI agent plans, calls tools, checks its own work, and responds with a complete schedule

## AI Feature: Agentic Workflow

The AI Assistant tab is powered by an **agentic loop** using the Claude API with tool use:

1. You describe your pet care needs in natural language
2. `PawPalAgent` sends your message to Claude (`claude-sonnet-4-6`) along with 6 tool schemas
3. Claude decides which tools to call — `create_pet`, `add_task`, `check_conflicts`, `generate_schedule`, etc.
4. Each tool call maps directly to the existing `Scheduler`/`Owner`/`Pet` logic — the AI orchestrates, it doesn't replace
5. Results feed back to Claude, which continues until it has a complete answer (`end_turn`)
6. Every API call, tool invocation, and error is written to `logs/agent.log`

```
User: "My dog Buddy needs a morning walk, breakfast, and medication daily."
    → create_pet(Buddy, 3, Golden Retriever)
    → add_task(Buddy, Morning Walk, 07:30, 0.5h, priority=4, daily)
    → add_task(Buddy, Breakfast, 08:00, 0.25h, priority=4, daily)
    → add_task(Buddy, Medication, 08:30, 0.1h, priority=5, daily)
    → check_conflicts()
    → generate_schedule()
    → "Here's Buddy's day: Medication at 8:30, Walk at 7:30..."
```

### Setup for AI features

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # get yours at console.anthropic.com
source .venv/bin/activate
streamlit run app.py
```

## 📸 Demo

<a href="/course_images/ai110/pawpal_screenshot.png" target="_blank"><img src='/course_images/ai110/pawpal_screenshot.png' title='PawPal App' width='' alt='PawPal App' class='center-block' /></a>

## Run the app

```bash
source .venv/bin/activate   # Windows: .venv\Scripts\activate
streamlit run app.py
```

---

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Smarter Scheduling

Phase 3 adds four algorithmic features to `Scheduler` in `pawpal_system.py`:

| Feature | Method | How it works |
|---|---|---|
| **Sort by time** | `sort_by_time()` | Uses `sorted()` with a `lambda` key on each task's `"HH:MM"` string — lexicographic order works correctly for zero-padded times |
| **Filter tasks** | `filter_by_pet(name)` / `filter_by_status(completed)` | List comprehensions that match on pet name (case-insensitive) or completion flag |
| **Recurring tasks** | `mark_task_complete(task_id)` | When a `daily` or `weekly` task is completed, `timedelta` calculates the next due date and a new `Task` copy is added automatically |
| **Conflict detection** | `detect_conflicts()` / `get_conflict_warnings()` | `itertools.combinations` examines every unique task pair; two tasks conflict when their `[start, start + duration)` windows overlap. `get_conflict_warnings()` returns plain warning strings so the app never crashes on a conflict |

Run the demo:

```bash
python3 main.py
```

---

## Testing PawPal+

Run the full test suite with:

```bash
# activate the virtual environment first
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pytest tests/test_pawpal.py -v
```

The suite contains **74 tests** across 10 test classes (44 scheduler + 30 agent tool tests):

| Class | What it covers |
|---|---|
| `TestTaskCompletion` | `mark_completed()` sets flag + timestamp; `reset_completion()` clears both |
| `TestTaskAddition` | Adding a task to a `Pet` increments task count and sets `pet_id` |
| `TestSortByTime` | Chronological ordering for scrambled, sorted, single, and empty task sets |
| `TestFilterByPet` | Scoped retrieval, case-insensitive name match, unknown/empty pet edge cases |
| `TestFilterByStatus` | Splits pending vs. completed correctly across mixed and uniform sets |
| `TestRecurrence` | Daily → tomorrow, weekly → +7 days, monthly → no recurrence, attribute inheritance |
| `TestConflictDetection` | Exact-time, overlapping windows, adjacent (no conflict), cross-pet, completed tasks excluded |
| `TestScheduleGeneration` | Priority ordering, hour-cap enforcement, validate_schedule |
| `TestEdgeCases` | Invalid priority/hours raise `ValueError`, duplicate special needs, missing IDs |

| `TestToolCreatePet` | Duplicate detection, case-insensitivity, special needs storage |
| `TestToolAddTask` | Attribute inheritance, unknown pet, invalid time format, boundary values |
| `TestToolListPetsAndTasks` | Empty owner, pet keys, task listing |
| `TestToolCheckConflicts` | Same-time, overlapping windows, adjacent tasks, warning string types |
| `TestToolGenerateSchedule` | Empty state, priority ordering, hour-cap enforcement |
| `TestToolMarkTaskDone` | Completion flag, recurrence, unknown pet/task, already-done guard |
| `TestDispatch` | Unknown tool name, exception → error dict (never crash) |

**Confidence level: ★★★★☆ (4/5)**
Core scheduling logic, recurrence, and conflict detection are thoroughly tested.
The remaining gap is integration-level testing of the Streamlit UI layer, which is not yet covered.

---

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
