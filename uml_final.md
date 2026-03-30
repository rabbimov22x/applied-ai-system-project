# PawPal+ — Final Class Diagram

Render this Mermaid diagram at https://mermaid.live to export as `uml_final.png`.

```mermaid
classDiagram
    direction TB

    class Task {
        +str id
        +str name
        +str description
        +float duration_hours
        +int priority
        +str frequency
        +str scheduled_time
        +date due_date
        +bool completed
        +datetime completed_at
        +str pet_id
        +set_priority(level)
        +get_duration() float
        +get_priority() int
        +is_urgent() bool
        +mark_completed()
        +reset_completion()
    }

    class Pet {
        +str id
        +str name
        +int age
        +str breed
        +List~str~ special_needs
        +Dict preferences
        +List~Task~ tasks
        +add_special_need(need)
        +remove_special_need(need)
        +get_special_needs() List
        +add_task(task)
        +remove_task(task_id) bool
        +get_tasks() List
        +get_pending_tasks() List
    }

    class Owner {
        +str name
        +float available_hours_per_day
        +Dict preferences
        +str timezone
        +List~Pet~ pets
        +set_available_hours(hours)
        +set_preferences(prefs)
        +get_available_hours() float
        +add_pet(pet)
        +remove_pet(pet_id) bool
        +get_pets() List
        +get_all_tasks() List
        +get_pending_tasks() List
        +get_pet_by_id(pet_id) Pet
    }

    class ScheduledTask {
        +Task task
        +time scheduled_time
        +float estimated_duration
        +__str__() str
    }

    class Scheduler {
        +Owner owner
        +List~ScheduledTask~ daily_schedule
        +add_task(task, pet_id)
        +remove_task(task_id) bool
        +generate_schedule() List
        +validate_schedule() bool
        +optimize_task_order() List
        +get_schedule_explanation() str
        +sort_by_time() List
        +filter_by_pet(pet_name) List
        +filter_by_status(completed) List
        +mark_task_complete(task_id) Task
        +detect_conflicts() List
        +get_conflict_warnings() List
    }

    Owner "1" o-- "0..*" Pet : manages
    Pet "1" o-- "0..*" Task : owns
    Scheduler "1" --> "1" Owner : orchestrates
    Scheduler "1" o-- "0..*" ScheduledTask : daily_schedule
    ScheduledTask "1" --> "1" Task : wraps
    Task --> Task : mark_task_complete creates next occurrence
```

## Key relationships added in Phase 3

| Change | Why |
|---|---|
| `Task.scheduled_time: str` | Enables `sort_by_time()` using lambda key on `"HH:MM"` string |
| `Task.due_date: date` | Stores next-occurrence date created by `mark_task_complete()` |
| `Scheduler.sort_by_time()` | New method — returns all tasks sorted chronologically |
| `Scheduler.filter_by_pet()` | New method — scopes task list to one pet by name |
| `Scheduler.filter_by_status()` | New method — splits tasks by completion flag |
| `Scheduler.mark_task_complete()` | Extended completion: auto-creates recurring next task via `timedelta` |
| `Scheduler.detect_conflicts()` | New method — `itertools.combinations` overlap check |
| `Scheduler.get_conflict_warnings()` | New method — wraps conflicts as plain warning strings |
