# app.py
from auth import register, login
from workouts import (
    add_workout,
    add_exercise_to_workout,
    update_workout,
    delete_workout,
    search_workouts,
    add_exercise_catalog,
    list_exercises,
)
from meals import (
    add_meal,
    add_food_to_meal,
    update_meal,
    delete_meal,
    search_meals,
    add_food_catalog,
    list_foods,
)
from reports import daily_report, weekly_report, export_data


def logged_in_menu(user_id: int, name: str):
    while True:
        print(f"=== Main Menu (logged in as {name}) ===")
        print("1) Add workout")
        print("2) Add exercise to workout")
        print("3) Update workout")
        print("4) Delete workout")
        print("5) Search workouts")
        print("")
        print("6) Add meal")
        print("7) Add food to meal")
        print("8) Update meal")
        print("9) Delete meal")
        print("10) Search meals")
        print("")
        print("11) Add exercise (catalog)")
        print("12) List exercises")
        print("13) Add food (catalog)")
        print("14) List foods")
        print("")
        print("15) Daily report")
        print("16) Weekly report")
        print("17) Export all data as JSON")
        print("0) Logout")

        choice = input("Choose: ").strip()

        if choice == "1":
            add_workout(user_id)
        elif choice == "2":
            add_exercise_to_workout()
        elif choice == "3":
            update_workout(user_id)
        elif choice == "4":
            delete_workout(user_id)
        elif choice == "5":
            search_workouts(user_id)

        elif choice == "6":
            add_meal(user_id)
        elif choice == "7":
            add_food_to_meal()
        elif choice == "8":
            update_meal(user_id)
        elif choice == "9":
            delete_meal(user_id)
        elif choice == "10":
            search_meals(user_id)

        elif choice == "11":
            add_exercise_catalog()
        elif choice == "12":
            list_exercises()
        elif choice == "13":
            add_food_catalog()
        elif choice == "14":
            list_foods()

        elif choice == "15":
            daily_report(user_id)
        elif choice == "16":
            weekly_report(user_id)
        elif choice == "17":
            export_data(user_id)

        elif choice == "0":
            print("Logging out.\n")
            break
        else:
            print("Invalid choice.\n")


def main():
    while True:
        print("=== Fitness & Nutrition Logger ===")
        print("1) Register")
        print("2) Login")
        print("0) Quit")
        choice = input("Choose: ").strip()

        if choice == "1":
            register()
        elif choice == "2":
            user_id, name = login()
            if user_id:
                logged_in_menu(user_id, name)
        elif choice == "0":
            print("Goodbye!")
            break
        else:
            print("Invalid choice.\n")


if __name__ == "__main__":
    main()
