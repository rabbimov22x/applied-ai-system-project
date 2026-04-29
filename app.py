"""PawPal+ Streamlit app — Phase 4 final UI + AI Agent."""

import os

import streamlit as st

from ai_agent import PawPalAgent
from pawpal_system import Owner, Pet, Task, Scheduler

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

# ---------------------------------------------------------------------------
# Session-state bootstrap
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan", available_hours_per_day=8.0)
if "scheduler" not in st.session_state:
    st.session_state.scheduler = Scheduler(st.session_state.owner)
if "use_rag" not in st.session_state:
    st.session_state.use_rag = True
if "specialized" not in st.session_state:
    st.session_state.specialized = False
if "agent" not in st.session_state:
    st.session_state.agent = PawPalAgent(
        st.session_state.owner,
        st.session_state.scheduler,
        use_rag=st.session_state.use_rag,
        specialized=st.session_state.specialized,
    )
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # list of {"role": "user"|"assistant", "content": str, "steps": list}
if "last_steps" not in st.session_state:
    st.session_state.last_steps = []


def scheduler() -> Scheduler:
    return st.session_state.scheduler


def owner() -> Owner:
    return st.session_state.owner


def pet_name_for(task: Task) -> str:
    for pet in owner().pets:
        if pet.id == task.pet_id:
            return pet.name
    return "Unknown"


# ---------------------------------------------------------------------------
# Sidebar — owner settings
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("🐾 PawPal+")
    st.caption("Smart pet care scheduling")

    st.divider()
    st.subheader("Owner settings")
    owner_name = st.text_input("Your name", value=owner().name)
    if owner_name != owner().name:
        owner().name = owner_name

    available_hours = st.slider(
        "Available hours / day", min_value=1.0, max_value=16.0,
        value=owner().available_hours_per_day, step=0.5
    )
    if available_hours != owner().available_hours_per_day:
        owner().available_hours_per_day = available_hours

    st.divider()
    st.subheader("AI settings")
    use_rag = st.toggle("RAG knowledge base", value=st.session_state.use_rag,
                        help="Retrieve pet care guidelines from the knowledge base before each response.")
    specialized = st.toggle("Specialization mode", value=st.session_state.specialized,
                            help="Use few-shot examples that add breed notes and a confidence rating to every response.")
    if use_rag != st.session_state.use_rag or specialized != st.session_state.specialized:
        st.session_state.use_rag = use_rag
        st.session_state.specialized = specialized
        st.session_state.agent.use_rag = use_rag
        st.session_state.agent.specialized = specialized

    st.divider()
    # Always-visible conflict banner in sidebar
    warnings = scheduler().get_conflict_warnings()
    if warnings:
        st.error(f"⚠️ {len(warnings)} scheduling conflict(s) detected")
        for w in warnings:
            st.caption(w)
    else:
        st.success("✅ No scheduling conflicts")


# ---------------------------------------------------------------------------
# Main area — tabs
# ---------------------------------------------------------------------------
st.title("🐾 PawPal+")
st.caption(f"Owner: **{owner().name}** · {owner().available_hours_per_day:.1f} hrs/day available")

tab_pets, tab_tasks, tab_conflicts, tab_schedule, tab_ai = st.tabs(
    ["🐶 Pets", "📋 Tasks", "⚠️ Conflicts", "📅 Schedule", "🤖 AI Assistant"]
)


# ── Tab 1: Pets ──────────────────────────────────────────────────────────────
with tab_pets:
    st.subheader("Add a pet")
    col1, col2, col3 = st.columns(3)
    with col1:
        pet_name = st.text_input("Pet name", value="Buddy")
    with col2:
        pet_age = st.number_input("Age (years)", min_value=0, max_value=30, value=2)
    with col3:
        pet_breed = st.text_input("Breed", value="Golden Retriever")

    if st.button("Add Pet", type="primary"):
        owner().add_pet(Pet(name=pet_name, age=pet_age, breed=pet_breed))
        st.success(f"Added **{pet_name}** ({pet_breed})")
        st.rerun()

    st.divider()
    st.subheader("Your pets")
    pets = owner().get_pets()
    if not pets:
        st.info("No pets yet — add one above.")
    else:
        for pet in pets:
            pending = len(pet.get_pending_tasks())
            total = len(pet.get_tasks())
            with st.expander(f"**{pet.name}** — {pet.breed}, {pet.age} yr", expanded=True):
                st.write(f"Tasks: {pending} pending / {total} total")
                if pet.special_needs:
                    st.write("Special needs: " + ", ".join(pet.special_needs))


