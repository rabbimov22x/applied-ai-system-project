# PawPal+ Project Reflection

## 1. System Design

### Core User Actions

A user should be able to perform three key actions:

1. **Add and manage pet information** — Enter details about their pet (name, age, preferences) and their own availability/constraints so the system understands the context for scheduling.

2. **Create and organize pet care tasks** — Add tasks the pet needs (walks, feeding, medications, grooming, enrichment) with duration and priority levels so the system knows what needs to be scheduled.

3. **Generate and view a daily schedule** — Request a daily plan that organizes all tasks within available time, respects priorities, and displays the schedule clearly with reasoning so the user can follow it and understand why tasks are ordered that way.

**a. Initial design**

I designed a system with four core classes: Pet, Task, Owner, and Scheduler.

- **Pet**: A dataclass that holds pet information (name, age, breed, special needs, preferences) and provides methods to manage special needs. This class is responsible for storing all pet-specific data that affects scheduling decisions.

- **Task**: A dataclass representing individual care activities (walks, feeding, medication, etc.) with attributes for duration, priority, type, and notes. It includes methods to manage priority levels and check urgency status.

- **Owner**: A class that encapsulates owner constraints and preferences (available hours, timezone, scheduling preferences). It manages the owner's availability and personal scheduling constraints.

- **Scheduler**: The main orchestration class that holds references to Owner, Pet, and a list of Tasks. It's responsible for generating daily schedules, validating them against time constraints, optimizing task order, and providing explanations for scheduling decisions.

**b. Design changes**

Yes, I made several changes during implementation based on the requirements and to improve the design:

1. **Added unique IDs**: Both `Task` and `Pet` now have unique IDs generated with UUID to enable proper task management and pet identification.

2. **Enhanced Task class**: Changed from a simple dataclass to include completion status (`completed`, `completed_at`), better description field, and a `pet_id` reference to link tasks to specific pets.

3. **Pet manages tasks directly**: Instead of having tasks managed separately, each `Pet` now stores its own list of tasks, making the relationship more explicit.

4. **Owner manages multiple pets**: The `Owner` class now maintains a list of pets and provides methods like `get_all_tasks()` to aggregate tasks across all pets, fulfilling the requirement that owners manage multiple pets.

5. **Scheduler-Owner relationship**: Changed the `Scheduler` to work with `Owner` only (removing the direct `Pet` reference) and use `Owner.get_all_tasks()` to retrieve tasks, making the architecture more flexible for multi-pet households.

6. **Added ScheduledTask**: Created a new dataclass to represent tasks scheduled at specific times, providing better structure for the daily schedule output.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers three constraints, in order of importance:

1. **Priority (1–5)** — tasks with higher urgency (e.g., medications, feeding) are always placed before lower-priority tasks like enrichment or grooming. This is the primary sort key.
2. **Duration** — among tasks of equal priority, shorter tasks come first, maximizing the number of tasks that fit within the daily time budget.
3. **Available hours** — the owner's daily hour cap acts as a hard cutoff; once the running total exceeds it, remaining tasks are dropped from the generated schedule.

I ranked priority first because a pet's health-critical tasks (medication, feeding) should never be bumped by a long but low-priority grooming session. Duration is secondary because fitting more tasks into a limited day is more useful than doing a single long task. The hour cap is non-negotiable — it reflects the owner's real availability.

**b. Tradeoffs**

The conflict detector checks whether two tasks' time *windows* overlap (using
start < other_end && other_start < end), rather than only flagging exact
same-start-time matches.

**Why this tradeoff is reasonable:** A pet owner cares whether two tasks are
physically impossible to do at the same time, not just whether they share an
identical start minute. A 90-minute vet visit starting at 10:00 genuinely
prevents a grooming session starting at 11:00, even though the start times
differ by a full hour. Checking full windows catches that real scheduling
impossibility.

**What it gives up:** The window-overlap check requires knowing `duration_hours`
for every task. If a task has no meaningful duration (e.g., a reminder with
`duration_hours=0`), the window collapses to a point and zero-duration tasks
will never be flagged as conflicting with anything. That edge case is
acceptable for this app because all care tasks (walks, feeding, grooming)
have a realistic, non-zero duration by design.

---

## 3. AI Collaboration

**a. How you used AI**

AI assistance was used across every phase, but for different purposes at each stage:

- **Phase 1 (design):** I asked the AI to brainstorm which classes a pet scheduling app would need and what their responsibilities should be. The prompts "What are the core entities in a pet care scheduling system?" and "What methods would a Scheduler class need?" gave me a starting class list that I then refined.
- **Phase 2 (implementation):** I used inline suggestions to fill in method bodies once I had stubs in place, and asked follow-up questions like "How do I link a Task back to its Pet using an ID rather than a direct reference?" to work out the `pet_id` design.
- **Phase 3 (algorithms):** The most useful prompts were specific and bounded: "How do I use `itertools.combinations` to check all pairs of tasks for overlap?" and "How does `timedelta` work for calculating next-day recurrence?" These worked better than vague requests like "add recurring task logic."
- **Phase 4 (testing):** I asked for a test plan — "What are the most important edge cases for sorting and recurrence?" — and used that list to drive which test classes to write, rather than letting the AI generate all the test code directly.

