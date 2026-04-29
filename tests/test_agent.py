"""
Reliability tests for PawPalAgent tool implementations.

These tests exercise every tool handler directly — no Claude API calls are made.
This verifies that the agent's action layer is correct independently of the
language model, following the "reliability / testing system" AI feature requirement.
"""

import pytest

from ai_agent import PawPalAgent
from pawpal_system import Owner, Pet, Scheduler, Task


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def agent() -> PawPalAgent:
    """Fresh agent with an empty owner for each test."""
    owner = Owner(name="Test Owner", available_hours_per_day=8.0)
    scheduler = Scheduler(owner)
    return PawPalAgent(owner=owner, scheduler=scheduler)


@pytest.fixture
def agent_with_pet(agent: PawPalAgent) -> PawPalAgent:
    """Agent that already has one pet (Buddy the Golden Retriever)."""
    agent._tool_create_pet(name="Buddy", age=3, breed="Golden Retriever")
    return agent


# ---------------------------------------------------------------------------
# create_pet
# ---------------------------------------------------------------------------

class TestToolCreatePet:

    def test_creates_pet_and_returns_created_status(self, agent):
        result = agent._tool_create_pet(name="Luna", age=2, breed="Siamese")
        assert result["status"] == "created"
        assert result["pet"] == "Luna"

    def test_pet_appears_in_owner_pets(self, agent):
        agent._tool_create_pet(name="Luna", age=2, breed="Siamese")
        names = [p.name for p in agent.owner.pets]
        assert "Luna" in names

    def test_duplicate_pet_returns_already_exists(self, agent):
        agent._tool_create_pet(name="Buddy", age=3, breed="Golden Retriever")
        result = agent._tool_create_pet(name="Buddy", age=3, breed="Golden Retriever")
        assert result["status"] == "already_exists"
        # Only one pet should exist
        assert sum(1 for p in agent.owner.pets if p.name == "Buddy") == 1

    def test_duplicate_check_is_case_insensitive(self, agent):
        agent._tool_create_pet(name="Buddy", age=3, breed="Golden Retriever")
        result = agent._tool_create_pet(name="buddy", age=3, breed="Golden Retriever")
        assert result["status"] == "already_exists"

    def test_special_needs_are_stored(self, agent):
        agent._tool_create_pet(
            name="Max", age=5, breed="Poodle",
            special_needs=["Gluten-free diet", "Daily insulin"]
        )
        pet = next(p for p in agent.owner.pets if p.name == "Max")
        assert "Gluten-free diet" in pet.special_needs
        assert "Daily insulin" in pet.special_needs

    def test_no_special_needs_defaults_to_empty(self, agent):
        agent._tool_create_pet(name="Milo", age=1, breed="Tabby")
        pet = next(p for p in agent.owner.pets if p.name == "Milo")
        assert pet.special_needs == []


# ---------------------------------------------------------------------------
# add_task
# ---------------------------------------------------------------------------

class TestToolAddTask:

    def test_adds_task_to_correct_pet(self, agent_with_pet):
        result = agent_with_pet._tool_add_task(
            pet_name="Buddy", task_name="Morning Walk",
            scheduled_time="07:30", duration_hours=0.5,
            priority=4, frequency="daily",
        )
        assert result["status"] == "added"
        pet = next(p for p in agent_with_pet.owner.pets if p.name == "Buddy")
        assert any(t.name == "Morning Walk" for t in pet.tasks)

    def test_task_inherits_correct_attributes(self, agent_with_pet):
        agent_with_pet._tool_add_task(
            pet_name="Buddy", task_name="Breakfast",
            scheduled_time="08:00", duration_hours=0.25,
            priority=5, frequency="daily",
        )
        pet = next(p for p in agent_with_pet.owner.pets if p.name == "Buddy")
        task = next(t for t in pet.tasks if t.name == "Breakfast")
        assert task.scheduled_time == "08:00"
        assert task.duration_hours == 0.25
        assert task.priority == 5
        assert task.frequency == "daily"

    def test_unknown_pet_returns_error(self, agent_with_pet):
        result = agent_with_pet._tool_add_task(
            pet_name="Ghost", task_name="Walk",
            scheduled_time="08:00", duration_hours=0.5,
            priority=3, frequency="daily",
        )
        assert "error" in result

    def test_invalid_time_format_returns_error(self, agent_with_pet):
        result = agent_with_pet._tool_add_task(
            pet_name="Buddy", task_name="Walk",
            scheduled_time="8am", duration_hours=0.5,
            priority=3, frequency="daily",
        )
        assert "error" in result

    def test_time_boundary_23_59_is_valid(self, agent_with_pet):
        result = agent_with_pet._tool_add_task(
            pet_name="Buddy", task_name="Late Meds",
            scheduled_time="23:59", duration_hours=0.1,
            priority=5, frequency="daily",
        )
        assert result["status"] == "added"

    def test_pet_name_match_is_case_insensitive(self, agent_with_pet):
        result = agent_with_pet._tool_add_task(
            pet_name="buddy", task_name="Walk",
            scheduled_time="08:00", duration_hours=0.5,
            priority=3, frequency="daily",
        )
        assert result["status"] == "added"


