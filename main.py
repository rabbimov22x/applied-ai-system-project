#!/usr/bin/env python3
"""
Testing script for PawPal+ system classes.
This script demonstrates the core functionality by creating pets, tasks, and generating a schedule.
"""

from pawpal_system import Owner, Pet, Task, Scheduler


def main():
    print("🐾 PawPal+ System Test")
    print("=" * 50)

    # Create an owner
    owner = Owner(name="Alex Johnson", available_hours_per_day=6.0)
    print(f"Created owner: {owner.name} (available: {owner.available_hours_per_day} hours/day)")

    # Create pets
    dog = Pet(name="Buddy", age=3, breed="Golden Retriever")
    dog.add_special_need("Needs daily walks")
    dog.add_special_need("Allergic to chicken")

    cat = Pet(name="Whiskers", age=2, breed="Siamese")
    cat.add_special_need("Needs litter box cleaning")

    # Add pets to owner
    owner.add_pet(dog)
    owner.add_pet(cat)

    print(f"Added pets: {dog.name} ({dog.breed}) and {cat.name} ({cat.breed})")

    # Create tasks for the dog
    dog_walk = Task(
        name="Morning Walk",
        description="30-minute walk in the park",
        duration_hours=0.5,
        priority=5,  # High priority
        frequency="daily"
    )

    dog_feeding = Task(
        name="Breakfast",
        description="Morning meal with kibble",
        duration_hours=0.25,
        priority=4,
        frequency="daily"
    )

    # Create tasks for the cat
    cat_litter = Task(
        name="Litter Box",
        description="Clean and refresh litter box",
        duration_hours=0.5,
        priority=4,
        frequency="daily"
    )

    # Add tasks to pets
    dog.add_task(dog_walk)
    dog.add_task(dog_feeding)
    cat.add_task(cat_litter)

    print(f"Added tasks:")
    print(f"  - {dog_walk.name} for {dog.name} ({dog_walk.duration_hours}h, priority {dog_walk.priority})")
    print(f"  - {dog_feeding.name} for {dog.name} ({dog_feeding.duration_hours}h, priority {dog_feeding.priority})")
    print(f"  - {cat_litter.name} for {cat.name} ({cat_litter.duration_hours}h, priority {cat_litter.priority})")

    # Create scheduler and generate schedule
    scheduler = Scheduler(owner)
    schedule = scheduler.generate_schedule()

    print("\n📅 Today's Schedule")
    print("=" * 50)

    if schedule:
        print(f"Scheduled {len(schedule)} tasks within {owner.available_hours_per_day} available hours:")
        print()

        for scheduled_task in schedule:
            task = scheduled_task.task
            pet_name = "Unknown"
            # Find which pet this task belongs to
            for pet in owner.pets:
                if pet.id == task.pet_id:
                    pet_name = pet.name
                    break

            print(f"🕐 {scheduled_task.scheduled_time.strftime('%H:%M')} - {task.name}")
            print(f"   Pet: {pet_name} | Duration: {task.duration_hours}h | Priority: {task.priority}")
            print(f"   {task.description}")
            print()

        # Show explanation
        print("💡 Schedule Explanation:")
        print(scheduler.get_schedule_explanation())

        # Validate schedule
        is_valid = scheduler.validate_schedule()
        print(f"\n✅ Schedule validation: {'Valid' if is_valid else 'Invalid'}")

    else:
        print("No tasks scheduled. All tasks may be completed or no tasks exist.")

    print("\n" + "=" * 50)
    print("🐾 PawPal+ Test Complete!")


if __name__ == "__main__":
    main()