# ── Tab 2: Tasks ─────────────────────────────────────────────────────────────
with tab_tasks:
    st.subheader("Add a task")

    pets = owner().get_pets()
    if not pets:
        st.warning("Add a pet first (Pets tab).")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            task_name = st.text_input("Task name", value="Morning Walk")
            task_desc = st.text_input("Description", value="")
        with col2:
            task_time = st.text_input("Scheduled time (HH:MM)", value="08:00")
            duration = st.number_input("Duration (hours)", min_value=0.1, max_value=8.0,
                                       value=0.5, step=0.1)
        with col3:
            priority = st.selectbox("Priority (1=low, 5=high)", [1, 2, 3, 4, 5], index=3)
            frequency = st.selectbox("Frequency", ["daily", "weekly", "monthly"])
            target_pet = st.selectbox("Pet", [p.name for p in pets])

        if st.button("Add Task", type="primary"):
            # Validate time format
            try:
                h, m = task_time.split(":")
                assert 0 <= int(h) <= 23 and 0 <= int(m) <= 59
            except Exception:
                st.error("Scheduled time must be in HH:MM format (e.g. 08:30).")
            else:
                pet = next(p for p in pets if p.name == target_pet)
                pet.add_task(Task(
                    name=task_name,
                    description=task_desc or f"{task_name} for {pet.name}",
                    scheduled_time=task_time,
                    duration_hours=duration,
                    priority=priority,
                    frequency=frequency,
                ))
                st.success(f"Added **{task_name}** to {target_pet}")
                st.rerun()

    st.divider()

    # Filters
    st.subheader("View tasks")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filter_pet = st.selectbox(
            "Filter by pet",
            ["All pets"] + [p.name for p in owner().get_pets()]
        )
    with col_f2:
        filter_status = st.selectbox("Filter by status", ["All", "Pending", "Completed"])

    # Gather tasks
    if filter_pet == "All pets":
        tasks = scheduler().sort_by_time()
    else:
        tasks = sorted(scheduler().filter_by_pet(filter_pet),
                       key=lambda t: t.scheduled_time)

    if filter_status == "Pending":
        tasks = [t for t in tasks if not t.completed]
    elif filter_status == "Completed":
        tasks = [t for t in tasks if t.completed]

    if not tasks:
        st.info("No tasks match your filters.")
    else:
        rows = []
        for task in tasks:
            rows.append({
                "Time": task.scheduled_time,
                "Task": task.name,
                "Pet": pet_name_for(task),
                "Duration": f"{task.duration_hours}h",
                "Priority": "⭐" * task.priority,
                "Frequency": task.frequency,
                "Status": "✅ Done" if task.completed else "⏳ Pending",
            })
        st.table(rows)

    # Mark complete
    st.divider()
    st.subheader("Mark a task complete")
    pending_tasks = scheduler().filter_by_status(completed=False)
    if not pending_tasks:
        st.info("All tasks are already complete.")
    else:
        task_options = {f"{t.scheduled_time} – {t.name} ({pet_name_for(t)})": t
                        for t in pending_tasks}
        chosen_label = st.selectbox("Select task to complete", list(task_options))
        if st.button("Mark complete"):
            chosen = task_options[chosen_label]
            next_task = scheduler().mark_task_complete(chosen.id)
            st.success(f"**{chosen.name}** marked complete!")
            if next_task:
                st.info(
                    f"🔁 Recurring task — next **{next_task.name}** "
                    f"automatically scheduled for {next_task.due_date} "
                    f"({next_task.frequency})"
                )
            st.rerun()