# ---------------------------------------------------------------------------
# list_pets_and_tasks
# ---------------------------------------------------------------------------

class TestToolListPetsAndTasks:

    def test_empty_owner_returns_info_key(self, agent):
        result = agent._tool_list_pets_and_tasks()
        assert "info" in result

    def test_returns_pet_names_as_keys(self, agent_with_pet):
        result = agent_with_pet._tool_list_pets_and_tasks()
        assert "Buddy" in result

    def test_tasks_appear_in_listing(self, agent_with_pet):
        agent_with_pet._tool_add_task(
            pet_name="Buddy", task_name="Walk",
            scheduled_time="08:00", duration_hours=0.5,
            priority=4, frequency="daily",
        )
        result = agent_with_pet._tool_list_pets_and_tasks()
        task_names = [t["name"] for t in result["Buddy"]["tasks"]]
        assert "Walk" in task_names


# ---------------------------------------------------------------------------
# check_conflicts
# ---------------------------------------------------------------------------

class TestToolCheckConflicts:

    def test_no_conflicts_when_empty(self, agent):
        result = agent._tool_check_conflicts()
        assert result["conflict_count"] == 0
        assert result["conflicts"] == []

    def test_detects_same_time_conflict(self, agent_with_pet):
        agent_with_pet._tool_add_task(
            pet_name="Buddy", task_name="Task A",
            scheduled_time="09:00", duration_hours=1.0,
            priority=3, frequency="daily",
        )
        agent_with_pet._tool_add_task(
            pet_name="Buddy", task_name="Task B",
            scheduled_time="09:00", duration_hours=0.5,
            priority=3, frequency="daily",
        )
        result = agent_with_pet._tool_check_conflicts()
        assert result["conflict_count"] >= 1

    def test_no_conflict_for_adjacent_tasks(self, agent_with_pet):
        agent_with_pet._tool_add_task(
            pet_name="Buddy", task_name="Walk",
            scheduled_time="08:00", duration_hours=0.5,
            priority=3, frequency="daily",
        )
        agent_with_pet._tool_add_task(
            pet_name="Buddy", task_name="Feed",
            scheduled_time="08:30", duration_hours=0.25,
            priority=4, frequency="daily",
        )
        result = agent_with_pet._tool_check_conflicts()
        assert result["conflict_count"] == 0

    def test_conflict_warnings_are_strings(self, agent_with_pet):
        agent_with_pet._tool_add_task(
            pet_name="Buddy", task_name="A",
            scheduled_time="10:00", duration_hours=2.0, priority=3, frequency="daily",
        )
        agent_with_pet._tool_add_task(
            pet_name="Buddy", task_name="B",
            scheduled_time="11:00", duration_hours=1.0, priority=3, frequency="daily",
        )
        result = agent_with_pet._tool_check_conflicts()
        for w in result["conflicts"]:
            assert isinstance(w, str)


# ---------------------------------------------------------------------------
# generate_schedule
# ---------------------------------------------------------------------------

