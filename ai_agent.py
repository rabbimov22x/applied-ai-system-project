"""
PawPal+ AI Agent — agentic workflow powered by the Claude API.

Architecture
------------
User message → PawPalAgent.chat()
    → _run_agent_loop(): send message + tools to Claude
    → Claude responds with tool_use blocks
    → _dispatch() executes each tool against the live Scheduler/Owner/Pet state
    → tool results fed back to Claude
    → loop repeats until Claude issues a final text response (stop_reason="end_turn")

All API calls, tool invocations, and errors are written to logs/agent.log.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import anthropic

from pawpal_system import Owner, Pet, Scheduler, Task

# ---------------------------------------------------------------------------
# Logging — file + console
# ---------------------------------------------------------------------------
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

_file_handler = logging.FileHandler(LOG_DIR / "agent.log", encoding="utf-8")
_file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

log = logging.getLogger("pawpal_agent")
log.setLevel(logging.INFO)
if not log.handlers:
    log.addHandler(_file_handler)
    log.addHandler(logging.StreamHandler())


# ---------------------------------------------------------------------------
# Tool schema — defines what Claude can call
# ---------------------------------------------------------------------------
TOOLS: List[Dict] = [
    {
        "name": "create_pet",
        "description": "Register a new pet under the owner's care.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name":          {"type": "string"},
                "age":           {"type": "integer", "description": "Age in years"},
                "breed":         {"type": "string"},
                "special_needs": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Optional list of special care requirements",
                },
            },
            "required": ["name", "age", "breed"],
        },
    },
    {
        "name": "add_task",
        "description": "Add a care task to a specific pet.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pet_name":       {"type": "string"},
                "task_name":      {"type": "string"},
                "scheduled_time": {
                    "type": "string",
                    "description": "24-hour HH:MM format, e.g. '08:30'",
                },
                "duration_hours": {
                    "type": "number",
                    "description": "Duration in hours, e.g. 0.5 for 30 minutes",
                },
                "priority": {
                    "type": "integer", "minimum": 1, "maximum": 5,
                    "description": "1=low importance, 5=critical (medication, feeding)",
                },
                "frequency":    {"type": "string", "enum": ["daily", "weekly", "monthly"]},
                "description":  {"type": "string", "description": "Optional task details"},
            },
            "required": [
                "pet_name", "task_name", "scheduled_time",
                "duration_hours", "priority", "frequency",
            ],
        },
    },
    {
        "name": "list_pets_and_tasks",
        "description": "Return a full summary of all registered pets and their tasks.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "check_conflicts",
        "description": (
            "Detect scheduling conflicts — tasks whose time windows overlap. "
            "Call this after adding tasks to catch problems early."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "generate_schedule",
        "description": (
            "Build the optimized daily schedule from all pending tasks, "
            "ordered by priority then duration, capped at the owner's available hours."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "mark_task_done",
        "description": (
            "Mark a task complete for a given pet. "
            "For daily/weekly tasks the next occurrence is created automatically."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pet_name":  {"type": "string"},
                "task_name": {"type": "string"},
            },
            "required": ["pet_name", "task_name"],
        },
    },
]

# ---------------------------------------------------------------------------
# System prompt — sets the agent's role and decision rules
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
You are PawPal+, a knowledgeable and friendly pet care scheduling assistant.
You help pet owners organise their pets' daily routines by managing pets and \
tasks through the tools available to you.

## Workflow
When a user describes their pets or care needs in natural language:
1. Use create_pet for every pet mentioned.
2. Use add_task for every care activity, choosing sensible defaults if details \
   are not given.
3. Use check_conflicts after adding all tasks.
4. Use generate_schedule to show the day's plan.
5. Summarise what you did in friendly, plain language.

## Default priorities (if not specified)
- Medication / health checks : 5
- Feeding                    : 4
- Walks / exercise           : 4
- Grooming                   : 3
- Enrichment / play          : 2

## Default durations (if not specified)
- Feeding         : 0.25 h
- Walk            : 0.5 h
- Grooming        : 1.0 h
- Vet visit       : 1.5 h
- Medication      : 0.1 h

## Default time slots (if not specified)
- Morning tasks   : 07:00–09:00
- Midday tasks    : 12:00–13:00
- Evening tasks   : 17:00–19:00

Always be transparent about what you did and why. If a conflict is detected, \
explain it clearly and suggest a fix.
"""


