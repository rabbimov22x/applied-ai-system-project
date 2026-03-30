from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime, time, date, timedelta
import itertools
import uuid


@dataclass
class Task:
    """Represents a single pet care activity."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    duration_hours: float = 1.0
    priority: int = 3  # 1=low, 5=high
    frequency: str = "daily"  # daily, weekly, monthly
    scheduled_time: str = "08:00"  # "HH:MM" format for sorting
    due_date: Optional[date] = None
    completed: bool = False
    completed_at: Optional[datetime] = None
    pet_id: Optional[str] = None  # Reference to associated pet

    def set_priority(self, level: int) -> None:
        """Set the priority level of the task (1-5)."""
        if 1 <= level <= 5:
            self.priority = level
        else:
            raise ValueError("Priority must be between 1 and 5")

    def get_duration(self) -> float:
        """Get the duration of the task in hours."""
        return self.duration_hours

    def get_priority(self) -> int:
        """Get the priority level of the task."""
        return self.priority

    def is_urgent(self) -> bool:
        """Check if the task is urgent (priority 4 or 5)."""
        return self.priority >= 4

    def mark_completed(self) -> None:
        """Mark the task as completed."""
        self.completed = True
        self.completed_at = datetime.now()

    def reset_completion(self) -> None:
        """Reset the task completion status."""
        self.completed = False
        self.completed_at = None


@dataclass
class Pet:
    """Stores pet details and manages associated tasks."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    age: int = 0
    breed: str = ""
    special_needs: List[str] = field(default_factory=list)
    preferences: Dict[str, str] = field(default_factory=dict)
    tasks: List[Task] = field(default_factory=list)

    def add_special_need(self, need: str) -> None:
        """Add a special need to the pet."""
        if need not in self.special_needs:
            self.special_needs.append(need)

    def remove_special_need(self, need: str) -> None:
        """Remove a special need from the pet."""
        if need in self.special_needs:
            self.special_needs.remove(need)

    def get_special_needs(self) -> List[str]:
        """Get all special needs for the pet."""
        return self.special_needs.copy()

    def add_task(self, task: Task) -> None:
        """Add a task to this pet."""
        task.pet_id = self.id
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> bool:
        """Remove a task from this pet. Returns True if found and removed."""
        for i, task in enumerate(self.tasks):
            if task.id == task_id:
                self.tasks.pop(i)
                return True
        return False

    def get_tasks(self) -> List[Task]:
        """Get all tasks for this pet."""
        return self.tasks.copy()

    def get_pending_tasks(self) -> List[Task]:
        """Get all incomplete tasks for this pet."""
        return [task for task in self.tasks if not task.completed]


class Owner:
    """Manages multiple pets and provides access to all their tasks."""

    def __init__(self, name: str, available_hours_per_day: float = 8.0,
                 preferences: Optional[Dict] = None, timezone: str = "UTC"):
        self.name = name
        self.available_hours_per_day = available_hours_per_day
        self.preferences = preferences or {}
        self.timezone = timezone
        self.pets: List[Pet] = []

    def set_available_hours(self, hours: float) -> None:
        """Set the available hours per day for pet care."""
        if hours > 0:
            self.available_hours_per_day = hours
        else:
            raise ValueError("Available hours must be positive")

    def set_preferences(self, preferences: Dict) -> None:
        """Set owner preferences for scheduling."""
        self.preferences = preferences

    def get_available_hours(self) -> float:
        """Get the available hours per day for pet care."""
        return self.available_hours_per_day

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to the owner's care."""
        self.pets.append(pet)

    def remove_pet(self, pet_id: str) -> bool:
        """Remove a pet from the owner's care. Returns True if found and removed."""
        for i, pet in enumerate(self.pets):
            if pet.id == pet_id:
                self.pets.pop(i)
                return True
        return False

    def get_pets(self) -> List[Pet]:
        """Get all pets owned by this owner."""
        return self.pets.copy()

    def get_all_tasks(self) -> List[Task]:
        """Get all tasks across all pets owned by this owner."""
        all_tasks = []
        for pet in self.pets:
            all_tasks.extend(pet.get_tasks())
        return all_tasks

    def get_pending_tasks(self) -> List[Task]:
        """Get all incomplete tasks across all pets."""
        all_pending = []
        for pet in self.pets:
            all_pending.extend(pet.get_pending_tasks())
        return all_pending

    def get_pet_by_id(self, pet_id: str) -> Optional[Pet]:
        """Get a specific pet by ID."""
        for pet in self.pets:
            if pet.id == pet_id:
                return pet
        return None


