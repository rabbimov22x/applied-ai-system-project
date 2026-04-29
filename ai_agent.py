"""
PawPal+ AI Agent — agentic workflow powered by the Claude API.

Stretch features
----------------
RAG (Retrieval-Augmented Generation):
    Before every API call the agent retrieves the most relevant entries
    from the pet care knowledge base (rag.py) and injects them into the
    system prompt so Claude can ground advice in real care guidelines.
    Toggle with use_rag=True/False.

Observable intermediate steps:
    chat_with_steps() returns both the final reply and a structured log
    of every intermediate action (retrieve, tool_call, tool_result,
    api_response). The UI renders these as an expandable trace panel.

Few-shot specialization:
    When specialized=True, two example exchanges are prepended to the
    conversation before the user message. These examples teach Claude
    to include breed-specific notes and a "Confidence:" statement in
    every response. Output measurably differs from the baseline (checked
    by the reliability evaluator).
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import anthropic

from pawpal_system import Owner, Pet, Scheduler, Task
from rag import format_context, retrieve

# ---------------------------------------------------------------------------
# Logging
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
# Tool schemas
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
                    "description": "Optional special care requirements",
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
                "scheduled_time": {"type": "string", "description": "HH:MM format"},
                "duration_hours": {"type": "number"},
                "priority": {
                    "type": "integer", "minimum": 1, "maximum": 5,
                    "description": "1=low, 5=critical",
                },
                "frequency":   {"type": "string", "enum": ["daily", "weekly", "monthly"]},
                "description": {"type": "string"},
            },
            "required": [
                "pet_name", "task_name", "scheduled_time",
                "duration_hours", "priority", "frequency",
            ],
        },
    },
    {
        "name": "list_pets_and_tasks",
        "description": "Return a summary of all registered pets and their tasks.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "check_conflicts",
        "description": "Detect tasks whose time windows overlap.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "generate_schedule",
        "description": (
            "Build the daily schedule from all pending tasks, "
            "ordered by priority then duration, capped at available hours."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "mark_task_done",
        "description": (
            "Mark a task complete. Daily/weekly tasks auto-create "
            "the next occurrence."
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
# Base system prompt
# ---------------------------------------------------------------------------
BASE_SYSTEM_PROMPT = """\
You are PawPal+, a knowledgeable and friendly pet care scheduling assistant.
You help pet owners organise their pets' daily routines through the tools
available to you.

## Workflow
1. Use create_pet for every pet mentioned.
2. Use add_task for each care activity; apply sensible defaults when details \
are missing.
3. Use check_conflicts after adding all tasks.
4. Use generate_schedule to present the day's plan.
5. Summarise what you did in clear, friendly language.

## Default priorities
- Medication / health : 5   Feeding : 4   Walks : 4
- Grooming : 3              Enrichment / play : 2

## Default durations
- Feeding 0.25 h   Walk 0.5 h   Grooming 1.0 h   Vet visit 1.5 h   Medication 0.1 h

## Default time slots
- Morning 07:00-09:00   Midday 12:00-13:00   Evening 17:00-19:00

