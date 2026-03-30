"""
Automated test suite for PawPal+ (pawpal_system.py).

Coverage areas
--------------
- Task completion and reset
- Adding tasks to pets
- sort_by_time: chronological ordering
- filter_by_pet: pet-scoped task retrieval
- filter_by_status: completion-status filtering
- mark_task_complete: recurring task generation
- detect_conflicts / get_conflict_warnings: overlap detection
- generate_schedule: priority ordering and hour-cap enforcement
- validate_schedule: schedule integrity check
- Edge cases: empty pets, no tasks, invalid inputs
"""

from datetime import date, timedelta

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_scheduler(*pets: Pet, hours: float = 8.0) -> Scheduler:
    """Build a minimal Owner + Scheduler with the supplied pets."""
    owner = Owner(name="Test Owner", available_hours_per_day=hours)
    for pet in pets:
        owner.add_pet(pet)
    return Scheduler(owner)


def make_pet(name: str = "Rex", *task_tuples) -> Pet:
    """Create a pet and optionally add tasks given as (name, scheduled_time, duration, priority) tuples."""
    pet = Pet(name=name, age=2, breed="Mixed")
    for t in task_tuples:
        task_name, stime, dur, pri = t
        pet.add_task(Task(name=task_name, scheduled_time=stime, duration_hours=dur, priority=pri))
    return pet


# ---------------------------------------------------------------------------
# Existing tests (preserved)
# ---------------------------------------------------------------------------

class TestTaskCompletion:
    """Test task completion functionality."""

    def test_mark_completed_changes_status(self):
        """Verify that calling mark_completed() actually changes the task's status."""
        task = Task(name="Test Task", description="A test task", duration_hours=1.0)

        assert task.completed is False
        assert task.completed_at is None

        task.mark_completed()

        assert task.completed is True
        assert task.completed_at is not None

    def test_reset_completion_clears_status(self):
        """reset_completion() should restore completed=False and clear the timestamp."""
        task = Task(name="Walk")
        task.mark_completed()
        task.reset_completion()

        assert task.completed is False
        assert task.completed_at is None


class TestTaskAddition:
    """Test adding tasks to pets."""

    def test_adding_task_increases_pet_task_count(self):
        """Verify that adding a task to a Pet increases that pet's task count."""
        pet = Pet(name="Test Pet", age=2, breed="Test Breed")

        assert len(pet.tasks) == 0

        task = Task(name="Test Task", description="A test task", duration_hours=1.0)
        pet.add_task(task)

        assert len(pet.tasks) == 1
        assert pet.tasks[0].name == "Test Task"
        assert pet.tasks[0].pet_id == pet.id


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------

class TestSortByTime:
    """Verify sort_by_time() returns tasks in chronological HH:MM order."""

    def test_tasks_returned_in_chronological_order(self):
        """Tasks added in reverse order should be sorted earliest-first."""
        pet = make_pet(
            "Buddy",
            ("Evening Walk", "18:00", 0.5, 3),
            ("Breakfast",    "08:00", 0.25, 4),
            ("Lunch",        "12:30", 0.25, 3),
            ("Morning Walk", "07:30", 0.5, 5),
        )
        scheduler = make_scheduler(pet)

        sorted_tasks = scheduler.sort_by_time()
        times = [t.scheduled_time for t in sorted_tasks]

        assert times == sorted(times), "sort_by_time() did not return tasks in chronological order"

    def test_already_sorted_tasks_unchanged(self):
        """Tasks already in order should remain in the same order."""
        pet = make_pet(
            "Milo",
            ("Medication", "07:00", 0.1, 5),
            ("Walk",       "09:00", 0.5, 4),
            ("Grooming",   "14:00", 1.0, 3),
        )
        scheduler = make_scheduler(pet)

        times = [t.scheduled_time for t in scheduler.sort_by_time()]
        assert times == ["07:00", "09:00", "14:00"]

    def test_single_task_still_works(self):
        """A single task should be returned without error."""
        pet = make_pet("Solo", ("Walk", "10:00", 0.5, 3))
        scheduler = make_scheduler(pet)

        result = scheduler.sort_by_time()
        assert len(result) == 1
        assert result[0].name == "Walk"

    def test_no_pets_returns_empty_list(self):
        """Owner with no pets should return an empty list."""
        scheduler = make_scheduler()
        assert scheduler.sort_by_time() == []


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

