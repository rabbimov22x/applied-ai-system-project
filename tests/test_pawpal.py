import pytest
from pawpal_system import Task, Pet


class TestTaskCompletion:
    """Test task completion functionality."""

    def test_mark_completed_changes_status(self):
        """Verify that calling mark_completed() actually changes the task's status."""
        # Create a new task
        task = Task(name="Test Task", description="A test task", duration_hours=1.0)

        # Initially, task should not be completed
        assert task.completed is False
        assert task.completed_at is None

        # Mark as completed
        task.mark_completed()

        # Now task should be completed with a timestamp
        assert task.completed is True
        assert task.completed_at is not None


class TestTaskAddition:
    """Test adding tasks to pets."""

    def test_adding_task_increases_pet_task_count(self):
        """Verify that adding a task to a Pet increases that pet's task count."""
        # Create a pet
        pet = Pet(name="Test Pet", age=2, breed="Test Breed")

        # Initially, pet should have no tasks
        initial_task_count = len(pet.tasks)
        assert initial_task_count == 0

        # Create and add a task
        task = Task(name="Test Task", description="A test task", duration_hours=1.0)
        pet.add_task(task)

        # Pet should now have one more task
        assert len(pet.tasks) == initial_task_count + 1
        assert len(pet.tasks) == 1

        # Verify the task was added correctly
        assert pet.tasks[0].name == "Test Task"
        assert pet.tasks[0].pet_id == pet.id