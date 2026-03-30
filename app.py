"""PawPal+ Streamlit app — Phase 4 final UI."""

import streamlit as st
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

tab_pets, tab_tasks, tab_conflicts, tab_schedule = st.tabs(
    ["🐶 Pets", "📋 Tasks", "⚠️ Conflicts", "📅 Schedule"]
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