class TestFilterByPet:
    """Verify filter_by_pet() scopes results to the correct pet."""

    def test_returns_only_named_pets_tasks(self):
        """Tasks from other pets must not appear in the filtered result."""
        dog = make_pet("Buddy", ("Walk", "08:00", 0.5, 4))
        cat = make_pet("Whiskers", ("Litter Box", "09:00", 0.25, 3))
        scheduler = make_scheduler(dog, cat)

        result = scheduler.filter_by_pet("Buddy")
        names = [t.name for t in result]

        assert "Walk" in names
        assert "Litter Box" not in names

    def test_case_insensitive_match(self):
        """Pet name matching should be case-insensitive."""
        pet = make_pet("Buddy", ("Walk", "08:00", 0.5, 4))
        scheduler = make_scheduler(pet)

        assert len(scheduler.filter_by_pet("buddy")) == 1
        assert len(scheduler.filter_by_pet("BUDDY")) == 1
        assert len(scheduler.filter_by_pet("BuDdY")) == 1

    def test_nonexistent_pet_returns_empty_list(self):
        """Filtering by an unknown pet name must return [] without raising."""
        pet = make_pet("Buddy", ("Walk", "08:00", 0.5, 4))
        scheduler = make_scheduler(pet)

        assert scheduler.filter_by_pet("Ghost") == []

    def test_pet_with_no_tasks_returns_empty_list(self):
        """A pet that exists but has no tasks should yield an empty list."""
        pet = Pet(name="Bare", age=1, breed="Unknown")
        scheduler = make_scheduler(pet)

        assert scheduler.filter_by_pet("Bare") == []


class TestFilterByStatus:
    """Verify filter_by_status() splits tasks by completion flag."""

    def test_pending_tasks_only(self):
        pet = make_pet("Rex", ("Walk", "08:00", 0.5, 3), ("Feed", "12:00", 0.25, 4))
        pet.tasks[0].mark_completed()
        scheduler = make_scheduler(pet)

        pending = scheduler.filter_by_status(completed=False)
        assert all(not t.completed for t in pending)
        assert len(pending) == 1
        assert pending[0].name == "Feed"

    def test_completed_tasks_only(self):
        pet = make_pet("Rex", ("Walk", "08:00", 0.5, 3), ("Feed", "12:00", 0.25, 4))
        pet.tasks[0].mark_completed()
        scheduler = make_scheduler(pet)

        done = scheduler.filter_by_status(completed=True)
        assert all(t.completed for t in done)
        assert len(done) == 1
        assert done[0].name == "Walk"

    def test_all_pending_when_none_completed(self):
        pet = make_pet("Rex", ("Walk", "08:00", 0.5, 3), ("Feed", "12:00", 0.25, 4))
        scheduler = make_scheduler(pet)

        assert len(scheduler.filter_by_status(completed=False)) == 2
        assert scheduler.filter_by_status(completed=True) == []

    def test_all_completed_when_all_done(self):
        pet = make_pet("Rex", ("Walk", "08:00", 0.5, 3))
        pet.tasks[0].mark_completed()
        scheduler = make_scheduler(pet)

        assert len(scheduler.filter_by_status(completed=True)) == 1
        assert scheduler.filter_by_status(completed=False) == []


# ---------------------------------------------------------------------------
# Recurring tasks
# ---------------------------------------------------------------------------

