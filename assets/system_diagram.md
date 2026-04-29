# PawPal+ System Architecture Diagram

Paste this Mermaid code at https://mermaid.live to render and export as `system_diagram.png`.

```mermaid
flowchart TD
    User(["👤 Pet Owner\n(natural language input)"])

    subgraph UI["Streamlit UI — app.py"]
        Tabs["Tabs: Pets | Tasks | Conflicts | Schedule | 🤖 AI Assistant"]
        ChatInput["st.chat_input / starter prompts"]
        Display["st.table · st.warning · st.success\nst.chat_message · st.expander"]
    end

    subgraph Agent["PawPalAgent — ai_agent.py"]
        direction TB
        Loop["Agentic Loop\n_run_agent_loop()"]
        Dispatch["Tool Dispatcher\n_dispatch()"]

        subgraph Tools["Tool Implementations"]
            T1["create_pet()"]
            T2["add_task()"]
            T3["list_pets_and_tasks()"]
            T4["check_conflicts()"]
            T5["generate_schedule()"]
            T6["mark_task_done()"]
        end
    end

    subgraph Model["Claude API (claude-sonnet-4-6)"]
        Prompt["System Prompt\n+ Tool Schemas"]
        Response["tool_use blocks\nor end_turn text"]
    end

    subgraph Core["Scheduling Engine — pawpal_system.py"]
        Owner["Owner"]
        Pet["Pet\n(tasks: List[Task])"]
        Task["Task\n(scheduled_time, priority,\nfrequency, due_date)"]
        Scheduler["Scheduler\nsort_by_time · filter_by_pet\ndetect_conflicts · generate_schedule\nmark_task_complete"]
    end

    subgraph Logging["Guardrails & Logging"]
        Log["logs/agent.log\n(all API calls, tool results, errors)"]
        Guard["Input validation\n(HH:MM format, priority 1–5,\nMAX_ITERATIONS cap)"]
        ErrReturn["Errors returned as\n{error: ...} dicts\n— never crash"]
    end

    subgraph Testing["Reliability / Testing System"]
        UnitTests["tests/test_agent.py\n30 tool-layer tests\n(no API calls)"]
        SchedTests["tests/test_pawpal.py\n44 scheduler tests"]
    end

    User -->|"chat message"| ChatInput
    ChatInput --> Loop
    Loop -->|"messages + tools"| Model
    Model -->|"tool_use"| Dispatch
    Dispatch --> Tools
    T1 --> Owner
    T2 --> Pet
    T3 --> Owner
    T4 --> Scheduler
    T5 --> Scheduler
    T6 --> Scheduler
    Owner --> Pet --> Task
    Scheduler -->|"reads"| Owner
    Tools -->|"tool_result JSON"| Loop
    Model -->|"end_turn text"| Display
    Display --> User
    Loop --> Log
    Dispatch --> Guard
    Guard --> ErrReturn
    UnitTests -.->|"verify"| Tools
    SchedTests -.->|"verify"| Scheduler
```

## Component responsibilities

| Component | Role |
|---|---|
| **Streamlit UI** | Renders the 5-tab interface; holds session state for owner, scheduler, agent, and chat history |
| **PawPalAgent** | Runs the agentic loop: sends messages to Claude, executes tool calls, feeds results back, repeats until `end_turn` |
| **Claude API** | Plans which tools to call and in what order; produces the final plain-language response |
| **Tool layer** | Thin adapters that translate Claude's JSON inputs into calls against `pawpal_system.py` classes |
| **Scheduling Engine** | Pure Python logic — `Owner`, `Pet`, `Task`, `Scheduler`; the single source of truth for all data |
| **Logging** | Every API call, tool invocation, and error is written to `logs/agent.log` |
| **Guardrails** | Time format validation, priority range check, `MAX_ITERATIONS` cap, error dicts instead of exceptions |
| **Test suite** | 30 tool-layer tests (no API) + 44 scheduler tests = 74 total; CI-safe |

## Data flow

```
User types: "Add daily morning walk for Buddy at 7:30"
    ↓
PawPalAgent.chat()
    ↓
Claude sees message + tool schemas → responds with tool_use: add_task(...)
    ↓
_dispatch("add_task", {pet_name:"Buddy", task_name:"Morning Walk", ...})
    ↓
Pet.add_task(Task(scheduled_time="07:30", ...))   ← pawpal_system.py
    ↓
tool_result JSON fed back to Claude
    ↓
Claude responds: "I've added a 30-minute morning walk for Buddy at 7:30 AM..."
    ↓
st.chat_message("assistant") renders reply + UI tabs update automatically
```