@dataclass
class ScheduledTask:
    """Represents a task scheduled at a specific time."""
    task: Task
    scheduled_time: time
    estimated_duration: float

    def __str__(self) -> str:
        return f"{self.scheduled_time.strftime('%H:%M')} - {self.task.name} ({self.estimated_duration}h)"


class Scheduler:
    """The 'Brain' that retrieves, organizes, and manages tasks across pets."""

    def __init__(self, owner: Owner):
        self.owner = owner
        self.daily_schedule: List[ScheduledTask] = []

    def add_task(self, task: Task, pet_id: Optional[str] = None) -> None:
        """Add a task to a specific pet or create a new pet if none specified."""
        if pet_id:
            pet = self.owner.get_pet_by_id(pet_id)
            if pet:
                pet.add_task(task)
            else:
                raise ValueError(f"Pet with ID {pet_id} not found")
        else:
            # If no pet specified, add to first pet or create a generic one
            if self.owner.pets:
                self.owner.pets[0].add_task(task)
            else:
                # Create a default pet if none exist
                default_pet = Pet(name="My Pet", age=1, breed="Unknown")
                self.owner.add_pet(default_pet)
                default_pet.add_task(task)

    def remove_task(self, task_id: str) -> bool:
        """Remove a task by ID from any pet. Returns True if found and removed."""
        for pet in self.owner.pets:
            if pet.remove_task(task_id):
                return True
        return False

    def generate_schedule(self) -> List[ScheduledTask]:
        """Generate a daily schedule based on tasks and constraints."""
        pending_tasks = self.owner.get_pending_tasks()

        if not pending_tasks:
            self.daily_schedule = []
            return self.daily_schedule

        # Sort tasks by priority (highest first) then by duration (shortest first)
        sorted_tasks = sorted(pending_tasks,
                            key=lambda t: (-t.priority, t.duration_hours))

        # Simple scheduling: start at 8 AM, schedule tasks sequentially
        schedule = []
        current_time = time(8, 0)  # Start at 8:00 AM
        available_hours = self.owner.available_hours_per_day

        total_scheduled_hours = 0

        for task in sorted_tasks:
            if total_scheduled_hours + task.duration_hours <= available_hours:
                scheduled_task = ScheduledTask(
                    task=task,
                    scheduled_time=current_time,
                    estimated_duration=task.duration_hours
                )
                schedule.append(scheduled_task)

                # Update time (simplified - doesn't handle hour overflow)
                hours_to_add = int(task.duration_hours)
                minutes_to_add = int((task.duration_hours % 1) * 60)
                new_hour = current_time.hour + hours_to_add
                new_minute = current_time.minute + minutes_to_add

                if new_minute >= 60:
                    new_hour += 1
                    new_minute -= 60

                current_time = time(new_hour, new_minute)
                total_scheduled_hours += task.duration_hours
            else:
                break  # No more time available

        self.daily_schedule = schedule
        return self.daily_schedule

    def validate_schedule(self) -> bool:
        """Validate if the current schedule fits within available time."""
        total_duration = sum(task.estimated_duration for task in self.daily_schedule)
        return total_duration <= self.owner.available_hours_per_day

    def optimize_task_order(self) -> List[Task]:
        """Return tasks in optimized order (by priority, then duration)."""
        pending_tasks = self.owner.get_pending_tasks()
        return sorted(pending_tasks,
                     key=lambda t: (-t.priority, t.duration_hours))

    def get_schedule_explanation(self) -> str:
        """Get an explanation of why the schedule was created this way."""
        if not self.daily_schedule:
            return "No tasks are currently scheduled. Generate a schedule first."

        total_tasks = len(self.daily_schedule)
        total_hours = sum(task.estimated_duration for task in self.daily_schedule)

        explanation = f"Scheduled {total_tasks} tasks totaling {total_hours:.1f} hours within your {self.owner.available_hours_per_day} hour daily limit.\n\n"
        explanation += "Tasks are ordered by:\n"
        explanation += "1. Priority (highest first)\n"
        explanation += "2. Duration (shortest first)\n\n"
        explanation += "This ensures critical tasks are completed first while maximizing the number of tasks that fit in your schedule."

        return explanation

    def sort_by_time(self) -> List[Task]:
        """Return all tasks sorted by their scheduled_time (HH:MM string)."""
        all_tasks = self.owner.get_all_tasks()
        return sorted(all_tasks, key=lambda t: t.scheduled_time)

    def filter_by_pet(self, pet_name: str) -> List[Task]:
        """Return tasks belonging to a specific pet (case-insensitive name match)."""
        for pet in self.owner.pets:
            if pet.name.lower() == pet_name.lower():
                return pet.get_tasks()
        return []

    def filter_by_status(self, completed: bool) -> List[Task]:
        """Return all tasks filtered by completion status."""
        return [t for t in self.owner.get_all_tasks() if t.completed == completed]

    def mark_task_complete(self, task_id: str) -> Optional[Task]:
        """Mark a task complete and auto-create the next occurrence for recurring tasks.

        Returns the newly created Task if one was generated, otherwise None.
        """
        for pet in self.owner.pets:
            for task in pet.tasks:
                if task.id == task_id:
                    task.mark_completed()
                    if task.frequency == "daily":
                        next_due = date.today() + timedelta(days=1)
                    elif task.frequency == "weekly":
                        next_due = date.today() + timedelta(weeks=1)
                    else:
                        return None  # No recurrence for other frequencies

                    next_task = Task(
                        name=task.name,
                        description=task.description,
                        duration_hours=task.duration_hours,
                        priority=task.priority,
                        frequency=task.frequency,
                        scheduled_time=task.scheduled_time,
                        due_date=next_due,
                    )
                    pet.add_task(next_task)
                    return next_task
        return None

    def detect_conflicts(self) -> List[Tuple[Task, Task]]:
        """Detect pairs of incomplete tasks whose time windows overlap.

        Uses itertools.combinations to examine every unique task pair without
        double-counting. Each task's window is [scheduled_time, scheduled_time
        + duration_hours). Two windows overlap when one starts before the
        other ends.

        Returns:
            List of (Task, Task) tuples where the two tasks conflict.
        """
        def to_minutes(hhmm: str) -> int:
            h, m = hhmm.split(":")
            return int(h) * 60 + int(m)

        pending = self.filter_by_status(completed=False)
        return [
            (a, b)
            for a, b in itertools.combinations(pending, 2)
            if to_minutes(a.scheduled_time) < to_minutes(b.scheduled_time) + int(b.duration_hours * 60)
            and to_minutes(b.scheduled_time) < to_minutes(a.scheduled_time) + int(a.duration_hours * 60)
        ]

    def get_conflict_warnings(self) -> List[str]:
        """Return human-readable warning strings for every scheduling conflict.

        Calls detect_conflicts() internally and formats each overlapping pair
        as a plain warning message. Returns an empty list when there are no
        conflicts, so callers can safely check ``if warnings`` without risk of
        an exception.

        Returns:
            List of warning strings, one per conflicting task pair.
        """
        warnings: List[str] = []
        for a, b in self.detect_conflicts():
            warnings.append(
                f"WARNING: '{a.name}' ({a.scheduled_time}, {a.duration_hours}h) "
                f"conflicts with '{b.name}' ({b.scheduled_time}, {b.duration_hours}h)"
            )
        return warnings