class TestRecurrence:
    """Verify mark_task_complete() auto-generates the next occurrence."""

    def test_daily_task_next_due_is_tomorrow(self):
        """Completing a daily task should create a new task due tomorrow."""
        pet = make_pet("Buddy", ("Morning Walk", "07:30", 0.5, 5))
        pet.tasks[0].frequency = "daily"
        scheduler = make_scheduler(pet)

        next_task = scheduler.mark_task_complete(pet.tasks[0].id)

        assert next_task is not None
        assert next_task.due_date == date.today() + timedelta(days=1)

    def test_weekly_task_next_due_is_next_week(self):
        """Completing a weekly task should create a new task due in 7 days."""
        pet = make_pet("Whiskers", ("Vet Checkup", "10:00", 1.5, 5))
        pet.tasks[0].frequency = "weekly"
        scheduler = make_scheduler(pet)

        next_task = scheduler.mark_task_complete(pet.tasks[0].id)

        assert next_task is not None
        assert next_task.due_date == date.today() + timedelta(weeks=1)

    def test_monthly_task_returns_none(self):
        """A 'monthly' frequency task should not spawn a new occurrence."""
        pet = make_pet("Rex", ("Flea Treatment", "09:00", 0.5, 4))
        pet.tasks[0].frequency = "monthly"
        scheduler = make_scheduler(pet)

        result = scheduler.mark_task_complete(pet.tasks[0].id)
        assert result is None

    def test_original_task_marked_completed(self):
        """The original task must be marked complete after calling mark_task_complete()."""
        pet = make_pet("Buddy", ("Walk", "08:00", 0.5, 4))
        original = pet.tasks[0]
        scheduler = make_scheduler(pet)

        scheduler.mark_task_complete(original.id)

        assert original.completed is True

    def test_new_task_starts_as_incomplete(self):
        """The auto-created next occurrence must not be pre-completed."""
        pet = make_pet("Buddy", ("Walk", "08:00", 0.5, 4))
        scheduler = make_scheduler(pet)

        next_task = scheduler.mark_task_complete(pet.tasks[0].id)

        assert next_task is not None
        assert next_task.completed is False

    def test_new_task_inherits_attributes(self):
        """The new occurrence should copy name, scheduled_time, duration, and frequency."""
        pet = make_pet("Buddy", ("Morning Walk", "07:30", 0.5, 5))
        original = pet.tasks[0]
        original.frequency = "daily"
        scheduler = make_scheduler(pet)

        next_task = scheduler.mark_task_complete(original.id)

        assert next_task.name == original.name
        assert next_task.scheduled_time == original.scheduled_time
        assert next_task.duration_hours == original.duration_hours
        assert next_task.frequency == original.frequency

    def test_pet_task_count_increases_after_recurrence(self):
        """Completing a recurring task should add one more task to the pet's list."""
        pet = make_pet("Buddy", ("Walk", "08:00", 0.5, 4))
        scheduler = make_scheduler(pet)

        count_before = len(pet.tasks)
        scheduler.mark_task_complete(pet.tasks[0].id)

        assert len(pet.tasks) == count_before + 1

    def test_unknown_task_id_returns_none(self):
        """Passing a non-existent task ID should return None gracefully."""
        pet = make_pet("Buddy")
        scheduler = make_scheduler(pet)

        assert scheduler.mark_task_complete("does-not-exist") is None


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

class TestConflictDetection:
    """Verify detect_conflicts() and get_conflict_warnings()."""

    def test_exact_same_time_is_a_conflict(self):
        """Two tasks starting at the identical time must be flagged."""
        pet = make_pet(
            "Rex",
            ("Medication", "09:00", 0.25, 5),
            ("Litter Box", "09:00", 0.5,  4),
        )
        scheduler = make_scheduler(pet)

        conflicts = scheduler.detect_conflicts()
        assert len(conflicts) == 1

    def test_overlapping_windows_is_a_conflict(self):
        """A task starting inside another task's window must be flagged."""
        # Vet Checkup: 10:00 → 11:30, Grooming: 11:00 → 12:00 → overlap
        pet = make_pet(
            "Whiskers",
            ("Vet Checkup",      "10:00", 1.5, 5),
            ("Grooming Session", "11:00", 1.0, 3),
        )
        scheduler = make_scheduler(pet)

        conflicts = scheduler.detect_conflicts()
        assert len(conflicts) == 1
        names = {conflicts[0][0].name, conflicts[0][1].name}
        assert names == {"Vet Checkup", "Grooming Session"}

    def test_adjacent_tasks_are_not_a_conflict(self):
        """Tasks that abut exactly (end == next start) must NOT be flagged."""
        # Walk: 10:00 → 11:00, Feed: 11:00 → 11:30 — windows touch but don't overlap
        pet = make_pet(
            "Rex",
            ("Walk", "10:00", 1.0, 4),
            ("Feed", "11:00", 0.5, 3),
        )
        scheduler = make_scheduler(pet)

        assert scheduler.detect_conflicts() == []

    def test_completed_tasks_excluded_from_conflict_check(self):
        """A completed task must not participate in conflict detection."""
        pet = make_pet(
            "Rex",
            ("Task A", "09:00", 1.0, 3),
            ("Task B", "09:00", 1.0, 3),
        )
        pet.tasks[0].mark_completed()  # Remove Task A from consideration
        scheduler = make_scheduler(pet)

        assert scheduler.detect_conflicts() == []

    def test_no_tasks_no_conflicts(self):
        pet = Pet(name="Empty", age=1, breed="Unknown")
        scheduler = make_scheduler(pet)

        assert scheduler.detect_conflicts() == []

    def test_one_task_no_conflicts(self):
        pet = make_pet("Rex", ("Walk", "08:00", 0.5, 3))
        scheduler = make_scheduler(pet)

        assert scheduler.detect_conflicts() == []

    def test_conflicts_across_different_pets(self):
        """Conflicts between tasks of different pets must also be detected."""
        dog = make_pet("Buddy",   ("Vet", "10:00", 2.0, 5))
        cat = make_pet("Whiskers", ("Groom", "11:00", 1.0, 3))
        scheduler = make_scheduler(dog, cat)

        # Vet: 10:00-12:00, Groom: 11:00-12:00 → overlap
        conflicts = scheduler.detect_conflicts()
        assert len(conflicts) == 1

    def test_get_conflict_warnings_returns_strings(self):
        """get_conflict_warnings() must return non-empty strings starting with 'WARNING:'."""
        pet = make_pet("Rex", ("A", "09:00", 1.0, 3), ("B", "09:00", 1.0, 3))
        scheduler = make_scheduler(pet)

        warnings = scheduler.get_conflict_warnings()
        assert len(warnings) == 1
        assert warnings[0].startswith("WARNING:")

    def test_get_conflict_warnings_empty_when_no_conflicts(self):
        pet = make_pet("Rex", ("Walk", "08:00", 0.5, 3), ("Feed", "12:00", 0.25, 4))
        scheduler = make_scheduler(pet)

        assert scheduler.get_conflict_warnings() == []


