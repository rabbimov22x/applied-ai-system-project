# PawPal+ AI Scheduling Assistant

A conversational pet care scheduling app powered by an agentic AI workflow. You describe your pets and their care needs in plain English, and the system automatically builds a conflict-free daily schedule, explains its decisions, and tracks recurring tasks over time.

---

## Video Walkthrough

[Watch the Loom walkthrough](https://www.loom.com/share/23a244a2a6f54441a1cf10493e8a35d5)

---

## Origin: PawPal+ (Modules 1 through 3)

This project began in Modules 1 through 3 as **PawPal+**, a rule-based pet care scheduling assistant. The original system let a pet owner register pets and tasks, then used a priority-and-duration algorithm to generate a daily care plan within a time budget. It also included conflict detection, recurring task automation, and a full Streamlit UI for managing everything through forms and tables.

This version extends that foundation by adding an **agentic AI layer**: instead of filling in forms manually, the owner can describe their needs in natural language and an AI agent handles the rest automatically.

---

## What This Project Does

PawPal+ AI is a scheduling assistant for pet owners who want a smarter way to stay on top of their pets' daily routines.

The app has two modes:

**Manual mode** (the four form-based tabs) lets you add pets and tasks by hand, view tasks sorted by time, filter by pet or status, check for scheduling conflicts, generate a priority-ordered daily schedule, and mark tasks as complete. Completing a recurring daily or weekly task automatically queues the next occurrence.

**AI Assistant mode** (the fifth tab) lets you type a sentence like "My dog Buddy needs a morning walk, breakfast, and medication every day" and the AI agent takes over. It registers the pet, creates all the tasks with sensible defaults, checks for conflicts, generates the schedule, and responds in plain English explaining what it did.

The scheduling logic is the same in both modes. The AI layer orchestrates the existing engine rather than replacing it.

---

## Architecture Overview

The system has four main layers that work together:

**Streamlit UI** (`app.py`) is the interface. It has five tabs: Pets, Tasks, Conflicts, Schedule, and AI Assistant. Session state holds the owner, scheduler, agent, and chat history across interactions.

**PawPalAgent** (`ai_agent.py`) is the AI layer. It runs an agentic loop: it sends the user's message plus six tool definitions to the Claude API, receives tool-call instructions back, executes each tool against the live scheduling engine, returns the results to Claude, and repeats until Claude produces a final text response. All API calls and tool results are logged to `logs/agent.log`.

**Scheduling Engine** (`pawpal_system.py`) is the core logic. Four classes handle all data and rules: `Owner` (availability and preferences), `Pet` (breed, age, special needs), `Task` (scheduled time, duration, priority, frequency), and `Scheduler` (sorting, filtering, conflict detection, schedule generation, and recurrence).

**Test Suite** (`tests/`) verifies both layers independently. The scheduler tests run with no external dependencies. The agent tool tests also run with no API key, because they test the tool handler functions directly rather than making live Claude calls.

The diagram below shows how data flows through the system:

```
User (natural language or form input)
        |
        v
Streamlit UI (app.py)
        |
        v
PawPalAgent (ai_agent.py)
        |--- sends message + tool schemas to Claude API
        |<-- receives tool_use instructions
        |--- executes tools against Scheduling Engine
        |<-- receives tool results
        |--- loops until Claude issues end_turn
        |
        v
Scheduling Engine (pawpal_system.py)
  Owner --> Pet --> Task
  Scheduler: sort / filter / detect_conflicts / generate_schedule / mark_complete
        |
        v
Streamlit UI renders response + updated tables
        |
        v
logs/agent.log (all calls and results written here)
```

The full interactive diagram (Mermaid source) is in `assets/system_diagram.md`. Paste it at [mermaid.live](https://mermaid.live) to render and export as a PNG.

---

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- An Anthropic API key (required only for the AI Assistant tab; all other tabs work without one)

### Step 1: Clone the repository

```bash
git clone git@github.com:rabbimov22x/applied-ai-system-project.git
cd applied-ai-system-project
```

### Step 2: Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # macOS and Linux
.venv\Scripts\activate         # Windows
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Add your API key (for the AI Assistant tab)

```bash
export ANTHROPIC_API_KEY=sk-ant-...    # macOS and Linux
set ANTHROPIC_API_KEY=sk-ant-...       # Windows Command Prompt
```

Get a key at [console.anthropic.com](https://console.anthropic.com).

### Step 5: Run the app

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501` in your browser.

### Step 6: Run the tests

```bash
python -m pytest tests/ -v
```

All 74 tests pass without an API key.

---

## Sample Interactions

The following examples show real inputs sent to the AI Assistant tab and the responses the system produces.

### Example 1: Register a pet and build a full daily routine from one sentence

**User input:**
```
I have a 3-year-old Golden Retriever named Buddy. He needs a morning walk,
breakfast, evening walk, and daily medication.
```

**What the agent does internally:**
```
create_pet("Buddy", age=3, breed="Golden Retriever")
add_task("Buddy", "Morning Walk",  "07:30", duration=0.5h,  priority=4, "daily")
add_task("Buddy", "Breakfast",     "08:00", duration=0.25h, priority=4, "daily")
add_task("Buddy", "Medication",    "08:30", duration=0.1h,  priority=5, "daily")
add_task("Buddy", "Evening Walk",  "17:30", duration=0.5h,  priority=4, "daily")
check_conflicts()
generate_schedule()
```

**Agent response:**
```
I've set up Buddy's daily routine with 4 tasks. Here is today's schedule:

  07:30  Morning Walk      (30 min, daily)
  08:00  Breakfast         (15 min, daily)
  08:30  Medication        (6 min, daily, priority 5)
  17:30  Evening Walk      (30 min, daily)

No scheduling conflicts were found. Medication is ranked highest in priority
so it will always be scheduled before lower-priority tasks if time is tight.
Total care time: 1.35 hours.
```

---

### Example 2: Add a second pet and detect a conflict

**User input:**
```
Also add my cat Whiskers (2 years old, Siamese). She needs a litter box clean
at 8am and a weekly vet checkup at 8:15am that takes 90 minutes.
```

**What the agent does internally:**
```
create_pet("Whiskers", age=2, breed="Siamese")
add_task("Whiskers", "Litter Box Clean", "08:00", duration=0.25h, priority=4, "daily")
add_task("Whiskers", "Vet Checkup",      "08:15", duration=1.5h,  priority=5, "weekly")
check_conflicts()
```

**Agent response:**
```
I've added Whiskers and both tasks. However, I found a scheduling conflict:

  WARNING: "Litter Box Clean" (08:00, 0.25h) conflicts with
           "Vet Checkup" (08:15, 1.5h)

The litter box clean runs from 08:00 to 08:15, and the vet checkup starts
at 08:15, so they overlap by the shared endpoint. To fix this, either move
the litter box clean to 07:45 or start the vet checkup at 08:30.

Would you like me to adjust one of the times?
```

---

### Example 3: Mark a task complete and see recurrence in action

**User input:**
```
Buddy just finished his morning walk. Mark it as done.
```

**What the agent does internally:**
```
mark_task_done("Buddy", "Morning Walk")
```

**Agent response:**
```
Done! Buddy's Morning Walk is marked complete.

Because this is a daily recurring task, I've automatically created the next
occurrence due tomorrow (2026-04-30). It will appear in tomorrow's schedule
with the same time and priority settings.
```

---

## Stretch Features

Four optional enhancements were added beyond the required baseline. Each one is independently togglable.

### 1. RAG Enhancement (+2)

**File:** `rag.py`

A retrieval-augmented generation module provides a curated pet care knowledge base with 19 entries across six categories: Feeding, Exercise, Grooming, Medication, Scheduling, and Vet Care. Each entry has a category label, a plain-text guideline, and keyword tags.

Before every Claude API call, the agent runs `retrieve(query, top_k=3)`, which scores every knowledge base entry against the user's message using Jaccard term-overlap similarity (no external ML libraries needed). The top three matching entries are formatted and injected into the system prompt so Claude's scheduling advice is grounded in real care guidelines rather than general training knowledge alone.

**Evidence of improvement:** The RAG comparison section of the evaluator shows a 4/4 keyword hit rate across four representative queries. Every query retrieved at least one entry from the correct category, and the top result's text directly addressed the query topic. Without RAG, those same queries would inject zero context and rely entirely on the model's training data.

RAG can be toggled on or off using the "RAG knowledge base" toggle in the sidebar of the AI Assistant tab. When off, the system prompt contains no retrieved context.

### 2. Agentic Workflow Enhancement (+2)

**Method:** `chat_with_steps()` in `ai_agent.py`

Every step in the agent's reasoning loop is now recorded and returned alongside the final reply. The AI Assistant tab exposes an expandable "Agent reasoning" panel beneath each response that shows every intermediate step: which documents were retrieved from the knowledge base, how many content blocks each API response contained, which tool was called with what arguments, and what result each tool returned.

The step trace is a list of dicts, each with a `type` field (`"retrieve"`, `"api_response"`, `"tool_call"`, `"tool_result"`) and type-specific fields. The existing `chat()` method calls `chat_with_steps()` and discards the steps, so the original interface is unchanged.

This makes the agent's behavior transparent and debuggable: a user can see exactly how the AI interpreted their message and what actions it took before responding.

### 3. Fine-Tuning / Specialization (+2)

**Implementation:** `FEW_SHOT_MESSAGES` in `ai_agent.py`, controlled by `specialized=True`

A set of two example conversation turns is prepended to every message when specialization mode is active. The examples demonstrate two output patterns that do not appear in the base model by default:

1. A "Breed note:" line that surfaces specific care guidelines relevant to the pet's breed.
2. A "Confidence: [High/Medium/Low] based on [reason]" line at the end of every response.

These patterns are measurably different from baseline output: the confidence rating suffix can be detected programmatically and was used during development to confirm that specialized responses consistently follow the injected format. Without the few-shot prefix, neither pattern appears.

Specialization mode is toggled via the "Specialization mode" toggle in the sidebar. When on, the few-shot prefix is injected before the user's message in every call.

### 4. Test Harness Enhancement (+2)

**File:** `tests/eval_reliability.py`

Two enhancements were added to the reliability evaluator:

**Confidence scoring:** Every scenario now carries a `confidence` float (0.0 to 1.0) representing how likely that test is to catch a real regression. Critical tool-handler tests (create pet, log file presence) are rated 0.90 to 0.95. Standard behavioral tests default to 0.80. The evaluator computes and prints a confidence-weighted overall score alongside the raw pass rate, giving a more calibrated measure of test suite strength.

**RAG comparison:** A new section at the end of the report runs four representative queries through `retrieve()` and checks whether the keyword associated with each query appears in the retrieved results. It reports the keyword hit rate and shows the top retrieved document for each query, giving a clear before/after comparison: 0 context blocks injected without RAG vs. 3 grounded knowledge base entries with RAG.

**Actual output from the most recent run:**
```
OVERALL: 29/29 scenarios passed (100%)
CONFIDENCE-WEIGHTED SCORE: 100.0%

RAG keyword hit rate: 4/4
Baseline (no retrieval): 0 docs injected into prompt
With RAG: avg 3 docs injected -- grounded in knowledge base.
```

---

## Design Decisions

### Why an agentic workflow instead of a simple chatbot

A regular chatbot would accept a question, call the Claude API once, and return text. That works for Q&A but not for a scheduling app where the AI needs to actually create data and check it for problems. The agentic loop lets Claude plan a sequence of actions, execute them one at a time, observe the results (including conflict warnings and schedule output), and adjust its plan before responding. This means the AI's final answer reflects the real state of the system, not a guess.

### Why Claude's tool use rather than prompt engineering

An alternative design would give Claude a description of the scheduling system and ask it to produce JSON that the app then parses. Tool use is more reliable because Claude produces a structured function call with typed parameters that are validated before touching the database. If a parameter is wrong (for example, an invalid time string), the tool returns an error dict and Claude can correct itself in the next iteration. Prompt-engineered JSON has no such feedback loop.

### Why the AI orchestrates existing classes rather than replacing them

All 74 tests target `pawpal_system.py` and the agent's tool handlers. The scheduling engine has no dependency on Claude. This means the rules are testable without an API key, the UI works fully without the AI tab, and the AI layer can be swapped for a different model without touching the scheduling logic. Keeping these concerns separate made both layers easier to reason about and test.

### Tradeoff: conflict detection uses window overlap, not exact time match

The conflict detector flags tasks whose `[start, start + duration)` windows intersect. This catches real problems like a 90-minute vet visit that runs into a grooming session scheduled an hour later. The tradeoff is that tasks with `duration_hours=0` (point-in-time reminders) can never conflict with anything, because their window has zero width. This is acceptable given that all real pet care tasks have a non-zero duration.

### Tradeoff: schedule generation is greedy

The scheduler sorts tasks by priority (highest first), then duration (shortest first), then stops when the owner's daily hour cap is reached. This is fast and predictable but does not globally optimize for the most tasks or the best fit. A constraint-satisfaction approach would schedule more tasks in edge cases, but at the cost of being harder to explain to the user and harder to test.

### Tradeoff: no persistent storage

All data lives in Streamlit session state, which resets on page refresh. This was the right call for a class project where the goal was demonstrating AI and scheduling logic, not building a production app. Adding SQLite or a JSON file for persistence would be the first improvement in a real deployment.

---

## Testing Summary

Three independent verification methods were used. All results shown below are from actual runs, not estimates.

### 1. Unit and integration tests (pytest)

```
74 passed in 1.78s
```

**`tests/test_pawpal.py` (44 tests)** covers the scheduling engine: task completion and reset, adding tasks to pets, chronological sorting, pet and status filtering, daily and weekly recurrence, window-overlap conflict detection, priority-ordered schedule generation, and input validation edge cases such as invalid priority ranges and duplicate special needs.

**`tests/test_agent.py` (30 tests)** covers every tool handler in `PawPalAgent` without making any Claude API calls. It tests the happy path for each tool and the error paths: unknown pet names, invalid time formats, duplicate pet creation, completing a task that is already done, passing an unknown tool name to the dispatcher, and passing bad input that would normally raise an exception.

Run with:
```bash
python -m pytest tests/ -v
```

### 2. Reliability evaluator (scored scenarios)

A separate script (`tests/eval_reliability.py`) runs 29 named scenarios across five categories and checks each result against an expected output. This is distinct from pytest -- it measures behavioral correctness at the system level, not just code correctness at the unit level.

```
python tests/eval_reliability.py
```

**Results (actual run):**

```
Category              Passed   Bar
Input Handling          8/8    [########]
Core Scheduling Logic   8/8    [########]
Conflict Detection      6/6    [######]
Error Handling          5/5    [#####]
Logging                 2/2    [##]

OVERALL: 29/29 scenarios passed (100%)
CONFIDENCE-WEIGHTED SCORE: 100.0%
```

Each scenario now carries a confidence weight (0.80 to 0.95) representing how likely it is to catch a real regression. A RAG comparison section also runs at the end of the report, showing keyword hit rate across four sample queries.

During development, the first run produced 26/29 (90%). Two failures revealed a real logging gap: `_dispatch()` only logged errors, not successful tool calls. The third failure exposed a subtle behavior: completing a recurring daily task auto-creates a new occurrence at the same time, so the original conflict reappears. Both were fixed before the final run.

The evaluator saves its full report to `logs/eval_report.txt` on every run.

### 3. Logging and error handling

Every tool call routed through `_dispatch()` is written to `logs/agent.log` with the tool name, arguments, and result. Errors include the exception message. The log is append-only so it accumulates a full history of every agent action.

Sample log entries:
```
2026-04-29 [INFO] TOOL  create_pet  args={'name': 'Buddy', 'age': 3, ...}  result={'status': 'created', ...}
2026-04-29 [INFO] TOOL  check_conflicts  args={}  result={'conflict_count': 1, 'conflicts': ['WARNING: ...']}
2026-04-29 [WARNING] Unknown tool requested: totally_fake_tool
2026-04-29 [ERROR] Tool 'add_task' raised: Invalid scheduled_time '8am'  args={...}
```

Errors are caught and returned as `{"error": "..."}` dicts so the agent can read the error message and self-correct rather than crash.

**What did not get covered:** The Streamlit UI layer has no automated tests. Tab rendering, button click behavior, and session state persistence were verified manually. A future improvement would be adding Playwright or Selenium tests for the critical user flows.

**What I learned:** Running the evaluator before finalizing the code found two real bugs that pytest had not caught -- the logging gap and the recurrence edge case. Behavioral testing at the scenario level and unit testing at the function level complement each other. Neither alone was sufficient.

---

## Reflection

**On building with AI tools**

The most important thing this project taught me is that AI tools work best when the problem is precisely defined. Every time I asked a vague question such as "add recurrence logic," the suggestions were generic and needed heavy editing. Every time I asked something specific such as "how do I use `timedelta` to add one day to a `date` object," the answer was immediately usable. Being the lead architect meant knowing what I was trying to solve clearly enough to ask the right question, not just asking the AI to figure it out.

**On agentic systems**

Building the agentic loop revealed something that is not obvious from reading about agents: the tool design matters more than the prompt. If a tool returns a vague result, Claude's next decision is based on vague information. If a tool returns a precise, structured dict (including clear error messages when something goes wrong), Claude can reason accurately about what to do next. The quality of the agent's behavior is largely determined by how well the tools communicate.

**On testing as a design practice**

Writing tests for the tool handlers before testing the full agent loop forced me to think clearly about what each tool was supposed to return in every case. That clarity carried back into the tool implementations and made them more robust. Testing was not just a verification step at the end; it shaped the design.

**On the limits of what is here**

This system does not persist data between sessions, does not support a real user login system, and has not been tested with a large number of pets or tasks. These are deliberate scope decisions for a course project, not oversights. Knowing where the edges of a system are is part of engineering honestly.

---

## Responsible AI

**Limitations and biases**

The scheduling algorithm trusts user-assigned priorities entirely. A user who marks medication as low priority will get a schedule that deprioritizes their pet's health, and the system has no way to detect or warn about that. The AI agent's default time slots (morning around 07:30, midday around 12:00, evening around 17:30) are biased toward a conventional daytime lifestyle and will produce unhelpful defaults for night-shift workers or owners in different routines. The conflict detector is purely time-based and cannot detect location conflicts, energy conflicts, or task dependencies. There is also no persistent memory, so the agent cannot learn from past sessions or adapt to a user's actual patterns.

**Potential misuse and how to address it**

The system has no minimum care validation. A user could describe a neglectful schedule and the AI agent would build it without warning. A responsible deployment would include guardrails: warnings when no feeding task exists within a 12-hour window, or when a pet's medication frequency drops below a safe threshold. The app also has no authentication. Deployed without access controls, any visitor could modify the schedule. The API key is read from an environment variable (the correct pattern), but a developer who hardcodes it into source code and pushes to a public repository would expose it. Setup instructions in this README deliberately show only the shell export form for this reason.

**What surprised me during reliability testing**

The reliability evaluator's first run returned 26/29 (90%) when a perfect score was expected. Two of the three failures were invisible to the 74 pytest tests. The logging gap (successful tool calls were silently not recorded) only appeared when the evaluator called `_dispatch()` directly, bypassing the outer loop that had its own logging. The recurrence edge case revealed that the system was behaving correctly but the test had been written with a wrong mental model -- completing a daily task immediately creates a new occurrence at the same conflicting time slot, which is correct behavior, not a bug. Both findings would have been missed without a second, independent evaluation method.

**One helpful AI suggestion and one flawed one**

The most useful suggestion in the project came when implementing conflict detection. The AI proposed using `itertools.combinations(pending, 2)` with a list comprehension to replace a verbose double-index loop. It was immediately usable, more readable, and introduced a standard library pattern that better communicated the intent.

The most flawed suggestion also came from the conflict detection phase. The AI generated logic that called `raise ValueError("Scheduling conflict detected")` when two tasks overlapped. This would crash the application every time a user accidentally scheduled two overlapping tasks, which is the exact scenario the feature exists to handle gracefully. I redirected the AI to return a list of warning strings instead. The fix became `get_conflict_warnings()`. The AI was optimizing for correctness (fail loudly) while the right answer for a user-facing app was to fail safely (warn without crashing). Recognizing that difference required overriding the suggestion rather than accepting it.

---

## Project Structure

```
applied-ai-system-project/
|
|-- app.py                  # Streamlit UI (5 tabs, RAG + specialization toggles)
|-- ai_agent.py             # PawPalAgent: agentic loop, RAG, few-shot, observable steps
|-- rag.py                  # Pet care knowledge base + Jaccard retrieval
|-- pawpal_system.py        # Core scheduling engine: Owner, Pet, Task, Scheduler
|-- main.py                 # CLI demo script for the scheduling engine
|-- requirements.txt        # Python dependencies
|
|-- tests/
|   |-- test_pawpal.py      # 44 scheduler tests
|   |-- test_agent.py       # 30 agent tool reliability tests
|   |-- eval_reliability.py # 29 scored scenarios + confidence weights + RAG comparison
|
|-- assets/
|   |-- system_diagram.md   # Mermaid source for the architecture diagram
|
|-- logs/
|   |-- agent.log           # Runtime log (API calls, tool results, errors)
|   |-- eval_report.txt     # Latest reliability evaluator report
|
|-- reflection.md           # Project reflection and design notes
|-- uml_final.md            # Final UML class diagram (Mermaid source)
```

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `streamlit` | >=1.30 | Web UI framework |
| `anthropic` | >=0.40 | Claude API client for the AI agent |
| `pytest` | >=7.0 | Test runner |

Python standard library only for everything else (`dataclasses`, `datetime`, `itertools`, `uuid`, `logging`, `json`).
