#!/usr/bin/env python3
"""
PawPal+ Phase 3 demo: sorting, filtering, recurring tasks, and conflict detection.
"""

from pawpal_system import Owner, Pet, Task, Scheduler


def print_task(task: Task, pet_name: str = "") -> None:
    label = f" [{pet_name}]" if pet_name else ""
    status = "DONE" if task.completed else "pending"
    print(f"  {task.scheduled_time} - {task.name}{label} | {task.duration_hours}h | priority {task.priority} | {status}")


def main():
    print("PawPal+ Phase 3: Algorithms Demo")
    print("=" * 50)

    # --- Setup ---
    owner = Owner(name="Alex Johnson", available_hours_per_day=6.0)

    dog = Pet(name="Buddy", age=3, breed="Golden Retriever")
    cat = Pet(name="Whiskers", age=2, breed="Siamese")
    owner.add_pet(dog)
    owner.add_pet(cat)

    # Tasks added OUT OF ORDER (intentionally scrambled times)
    dog.add_task(Task(name="Evening Walk",     scheduled_time="18:00", duration_hours=0.5,  priority=4, frequency="daily"))
    dog.add_task(Task(name="Morning Walk",     scheduled_time="07:30", duration_hours=0.5,  priority=5, frequency="daily"))
    dog.add_task(Task(name="Breakfast",        scheduled_time="08:00", duration_hours=0.25, priority=4, frequency="daily"))
    cat.add_task(Task(name="Litter Box",       scheduled_time="09:00", duration_hours=0.5,  priority=4, frequency="daily"))
    cat.add_task(Task(name="Vet Checkup",      scheduled_time="10:00", duration_hours=1.5,  priority=5, frequency="weekly"))
    # Duration conflict: Vet Checkup runs 10:00-11:30, Grooming starts at 11:00
    cat.add_task(Task(name="Grooming Session", scheduled_time="11:00", duration_hours=1.0,  priority=3, frequency="weekly"))
    # Exact same-time conflict: both dog and cat have a task at 09:00
    dog.add_task(Task(name="Medication",       scheduled_time="09:00", duration_hours=0.25, priority=5, frequency="daily"))

    scheduler = Scheduler(owner)

    # ------------------------------------------------------------------ #
    # Step 2a: Sort all tasks by scheduled_time
    # ------------------------------------------------------------------ #
    print("\n[Sort by Time]")
    for task in scheduler.sort_by_time():
        pet_name = next((p.name for p in owner.pets if p.id == task.pet_id), "?")
        print_task(task, pet_name)

    # ------------------------------------------------------------------ #
    # Step 2b: Filter by pet
    # ------------------------------------------------------------------ #
    print("\n[Filter: Buddy's tasks]")
    for task in scheduler.filter_by_pet("Buddy"):
        print_task(task)

    print("\n[Filter: Whiskers's tasks]")
    for task in scheduler.filter_by_pet("Whiskers"):
        print_task(task)

    # ------------------------------------------------------------------ #
    # Step 2c: Filter by completion status
    # ------------------------------------------------------------------ #
    print("\n[Filter: pending tasks]")
    for task in scheduler.filter_by_status(completed=False):
        print_task(task)

    # ------------------------------------------------------------------ #
    # Step 3: Recurring tasks — auto-create next occurrence on completion
    # ------------------------------------------------------------------ #
    print("\n[Recurring Task Demo]")
    morning_walk = dog.tasks[1]  # Morning Walk
    print(f"  Completing '{morning_walk.name}' (frequency: {morning_walk.frequency}) ...")
    next_task = scheduler.mark_task_complete(morning_walk.id)
    if next_task:
        print(f"  Auto-created next occurrence: '{next_task.name}' due {next_task.due_date}")

    breakfast = dog.tasks[2]  # Breakfast
    print(f"  Completing '{breakfast.name}' (frequency: {breakfast.frequency}) ...")
    next_task = scheduler.mark_task_complete(breakfast.id)
    if next_task:
        print(f"  Auto-created next occurrence: '{next_task.name}' due {next_task.due_date}")

    print("\n[Filter: completed tasks after marking]")
    for task in scheduler.filter_by_status(completed=True):
        print_task(task)

    # ------------------------------------------------------------------ #
    # Step 4: Conflict detection — warning strings, no crash
    # ------------------------------------------------------------------ #
    print("\n[Conflict Detection]")
    warnings = scheduler.get_conflict_warnings()
    if warnings:
        for warning in warnings:
            print(f"  {warning}")
    else:
        print("  No scheduling conflicts found.")

    # ------------------------------------------------------------------ #
    # Original priority-based schedule generation
    # ------------------------------------------------------------------ #
    print("\n[Generated Daily Schedule]")
    schedule = scheduler.generate_schedule()
    for st in schedule:
        pet_name = next((p.name for p in owner.pets if p.id == st.task.pet_id), "?")
        print(f"  {st.scheduled_time.strftime('%H:%M')} - {st.task.name} [{pet_name}] ({st.estimated_duration}h)")

    print("\nPawPal+ Phase 3 Complete!")


if __name__ == "__main__":
    main()