Always explain what you did and why. If a conflict is detected, describe it \
and suggest a fix.
"""

# ---------------------------------------------------------------------------
# Few-shot examples for specialization mode
# ---------------------------------------------------------------------------
# These two example turns teach Claude to include breed-specific notes and
# end every response with a "Confidence:" line. This makes the output
# measurably different from the baseline (checked in the eval script).
FEW_SHOT_MESSAGES: List[Dict] = [
    {
        "role": "user",
        "content": (
            "I have a 5-year-old Golden Retriever named Max. "
            "What daily tasks should I add for him?"
        ),
    },
    {
        "role": "assistant",
        "content": (
            "Breed note: Golden Retrievers are high-energy dogs that need "
            "1-2 hours of vigorous exercise daily and brushing 2-3 times per week.\n\n"
            "Here is what I recommend for Max:\n"
            "- Morning Walk (07:30, 0.5 h, priority 4, daily)\n"
            "- Breakfast (08:00, 0.25 h, priority 4, daily)\n"
            "- Evening Walk (17:30, 0.5 h, priority 4, daily)\n"
            "- Brushing (09:00, 0.25 h, priority 3, daily)\n\n"
            "Confidence: High — recommendations are based on Golden Retriever "
            "breed-standard care guidelines."
        ),
    },
    {
        "role": "user",
        "content": "Add a weekly vet checkup for Max on Monday mornings.",
    },
    {
        "role": "assistant",
        "content": (
            "Breed note: Annual or bi-annual vet visits are standard for adult dogs; "
            "weekly checkups are unusual and may indicate an ongoing health condition.\n\n"
            "I have added:\n"
            "- Vet Checkup (09:00, 1.5 h, priority 5, weekly)\n\n"
            "No conflicts detected with existing tasks.\n\n"
            "Confidence: High — task added as requested; flagged frequency as \
atypical for reference."
        ),
    },
]


# ---------------------------------------------------------------------------
# PawPalAgent
# ---------------------------------------------------------------------------
class PawPalAgent:
    """
    Agentic loop: natural-language input -> optional RAG retrieval ->
    Claude API with tool use -> observable intermediate steps ->
    plain-language response.

    Parameters
    ----------
    owner       : Owner instance (shared with Streamlit session state)
    scheduler   : Scheduler instance (shared with Streamlit session state)
    use_rag     : inject retrieved knowledge base context (default True)
    specialized : prepend few-shot examples for structured output (default False)
    """

    MAX_ITERATIONS = 10

    def __init__(
        self,
        owner: Owner,
        scheduler: Scheduler,
        use_rag: bool = True,
        specialized: bool = False,
    ):
        self.owner = owner
        self.scheduler = scheduler
        self.use_rag = use_rag
        self.specialized = specialized
        self.client = anthropic.Anthropic()
        self.conversation: List[Dict] = []

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def chat(self, user_message: str) -> str:
        """Send a message and return the agent's reply."""
        reply, _ = self._run(user_message)
        return reply

    def chat_with_steps(self, user_message: str) -> Tuple[str, List[Dict]]:
        """
        Send a message and return (reply, steps).

        steps is a list of dicts, each describing one observable action:
            {"step": int, "type": "retrieve"|"tool_call"|"tool_result"|"api_response",
             ...type-specific keys...}

        This makes the agent's multi-step reasoning visible so humans can
        inspect what it did and why at each stage.
        """
        return self._run(user_message)

    def reset(self) -> None:
        self.conversation = []
        log.info("Conversation history cleared.")

    # ------------------------------------------------------------------
    # Core run method (shared by chat and chat_with_steps)
    # ------------------------------------------------------------------

    def _run(self, user_message: str) -> Tuple[str, List[Dict]]:
        log.info("USER › %s", user_message)
        steps: List[Dict] = []
        step_n = 0

        # Step 0: RAG retrieval
        rag_context = ""
        if self.use_rag:
            docs = retrieve(user_message, top_k=3)
            rag_context = format_context(docs)
            step_n += 1
            steps.append({
                "step": step_n,
                "type": "retrieve",
                "query": user_message[:120],
                "retrieved_count": len(docs),
                "docs": [
                    {"id": d["id"], "category": d["category"],
                     "score": d["score"], "text": d["text"]}
                    for d in docs
                ],
            })
            log.info("RAG retrieved %d docs for query: %s", len(docs), user_message[:80])

        # Build the system prompt (base + RAG context)
        system = BASE_SYSTEM_PROMPT
        if rag_context:
            system = system + "\n\n" + rag_context

        # Build the message history (few-shot prefix + conversation + new message)
        self.conversation.append({"role": "user", "content": user_message})
        prefix = FEW_SHOT_MESSAGES if self.specialized else []
        messages = prefix + list(self.conversation)

        try:
            reply = self._agent_loop(system, messages, steps, step_n)
        except anthropic.APIError as exc:
            log.error("Anthropic API error: %s", exc)
            reply = (
                "Sorry, I could not reach the AI service. "
                "Check your ANTHROPIC_API_KEY and try again."
            )
        except Exception as exc:
            log.error("Unexpected agent error: %s", exc, exc_info=True)
            reply = f"An unexpected error occurred: {exc}"

        self.conversation.append({"role": "assistant", "content": reply})
        log.info("AGENT › %s", reply[:300])
        return reply, steps

    # ------------------------------------------------------------------
    # Agentic loop
    # ------------------------------------------------------------------

    def _agent_loop(
        self, system: str, messages: List[Dict], steps: List[Dict], step_n: int
    ) -> str:
        iterations = 0

        while iterations < self.MAX_ITERATIONS:
            iterations += 1

            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=system,
                tools=TOOLS,
                messages=messages,
            )

            step_n += 1
            steps.append({
                "step": step_n,
                "type": "api_response",
                "stop_reason": response.stop_reason,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            })
            log.info(
                "API response  stop_reason=%s  in=%s  out=%s",
                response.stop_reason,
                response.usage.input_tokens,
                response.usage.output_tokens,
            )

            text_blocks = [b.text for b in response.content if b.type == "text"]
            tool_calls  = [b for b in response.content if b.type == "tool_use"]

            if response.stop_reason == "end_turn" or not tool_calls:
                return "\n".join(text_blocks) if text_blocks else "(no response)"

            tool_results = []
            for call in tool_calls:
                # Record the tool call as an observable step
                step_n += 1
                steps.append({
                    "step": step_n,
                    "type": "tool_call",
                    "tool": call.name,
                    "args": call.input,
                })

                result = self._dispatch(call.name, call.input)

                # Record the tool result as an observable step
                step_n += 1
                steps.append({
                    "step": step_n,
                    "type": "tool_result",
                    "tool": call.name,
                    "result": result,
                    "is_error": "error" in result,
                })

                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": call.id,
                    "content":     json.dumps(result),
                })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user",      "content": tool_results})

        log.warning("Agent loop hit MAX_ITERATIONS (%d).", self.MAX_ITERATIONS)
        return "I reached my iteration limit. Please try a simpler request."

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
    # Tool implementations
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
            return {"error": f"No pet named '{pet_name}'. Create them first."}
        try:
            h, m = scheduled_time.split(":")
            assert 0 <= int(h) <= 23 and 0 <= int(m) <= 59
        except Exception:
            return {"error": f"Invalid scheduled_time '{scheduled_time}'. Use HH:MM."}

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
            "status": "added", "task": task_name, "pet": pet.name,
            "time": scheduled_time, "duration_hours": duration_hours,
            "priority": priority, "frequency": frequency,
        }

    def _tool_list_pets_and_tasks(self) -> Dict:
        if not self.owner.pets:
            return {"info": "No pets registered yet."}
        return {
            pet.name: {
                "breed": pet.breed, "age": pet.age,
                "special_needs": pet.special_needs,
                "tasks": [
                    {"name": t.name, "time": t.scheduled_time,
                     "duration_hours": t.duration_hours, "priority": t.priority,
                     "frequency": t.frequency,
                     "status": "done" if t.completed else "pending"}
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
                {"slot": s.scheduled_time.strftime("%H:%M"),
                 "task": s.task.name, "duration_hours": s.estimated_duration}
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
            return {"error": f"No pending task '{task_name}' for {pet_name}."}
        next_task = self.scheduler.mark_task_complete(task.id)
        result: Dict = {"status": "completed", "task": task_name, "pet": pet_name}
        if next_task:
            result["next_occurrence_due"] = str(next_task.due_date)
        return result