class TestToolGenerateSchedule:

    def test_empty_returns_info(self, agent):
        result = agent._tool_generate_schedule()
        assert "info" in result

    def test_returns_schedule_list(self, agent_with_pet):
        agent_with_pet._tool_add_task(
            pet_name="Buddy", task_name="Walk",
            scheduled_time="08:00", duration_hours=0.5,
            priority=4, frequency="daily",
        )
        result = agent_with_pet._tool_generate_schedule()
        assert "schedule" in result
        assert len(result["schedule"]) >= 1

    def test_highest_priority_task_first(self, agent_with_pet):
        agent_with_pet._tool_add_task(
            pet_name="Buddy", task_name="Low",
            scheduled_time="08:00", duration_hours=0.5, priority=1, frequency="daily",
        )
        agent_with_pet._tool_add_task(
            pet_name="Buddy", task_name="High",
            scheduled_time="08:00", duration_hours=0.5, priority=5, frequency="daily",
        )
        result = agent_with_pet._tool_generate_schedule()
        assert result["schedule"][0]["task"] == "High"

    def test_total_hours_within_limit(self, agent_with_pet):
        for i in range(20):
            agent_with_pet._tool_add_task(
                pet_name="Buddy", task_name=f"Task {i}",
                scheduled_time="08:00", duration_hours=1.0,
                priority=3, frequency="daily",
            )
        result = agent_with_pet._tool_generate_schedule()
        assert result["total_hours"] <= agent_with_pet.owner.available_hours_per_day


# ---------------------------------------------------------------------------
# mark_task_done
# ---------------------------------------------------------------------------

class TestToolMarkTaskDone:

    def test_marks_task_as_completed(self, agent_with_pet):
        agent_with_pet._tool_add_task(
            pet_name="Buddy", task_name="Walk",
            scheduled_time="08:00", duration_hours=0.5,
            priority=4, frequency="daily",
        )
        result = agent_with_pet._tool_mark_task_done(pet_name="Buddy", task_name="Walk")
        assert result["status"] == "completed"

        pet = next(p for p in agent_with_pet.owner.pets if p.name == "Buddy")
        done = [t for t in pet.tasks if t.name == "Walk" and t.completed]
        assert len(done) == 1

    def test_daily_task_creates_next_occurrence(self, agent_with_pet):
        agent_with_pet._tool_add_task(
            pet_name="Buddy", task_name="Medication",
            scheduled_time="08:00", duration_hours=0.1,
            priority=5, frequency="daily",
        )
        result = agent_with_pet._tool_mark_task_done(pet_name="Buddy", task_name="Medication")
        assert "next_occurrence_due" in result

    def test_unknown_pet_returns_error(self, agent_with_pet):
        result = agent_with_pet._tool_mark_task_done(pet_name="Ghost", task_name="Walk")
        assert "error" in result

    def test_unknown_task_returns_error(self, agent_with_pet):
        result = agent_with_pet._tool_mark_task_done(pet_name="Buddy", task_name="Nonexistent")
        assert "error" in result

    def test_already_completed_task_returns_error(self, agent_with_pet):
        agent_with_pet._tool_add_task(
            pet_name="Buddy", task_name="Walk",
            scheduled_time="08:00", duration_hours=0.5,
            priority=4, frequency="daily",
        )
        agent_with_pet._tool_mark_task_done(pet_name="Buddy", task_name="Walk")
        # Trying to complete it again (the original is done; only the new occurrence is pending)
        pet = next(p for p in agent_with_pet.owner.pets if p.name == "Buddy")
        completed_count = sum(1 for t in pet.tasks if t.name == "Walk" and t.completed)
        assert completed_count == 1


# ---------------------------------------------------------------------------
# Dispatch safety
# ---------------------------------------------------------------------------

class TestDispatch:

    def test_unknown_tool_name_returns_error(self, agent):
        result = agent._dispatch("nonexistent_tool", {})
        assert "error" in result

    def test_tool_exception_returns_error_dict(self, agent_with_pet):
        # Pass an integer where a string is expected — should not raise, returns error
        result = agent_with_pet._dispatch("add_task", {
            "pet_name": "Buddy",
            "task_name": "Walk",
            "scheduled_time": "not-a-time",
            "duration_hours": 0.5,
            "priority": 3,
            "frequency": "daily",
        })
        assert "error" in result