# ── Tab 3: Conflicts ─────────────────────────────────────────────────────────
with tab_conflicts:
    st.subheader("Scheduling conflict checker")
    st.caption(
        "Two tasks conflict when their time windows overlap "
        "(e.g. a 90-minute vet visit starting at 10:00 blocks anything before 11:30)."
    )

    warnings = scheduler().get_conflict_warnings()
    conflicts = scheduler().detect_conflicts()

    if not conflicts:
        st.success("✅ No conflicts found — your schedule is clean!")
    else:
        st.error(f"⚠️ {len(conflicts)} conflict(s) found. Please adjust task times or durations.")
        for i, (a, b) in enumerate(conflicts, 1):
            with st.expander(f"Conflict {i}: **{a.name}** ↔ **{b.name}**", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**{a.name}**")
                    st.write(f"Pet: {pet_name_for(a)}")
                    st.write(f"Starts: {a.scheduled_time}")
                    st.write(f"Duration: {a.duration_hours}h")
                    a_end_min = int(a.scheduled_time.split(":")[0]) * 60 \
                              + int(a.scheduled_time.split(":")[1]) \
                              + int(a.duration_hours * 60)
                    st.write(f"Ends: {a_end_min // 60:02d}:{a_end_min % 60:02d}")
                with col2:
                    st.markdown(f"**{b.name}**")
                    st.write(f"Pet: {pet_name_for(b)}")
                    st.write(f"Starts: {b.scheduled_time}")
                    st.write(f"Duration: {b.duration_hours}h")
                    b_end_min = int(b.scheduled_time.split(":")[0]) * 60 \
                              + int(b.scheduled_time.split(":")[1]) \
                              + int(b.duration_hours * 60)
                    st.write(f"Ends: {b_end_min // 60:02d}:{b_end_min % 60:02d}")

                st.warning(
                    "Fix: move one task earlier/later, or shorten its duration "
                    "so the windows no longer overlap."
                )


# ── Tab 4: Schedule ───────────────────────────────────────────────────────────
with tab_schedule:
    st.subheader("Generate today's schedule")

    # Warn about conflicts before generating
    warnings = scheduler().get_conflict_warnings()
    if warnings:
        st.warning(
            f"⚠️ **{len(warnings)} conflict(s) exist** — resolve them in the Conflicts tab "
            "for the most accurate schedule."
        )

    if st.button("Generate Schedule", type="primary"):
        if not owner().get_pets():
            st.error("Add at least one pet first.")
        elif not owner().get_pending_tasks():
            st.warning("No pending tasks. Add tasks or mark existing ones incomplete.")
        else:
            schedule = scheduler().generate_schedule()

            if not schedule:
                st.info("No tasks could be scheduled (all may be complete).")
            else:
                st.success(
                    f"Scheduled **{len(schedule)} task(s)** across "
                    f"{owner().available_hours_per_day:.1f} available hours."
                )

                # Schedule table
                rows = []
                for st_item in schedule:
                    task = st_item.task
                    rows.append({
                        "Slot": st_item.scheduled_time.strftime("%H:%M"),
                        "Task": task.name,
                        "Pet": pet_name_for(task),
                        "Duration": f"{st_item.estimated_duration}h",
                        "Priority": "⭐" * task.priority,
                    })
                st.table(rows)

                # Explanation
                with st.expander("💡 Why this order?"):
                    st.write(scheduler().get_schedule_explanation())

                # Validation
                if scheduler().validate_schedule():
                    st.success("✅ Schedule fits within your available time.")
                else:
                    st.warning("⚠️ Total duration exceeds your daily limit.")


# ── Tab 5: AI Assistant ───────────────────────────────────────────────────────
with tab_ai:
    st.subheader("🤖 AI Assistant")
    st.caption(
        "Describe your pets and care needs in plain English. "
        "The AI will create pets, add tasks, check conflicts, and generate your schedule automatically."
    )

    # API key guard
    api_key_set = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if not api_key_set:
        st.warning(
            "**ANTHROPIC_API_KEY not set.** "
            "Add it to your environment before using the AI Assistant:\n\n"
            "```bash\nexport ANTHROPIC_API_KEY=sk-ant-...\nstreamlit run app.py\n```"
        )

    # Active mode indicators
    mode_parts = []
    if st.session_state.use_rag:
        mode_parts.append("RAG on")
    if st.session_state.specialized:
        mode_parts.append("Specialization on")
    if mode_parts:
        st.caption("Active: " + " · ".join(mode_parts))

    # Starter prompts
    with st.expander("💡 Try one of these prompts", expanded=not bool(st.session_state.chat_history)):
        examples = [
            "I have a 3-year-old Golden Retriever named Buddy. He needs a morning walk, breakfast, and an evening walk every day.",
            "Add a weekly grooming session for Buddy on Saturday mornings, and daily medication at 8am.",
            "Check if there are any scheduling conflicts and generate today's schedule.",
            "Mark Buddy's morning walk as done.",
        ]
        for ex in examples:
            if st.button(ex, key=f"ex_{ex[:20]}"):
                st.session_state.chat_history.append({"role": "user", "content": ex, "steps": []})
                if api_key_set:
                    with st.spinner("Thinking..."):
                        reply, steps = st.session_state.agent.chat_with_steps(ex)
                    st.session_state.chat_history.append({"role": "assistant", "content": reply, "steps": steps})
                else:
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": "⚠️ Set ANTHROPIC_API_KEY to enable the AI assistant.",
                        "steps": [],
                    })
                st.rerun()

    # Render conversation history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            steps = msg.get("steps", [])
            if steps and msg["role"] == "assistant":
                with st.expander(f"🔍 Agent reasoning ({len(steps)} step(s))", expanded=False):
                    for s in steps:
                        stype = s.get("type", "")
                        if stype == "retrieve":
                            st.markdown(f"**Step {s['step']} — RAG retrieve** · query: `{s['query']}` · {s['retrieved_count']} doc(s)")
                            for doc in s.get("docs", []):
                                st.caption(f"[{doc['category']}] {doc['text'][:120]}...")
                        elif stype == "api_response":
                            st.markdown(f"**Step {s['step']} — API response** · stop: `{s.get('stop_reason', '?')}` · {s.get('content_blocks', 0)} block(s)")
                        elif stype == "tool_call":
                            import json
                            st.markdown(f"**Step {s['step']} — Tool call** · `{s['tool']}`")
                            st.code(json.dumps(s.get("args", {}), indent=2), language="json")
                        elif stype == "tool_result":
                            import json
                            status = "error" if s.get("is_error") else "ok"
                            st.markdown(f"**Step {s['step']} — Tool result** · `{s['tool']}` · {status}")
                            st.code(json.dumps(s.get("result", {}), indent=2), language="json")

    # Chat input
    user_input = st.chat_input("Ask PawPal+ anything about your pet care schedule...")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input, "steps": []})
        with st.chat_message("user"):
            st.markdown(user_input)

        if api_key_set:
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    reply, steps = st.session_state.agent.chat_with_steps(user_input)
                st.markdown(reply)
                if steps:
                    with st.expander(f"🔍 Agent reasoning ({len(steps)} step(s))", expanded=False):
                        for s in steps:
                            stype = s.get("type", "")
                            if stype == "retrieve":
                                st.markdown(f"**Step {s['step']} — RAG retrieve** · query: `{s['query']}` · {s['retrieved_count']} doc(s)")
                                for doc in s.get("docs", []):
                                    st.caption(f"[{doc['category']}] {doc['text'][:120]}...")
                            elif stype == "api_response":
                                st.markdown(f"**Step {s['step']} — API response** · stop: `{s.get('stop_reason', '?')}` · {s.get('content_blocks', 0)} block(s)")
                            elif stype == "tool_call":
                                import json
                                st.markdown(f"**Step {s['step']} — Tool call** · `{s['tool']}`")
                                st.code(json.dumps(s.get("args", {}), indent=2), language="json")
                            elif stype == "tool_result":
                                import json
                                status = "error" if s.get("is_error") else "ok"
                                st.markdown(f"**Step {s['step']} — Tool result** · `{s['tool']}` · {status}")
                                st.code(json.dumps(s.get("result", {}), indent=2), language="json")
        else:
            reply = "⚠️ Set ANTHROPIC_API_KEY to enable the AI assistant."
            steps = []
            with st.chat_message("assistant"):
                st.markdown(reply)

        st.session_state.chat_history.append({"role": "assistant", "content": reply, "steps": steps})
        st.rerun()

    # Reset button
    if st.session_state.chat_history:
        if st.button("🗑 Clear conversation"):
            st.session_state.chat_history = []
            st.session_state.agent.reset()
            st.rerun()
