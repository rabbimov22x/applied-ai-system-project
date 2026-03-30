import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# Initialize session state for persistent data
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan", available_hours_per_day=8.0)

if "scheduler" not in st.session_state:
    st.session_state.scheduler = Scheduler(st.session_state.owner)

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Quick Demo Inputs (UI only)")
owner_name = st.text_input("Owner name", value=st.session_state.owner.name)
pet_name = st.text_input("Pet name", value="Mochi")
pet_age = st.number_input("Pet age", min_value=0, max_value=30, value=2)
pet_breed = st.text_input("Pet breed", value="Golden Retriever")

# Update owner name if changed
if owner_name != st.session_state.owner.name:
    st.session_state.owner.name = owner_name

if st.button("Add Pet"):
    new_pet = Pet(name=pet_name, age=pet_age, breed=pet_breed)
    st.session_state.owner.add_pet(new_pet)
    st.success(f"Added pet: {pet_name} ({pet_breed})")
    st.rerun()  # Refresh to show updated pet list

# Display current pets
if st.session_state.owner.get_pets():
    st.write("Current pets:")
    for pet in st.session_state.owner.get_pets():
        st.write(f"- {pet.name} ({pet.breed}, {pet.age} years old)")
else:
    st.info("No pets added yet.")

st.markdown("### Tasks")
st.caption("Add tasks to your pets. Tasks will be scheduled based on priority and time constraints.")

# Only show task form if there are pets
if st.session_state.owner.get_pets():
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
    with col2:
        duration_hours = st.number_input("Duration (hours)", min_value=0.1, max_value=8.0, value=0.5, step=0.1)
    with col3:
        priority = st.selectbox("Priority", [1, 2, 3, 4, 5], index=4, help="1=low, 5=high")
    with col4:
        selected_pet = st.selectbox("Pet", [pet.name for pet in st.session_state.owner.get_pets()])

    if st.button("Add task"):
        # Find the selected pet
        pet = next((p for p in st.session_state.owner.get_pets() if p.name == selected_pet), None)
        if pet:
            new_task = Task(
                name=task_title,
                description=f"{task_title} for {pet.name}",
                duration_hours=duration_hours,
                priority=priority
            )
            pet.add_task(new_task)
            st.success(f"Added task '{task_title}' to {pet.name}")
            st.rerun()

    # Display current tasks across all pets
    all_tasks = st.session_state.owner.get_all_tasks()
    if all_tasks:
        st.write("Current tasks:")
        task_data = []
        for task in all_tasks:
            pet_name = "Unknown"
            for pet in st.session_state.owner.get_pets():
                if pet.id == task.pet_id:
                    pet_name = pet.name
                    break
            task_data.append({
                "Task": task.name,
                "Pet": pet_name,
                "Duration": f"{task.duration_hours}h",
                "Priority": task.priority,
                "Status": "Completed" if task.completed else "Pending"
            })
        st.table(task_data)
    else:
        st.info("No tasks yet. Add one above.")
else:
    st.warning("Please add a pet first before adding tasks.")

st.divider()

st.subheader("Build Schedule")
st.caption("Generate a daily schedule based on your tasks and available time.")

col1, col2 = st.columns(2)
with col1:
    available_hours = st.number_input(
        "Available hours per day",
        min_value=1.0,
        max_value=24.0,
        value=st.session_state.owner.available_hours_per_day,
        step=0.5
    )
with col2:
    if st.button("Update Hours"):
        st.session_state.owner.available_hours_per_day = available_hours
        st.success(f"Updated available hours to {available_hours}")
        st.rerun()

if st.button("Generate schedule", type="primary"):
    if not st.session_state.owner.get_pets():
        st.error("Please add at least one pet first.")
    elif not st.session_state.owner.get_pending_tasks():
        st.warning("No pending tasks to schedule. Add some tasks first.")
    else:
        # Generate the schedule
        schedule = st.session_state.scheduler.generate_schedule()

        if schedule:
            st.success(f"Generated schedule with {len(schedule)} tasks!")

            # Display the schedule
            st.subheader("📅 Today's Schedule")

            for scheduled_task in schedule:
                task = scheduled_task.task
                pet_name = "Unknown"
                # Find which pet this task belongs to
                for pet in st.session_state.owner.get_pets():
                    if pet.id == task.pet_id:
                        pet_name = pet.name
                        break

                with st.expander(f"🕐 {scheduled_task.scheduled_time.strftime('%H:%M')} - {task.name}", expanded=True):
                    st.write(f"**Pet:** {pet_name}")
                    st.write(f"**Duration:** {task.duration_hours} hours")
                    st.write(f"**Priority:** {task.priority}")
                    st.write(f"**Description:** {task.description}")

            # Show schedule explanation
            with st.expander("💡 Schedule Explanation"):
                explanation = st.session_state.scheduler.get_schedule_explanation()
                st.write(explanation)

            # Validate schedule
            is_valid = st.session_state.scheduler.validate_schedule()
            if is_valid:
                st.info("✅ Schedule fits within your available time.")
            else:
                st.warning("⚠️ Schedule exceeds your available time. Consider adjusting priorities or available hours.")

        else:
            st.info("No tasks were scheduled. All tasks may be completed or there may be time constraints.")