**b. Judgment and verification**

When implementing conflict detection, the AI initially suggested a double nested `for i in range(len(...))` loop. I rejected this in favor of `itertools.combinations` because:

1. The manual index loop is a common Python anti-pattern — it obscures intent.
2. `combinations(pending, 2)` communicates "examine every unique pair" at a glance, without readers needing to think about why `j` starts at `i + 1`.
3. I verified the replacement produced identical results by running both versions against the same fixture data: two overlapping tasks → one conflict, adjacent tasks → zero conflicts.

The AI's version was correct but not the most readable. Choosing `combinations` was a deliberate style decision, not a blind acceptance of the suggestion.

---

## 4. Testing and Verification

**a. What you tested**

The test suite covers five behavioral areas:

1. **Sorting** — tasks added in scrambled order are returned chronologically; already-sorted tasks remain unchanged; empty and single-task sets don't crash.
2. **Filtering** — `filter_by_pet` returns only that pet's tasks, is case-insensitive, and returns `[]` for unknown pets. `filter_by_status` correctly splits pending from completed.
3. **Recurrence** — `mark_task_complete` produces a next task with the correct `due_date` (+1 day for daily, +7 for weekly), the original is marked done, the new task starts incomplete, all attributes are copied, and "monthly" returns `None`.
4. **Conflict detection** — exact-time overlap, window overlap, adjacent-but-not-overlapping tasks, completed tasks excluded, cross-pet conflicts, and the warning string format.
5. **Schedule generation** — highest priority scheduled first, hour cap enforced, empty-task and all-complete edge cases.

These tests matter because they guard the behaviors a pet owner would notice immediately if broken: wrong task order, a recurring medication not showing up tomorrow, or a false "no conflicts" message.

**b. Confidence**

**4/5 stars.** The core logic — sorting, filtering, recurrence, and conflict detection — is thoroughly exercised with both happy-path and edge-case tests (44 tests, all passing). The main gap is the Streamlit UI layer: the tab rendering, button interactions, and session-state persistence are not tested programmatically. If I had more time, I would add:

- A test for `mark_task_complete` when the pet list is empty (should return `None` gracefully).
- Tests for `generate_schedule` with tasks of equal priority and different durations to confirm the tie-breaking rule.
- A test confirming that tasks scheduled past midnight (hour > 23) don't crash the time arithmetic.

---

## 5. Reflection

**a. What went well**

The part I'm most satisfied with is the conflict detection design. Rather than a simple "same start time" check, the window-overlap algorithm catches real scheduling impossibilities (a vet visit that runs long enough to crowd out the next task). Using `itertools.combinations` makes the intent readable in one line. The fact that 9 tests cover it — including edge cases like adjacent tasks that should *not* conflict and completed tasks that should be excluded — gives me high confidence it behaves correctly in every scenario a pet owner would encounter.

**b. What you would improve**

Two things stand out:

1. **Persistent storage** — every Streamlit page refresh wipes session state. Adding a simple JSON file or SQLite database to save pets and tasks between sessions would make the app genuinely usable day-to-day rather than a demo.
2. **Smarter schedule generation** — the current algorithm is greedy (highest priority, then stop when hours run out). It doesn't consider the task's `scheduled_time` preference when placing items on the generated timeline. A constraint-satisfaction approach that respects preferred times while still fitting within the hour cap would produce a much more useful daily plan.

**c. Key takeaway**

The most important thing I learned is that **AI tools are excellent at filling in the "how" once you have decided the "what."** Every time I asked a vague question ("add recurrence logic"), the suggestions were generic and required heavy editing. Every time I came with a specific, bounded question ("how do I use `timedelta` to add one day to today's date and store it as a `date` object?"), the answer was immediately usable. The lead architect role isn't about knowing all the syntax — it's about knowing what problem you're solving precisely enough to ask the right question.

### AI Collaboration — VS Code Copilot specifics

**Most effective features:**
- **Inline Chat on a method stub** was the highest-signal interaction. Having the class context visible while asking "implement this method" produced suggestions that matched the existing data model rather than inventing new fields.
- **`#codebase` in chat** was useful for cross-file questions (e.g., "what attributes does Task have that I could sort on?") without having to manually read every file first.
- **Separate chat sessions per phase** prevented the AI from mixing Phase 1 design discussions with Phase 3 implementation details. When a single chat session accumulated too much context, suggestions started referencing approaches from earlier phases that had since been replaced.

**One suggestion I rejected:**
When I asked for conflict detection logic, Copilot generated a version that raised a `ValueError` and halted execution when a conflict was found. This would crash the app any time a user accidentally scheduled two overlapping tasks. I kept the algorithm but changed the return type from "raise on conflict" to "return a list of warning strings" — `get_conflict_warnings()` — so the UI can display the problem without terminating. The AI was optimizing for correctness (crash loudly); I was optimizing for usability (warn gracefully).

**What using separate chat sessions taught me:**
Each session acts like a focused work context. Phase 1 was for architecture, Phase 2 for implementation, Phase 3 for algorithms, Phase 4 for testing. Keeping them separate forced me to make deliberate decisions at each boundary — I had to summarize what I'd built before asking the next session for help, which doubled as a design review. That human checkpoint between phases was more valuable than the AI suggestions themselves.