# ---------------------------------------------------------------------------
# PawPalAgent
# ---------------------------------------------------------------------------
class PawPalAgent:
    """
    Agentic loop: receive natural-language input → call tools against the live
    Scheduler/Owner/Pet state → return a structured plain-language response.

    The agent maintains conversation history so follow-up messages work
    naturally within the same session.
    """

    MAX_ITERATIONS = 10  # safety cap to prevent infinite loops

    def __init__(self, owner: Owner, scheduler: Scheduler):
        self.owner = owner
        self.scheduler = scheduler
        self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
        self.conversation: List[Dict] = []

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def chat(self, user_message: str) -> str:
        """Send a message and run the full agentic loop until a final reply."""
        log.info("USER › %s", user_message)
        self.conversation.append({"role": "user", "content": user_message})

        try:
            reply = self._run_agent_loop()
        except anthropic.APIError as exc:
            log.error("Anthropic API error: %s", exc)
            reply = (
                "Sorry, I couldn't reach the AI service right now. "
                "Please check your ANTHROPIC_API_KEY and try again."
            )
        except Exception as exc:
            log.error("Unexpected agent error: %s", exc, exc_info=True)
            reply = f"An unexpected error occurred: {exc}"

        self.conversation.append({"role": "assistant", "content": reply})
        log.info("AGENT › %s", reply[:300])
        return reply

    def reset(self) -> None:
        """Clear conversation history for a fresh session."""
        self.conversation = []
        log.info("Conversation history cleared.")

    # ------------------------------------------------------------------
    # Agentic loop
    # ------------------------------------------------------------------

    def _run_agent_loop(self) -> str:
        """
        Iterate: call Claude → execute tool calls → feed results back → repeat.
        Stops when Claude sends stop_reason='end_turn' (no more tool calls).
        """
        messages = list(self.conversation)
        iterations = 0

        while iterations < self.MAX_ITERATIONS:
            iterations += 1

            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )
            log.info(
                "API response — stop_reason=%s  input_tokens=%s  output_tokens=%s",
                response.stop_reason,
                response.usage.input_tokens,
                response.usage.output_tokens,
            )

            text_blocks = [b.text for b in response.content if b.type == "text"]
            tool_calls  = [b for b in response.content if b.type == "tool_use"]

            # No more tool calls → we have the final answer
            if response.stop_reason == "end_turn" or not tool_calls:
                return "\n".join(text_blocks) if text_blocks else "(no response)"

            # Execute each tool call
            tool_results = []
            for call in tool_calls:
                result = self._dispatch(call.name, call.input)
                log.info("TOOL  %s(%s) → %s", call.name, call.input, str(result)[:300])
                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": call.id,
                    "content":     json.dumps(result),
                })

            # Append assistant turn + tool results before next iteration
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user",      "content": tool_results})

        log.warning("Agent loop hit MAX_ITERATIONS (%d) — returning partial response.", self.MAX_ITERATIONS)
        return "I hit my iteration limit. Please try a simpler request."

    # ------------------------------------------------------------------
    # Tool dispatcher
    # ------------------------------------------------------------------

    def _dispatch(self, name: str, inputs: Dict) -> Any:
        handler = getattr(self, f"_tool_{name}", None)
        if handler is None:
            log.warning("Unknown tool requested: %s", name)
            return {"error": f"Unknown tool: {name}"}
        try:
            result = handler(**inputs)
            log.info("TOOL  %s  args=%s  result=%s", name, inputs, str(result)[:200])
            return result
        except Exception as exc:
            log.error("Tool '%s' raised: %s  args=%s", name, exc, inputs)
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # Tool implementations — each maps to existing pawpal_system.py logic
    # ------------------------------------------------------------------

    def _tool_create_pet(
        self,
        name: str,
        age: int,
        breed: str,
        special_needs: Optional[List[str]] = None,
    ) -> Dict:
        if any(p.name.lower() == name.lower() for p in self.owner.pets):
            return {"status": "already_exists", "pet": name}
        pet = Pet(name=name, age=age, breed=breed)
        for need in (special_needs or []):
            pet.add_special_need(need)
        self.owner.add_pet(pet)
        return {"status": "created", "pet": name, "breed": breed, "age": age,
                "special_needs": special_needs or []}

    def _tool_add_task(
        self,
        pet_name: str,
        task_name: str,
        scheduled_time: str,
        duration_hours: float,
        priority: int,
        frequency: str,
        description: str = "",
    ) -> Dict:
        pet = next(
            (p for p in self.owner.pets if p.name.lower() == pet_name.lower()), None
        )
        if pet is None:
            return {"error": f"No pet named '{pet_name}'. Create them first with create_pet."}

        # Validate HH:MM
        try:
            h, m = scheduled_time.split(":")
            assert 0 <= int(h) <= 23 and 0 <= int(m) <= 59
        except Exception:
            return {"error": f"Invalid scheduled_time '{scheduled_time}'. Use HH:MM format."}

        task = Task(
            name=task_name,
            description=description or f"{task_name} for {pet.name}",
            scheduled_time=scheduled_time,
            duration_hours=duration_hours,
            priority=priority,
            frequency=frequency,
        )
        pet.add_task(task)
        return {
            "status": "added",
            "task": task_name,
            "pet": pet.name,
            "time": scheduled_time,
            "duration_hours": duration_hours,
            "priority": priority,
            "frequency": frequency,
        }

    def _tool_list_pets_and_tasks(self) -> Dict:
        if not self.owner.pets:
            return {"info": "No pets registered yet."}
        return {
            pet.name: {
                "breed": pet.breed,
                "age": pet.age,
                "special_needs": pet.special_needs,
                "tasks": [
                    {
                        "name": t.name,
                        "time": t.scheduled_time,
                        "duration_hours": t.duration_hours,
                        "priority": t.priority,
                        "frequency": t.frequency,
                        "status": "done" if t.completed else "pending",
                    }
                    for t in pet.tasks
                ],
            }
            for pet in self.owner.pets
        }

    def _tool_check_conflicts(self) -> Dict:
        warnings = self.scheduler.get_conflict_warnings()
        return {"conflict_count": len(warnings), "conflicts": warnings}

    def _tool_generate_schedule(self) -> Dict:
        schedule = self.scheduler.generate_schedule()
        if not schedule:
            return {"info": "No pending tasks to schedule."}
        return {
            "scheduled_task_count": len(schedule),
            "total_hours": round(sum(s.estimated_duration for s in schedule), 2),
            "schedule": [
                {
                    "slot": s.scheduled_time.strftime("%H:%M"),
                    "task": s.task.name,
                    "duration_hours": s.estimated_duration,
                }
                for s in schedule
            ],
            "explanation": self.scheduler.get_schedule_explanation(),
        }

    def _tool_mark_task_done(self, pet_name: str, task_name: str) -> Dict:
        pet = next(
            (p for p in self.owner.pets if p.name.lower() == pet_name.lower()), None
        )
        if pet is None:
            return {"error": f"No pet named '{pet_name}'."}

        task = next(
            (t for t in pet.tasks
             if t.name.lower() == task_name.lower() and not t.completed),
            None,
        )
        if task is None:
            return {"error": f"No pending task '{task_name}' found for {pet_name}."}

        next_task = self.scheduler.mark_task_complete(task.id)
        result: Dict = {"status": "completed", "task": task_name, "pet": pet_name}
        if next_task:
            result["next_occurrence_due"] = str(next_task.due_date)
        return result