# ---------------------------------------------------------------------------
# Schedule generation
# ---------------------------------------------------------------------------

class TestScheduleGeneration:
    """Verify generate_schedule() priority ordering and hour-cap behavior."""

    def test_empty_task_list_produces_empty_schedule(self):
        pet = Pet(name="Ghost", age=1, breed="Unknown")
        scheduler = make_scheduler(pet)

        assert scheduler.generate_schedule() == []

    def test_highest_priority_task_scheduled_first(self):
        """The task with the highest priority should appear first in the schedule."""
        pet = make_pet(
            "Rex",
            ("Low Priority Task",  "08:00", 0.5, 1),
            ("High Priority Task", "08:00", 0.5, 5),
        )
        scheduler = make_scheduler(pet)

        schedule = scheduler.generate_schedule()
        assert schedule[0].task.priority == 5

    def test_schedule_respects_available_hours(self):
        """Tasks that exceed the owner's daily hour limit must be excluded."""
        pet = make_pet(
            "Rex",
            ("Task 1", "08:00", 1.0, 3),
            ("Task 2", "09:00", 1.0, 3),
            ("Task 3", "10:00", 1.0, 3),
        )
        # Only 2 hours available → at most 2 tasks scheduled
        scheduler = make_scheduler(pet, hours=2.0)

        schedule = scheduler.generate_schedule()
        total_hours = sum(st.estimated_duration for st in schedule)
        assert total_hours <= 2.0

    def test_validate_schedule_true_for_valid_schedule(self):
        pet = make_pet("Rex", ("Walk", "08:00", 0.5, 3))
        scheduler = make_scheduler(pet, hours=4.0)
        scheduler.generate_schedule()

        assert scheduler.validate_schedule() is True

    def test_all_tasks_complete_returns_empty_schedule(self):
        """If every task is already done, no schedule items should be generated."""
        pet = make_pet("Rex", ("Walk", "08:00", 0.5, 3))
        pet.tasks[0].mark_completed()
        scheduler = make_scheduler(pet)

        assert scheduler.generate_schedule() == []


# ---------------------------------------------------------------------------
# Edge cases and input validation
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Guard rails: invalid inputs, boundary conditions."""

    def test_set_priority_rejects_out_of_range(self):
        task = Task(name="Walk")
        with pytest.raises(ValueError):
            task.set_priority(0)
        with pytest.raises(ValueError):
            task.set_priority(6)

    def test_set_priority_accepts_boundary_values(self):
        task = Task(name="Walk")
        task.set_priority(1)
        assert task.priority == 1
        task.set_priority(5)
        assert task.priority == 5

    def test_set_available_hours_rejects_zero_and_negative(self):
        owner = Owner(name="Alex", available_hours_per_day=6.0)
        with pytest.raises(ValueError):
            owner.set_available_hours(0)
        with pytest.raises(ValueError):
            owner.set_available_hours(-1)

    def test_is_urgent_threshold(self):
        low = Task(name="Low", priority=3)
        high = Task(name="High", priority=4)
        assert low.is_urgent() is False
        assert high.is_urgent() is True

    def test_remove_task_returns_false_for_unknown_id(self):
        pet = Pet(name="Rex", age=1, breed="Unknown")
        assert pet.remove_task("nonexistent-id") is False

    def test_remove_pet_returns_false_for_unknown_id(self):
        owner = Owner(name="Alex")
        assert owner.remove_pet("nonexistent-id") is False

    def test_add_special_need_no_duplicates(self):
        pet = Pet(name="Rex", age=1, breed="Mixed")
        pet.add_special_need("Gluten-free diet")
        pet.add_special_need("Gluten-free diet")

        assert pet.special_needs.count("Gluten-free diet") == 1
