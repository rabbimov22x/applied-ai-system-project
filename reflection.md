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

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
