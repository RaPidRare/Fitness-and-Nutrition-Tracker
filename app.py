# app.py
import getpass
import hashlib
import json
from datetime import date, timedelta

import psycopg2
from psycopg2.extras import DictCursor

DB_NAME = "fitness_tracker"
DB_USER = "postgres"   # change to match run.sh
DB_PASSWORD = ""       # fill in if needed
DB_HOST = "localhost"
DB_PORT = "5432"


def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )


# ------------- AUTH HELPERS ---------------------------------------------------

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def register():
    print("\n=== Register ===")
    name = input("Name: ").strip()
    email = input("Email: ").strip()
    password = getpass.getpass("Password: ")

    with get_connection() as conn, conn.cursor(cursor_factory=DictCursor) as cur:
        # Create user row
        cur.execute(
            "INSERT INTO users (name) VALUES (%s) RETURNING id;",
            (name,),
        )
        user_id = cur.fetchone()["id"]

        # Create profile row
        cur.execute(
            """
            INSERT INTO user_profiles (user_id, email, password_hash)
            VALUES (%s, %s, %s);
            """,
            (user_id, email, hash_password(password)),
        )
        conn.commit()

    print(f"Registered successfully. Your user id is {user_id}.\n")


def login():
    print("\n=== Login ===")
    email = input("Email: ").strip()
    password = getpass.getpass("Password: ")
    pw_hash = hash_password(password)

    with get_connection() as conn, conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(
            """
            SELECT u.id, u.name
            FROM user_profiles up
            JOIN users u ON u.id = up.user_id
            WHERE up.email = %s AND up.password_hash = %s;
            """,
            (email, pw_hash),
        )
        row = cur.fetchone()

    if row:
        print(f"Welcome, {row['name']}!\n")
        return row["id"], row["name"]
    else:
        print("Invalid email or password.\n")
        return None, None


# ------------- WORKOUT FUNCTIONS ---------------------------------------------

def add_workout(user_id: int):
    print("\n=== Add Workout ===")
    workout_type = input("Workout type (e.g., 'Upper body'): ")
    duration_min = float(input("Duration (minutes): ") or 0)
    intensity = input("Intensity (e.g., 'Light/Moderate/Hard'): ")
    calories_burned = float(input("Calories burned: ") or 0)
    workout_date_str = input("Workout date (YYYY-MM-DD, blank = today): ").strip()
    workout_date = workout_date_str or date.today().isoformat()

    with get_connection() as conn, conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(
            """
            INSERT INTO workout_logs
            (user_id, workout_type, duration_min, intensity, calories_burned, workout_date)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (
                user_id,
                workout_type,
                duration_min,
                intensity,
                calories_burned,
                workout_date,
            ),
        )
        workout_id = cur.fetchone()["id"]
        conn.commit()

    print(f"Workout created with id {workout_id}.\n")


def add_exercise_to_workout():
    print("\n=== Add Exercise To Workout ===")
    workout_id = int(input("Workout id: "))

    with get_connection() as conn, conn.cursor(cursor_factory=DictCursor) as cur:
        # Show existing exercises for convenience
        cur.execute("SELECT id, exercise_name FROM exercises ORDER BY id LIMIT 20;")
        rows = cur.fetchall()
        if rows:
            print("Existing exercises:")
            for r in rows:
                print(f"  {r['id']}: {r['exercise_name']}")
        else:
            print("No exercises found. You may want to insert some into 'exercises' first.")

        exercise_id = int(input("Exercise id: "))
        sets = int(input("Sets: ") or 0)
        reps = int(input("Reps: ") or 0)
        weight_used = float(input("Weight used (kg): ") or 0)

        cur.execute(
            """
            INSERT INTO workout_exercises (workout_id, exercise_id, sets, reps, weight_used_kg)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (workout_id, exercise_id)
            DO UPDATE SET sets = EXCLUDED.sets,
            reps = EXCLUDED.reps,
            weight_used_kg = EXCLUDED.weight_used_kg;
            """,
            (workout_id, exercise_id, sets, reps, weight_used),
        )
        conn.commit()

    print("Exercise added to workout.\n")


# ------------- MEAL / FOOD FUNCTIONS ----------------------------------------

def add_meal(user_id: int):
    print("\n=== Add Meal ===")
    meal_type = input("Meal type (Breakfast/Lunch/etc.): ")
    meal_date_str = input("Meal date (YYYY-MM-DD, blank = today): ").strip()
    meal_date = meal_date_str or date.today().isoformat()

    # Start with null calories/macros, we’ll compute later from meal_foods
    with get_connection() as conn, conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(
            """
            INSERT INTO meal_logs (user_id, meal_type, meal_date)
            VALUES (%s, %s, %s)
            RETURNING id;
            """,
            (user_id, meal_type, meal_date),
        )
        meal_id = cur.fetchone()["id"]
        conn.commit()

    print(f"Meal created with id {meal_id}.\n")


def add_food_to_meal():
    print("\n=== Add Food To Meal ===")
    meal_id = int(input("Meal id: "))

    with get_connection() as conn, conn.cursor(cursor_factory=DictCursor) as cur:
        # Show some foods
        cur.execute("SELECT id, food_name FROM foods ORDER BY id LIMIT 20;")
        foods = cur.fetchall()
        if foods:
            print("Existing foods:")
            for f in foods:
                print(f"  {f['id']}: {f['food_name']}")
        else:
            print("No foods found. Insert into 'foods' first.")

        food_id = int(input("Food id: "))
        quantity = float(input("Quantity (servings): ") or 1.0)

        cur.execute(
            """
            INSERT INTO meal_foods (meal_id, food_id, quantity)
            VALUES (%s, %s, %s)
            ON CONFLICT (meal_id, food_id)
            DO UPDATE SET quantity = EXCLUDED.quantity;
            """,
            (meal_id, food_id, quantity),
        )

        # Recalculate aggregated calories/macros for the meal
        cur.execute(
            """
            UPDATE meal_logs ml
            SET calories  = sub.total_cal,
                protein_g = sub.total_protein,
                carbs_g   = sub.total_carbs,
                fats_g    = sub.total_fats
            FROM (
                SELECT mf.meal_id,
                       SUM(f.calories_per_serv * mf.quantity) AS total_cal,
                       SUM(f.protein_g * mf.quantity)        AS total_protein,
                       SUM(f.carbs_g * mf.quantity)          AS total_carbs,
                       SUM(f.fats_g * mf.quantity)           AS total_fats
                FROM meal_foods mf
                JOIN foods f ON f.id = mf.food_id
                WHERE mf.meal_id = %s
                GROUP BY mf.meal_id
            ) sub
            WHERE ml.id = sub.meal_id;
            """,
            (meal_id,),
        )

        # optional warning
        cur.execute(
            "SELECT calories FROM meal_logs WHERE id = %s;",
            (meal_id,),
        )
        cals = cur.fetchone()[0] or 0
        conn.commit()

    print("Food added.")
    if cals > 1200:  # example threshold
        print(f"Warning: this meal is high in calories ({cals:.0f} kcal).\n")
    else:
        print("")


# ------------- REPORTS & EXPORT ---------------------------------------------

def daily_report(user_id: int):
    print("\n=== Daily Report ===")
    date_str = input("Date (YYYY-MM-DD, blank = today): ").strip()
    day = date_str or date.today().isoformat()

    with get_connection() as conn, conn.cursor(cursor_factory=DictCursor) as cur:
        # calories in
        cur.execute(
            """
            SELECT COALESCE(SUM(calories), 0)
            FROM meal_logs
            WHERE user_id = %s AND meal_date = %s;
            """,
            (user_id, day),
        )
        calories_in = cur.fetchone()[0]

        # calories out
        cur.execute(
            """
            SELECT COALESCE(SUM(calories_burned), 0)
            FROM workout_logs
            WHERE user_id = %s AND workout_date = %s;
            """,
            (user_id, day),
        )
        calories_out = cur.fetchone()[0]

    balance = calories_in - calories_out
    print(f"Date: {day}")
    print(f"Calories in : {calories_in:.2f}")
    print(f"Calories out: {calories_out:.2f}")
    print(f"Balance     : {balance:.2f} (positive = surplus)\n")


def weekly_report(user_id: int):
    print("\n=== Weekly Report (last 7 days) ===")
    end = date.today()
    start = end - timedelta(days=6)

    with get_connection() as conn, conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(
            """
            SELECT
                AVG(calories)  AS avg_cal,
                AVG(protein_g) AS avg_protein,
                AVG(carbs_g)   AS avg_carbs,
                AVG(fats_g)    AS avg_fats
            FROM meal_logs
            WHERE user_id = %s AND meal_date BETWEEN %s AND %s;
            """,
            (user_id, start, end),
        )
        row = cur.fetchone()

    print(f"From {start} to {end}")
    if row and any(row):
        print(f"Avg calories: {row['avg_cal'] or 0:.2f}")
        print(f"Avg protein : {row['avg_protein'] or 0:.2f} g")
        print(f"Avg carbs   : {row['avg_carbs'] or 0:.2f} g")
        print(f"Avg fats    : {row['avg_fats'] or 0:.2f} g\n")
    else:
        print("No meal data in this range.\n")


def export_data(user_id: int):
    print("\n=== Export Data ===")
    with get_connection() as conn, conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(
            "SELECT * FROM workout_logs WHERE user_id = %s ORDER BY workout_date;",
            (user_id,),
        )
        workouts = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """
            SELECT wl.*, we.exercise_id, we.sets, we.reps, we.weight_used_kg
            FROM workout_logs wl
            LEFT JOIN workout_exercises we ON wl.id = we.workout_id
            WHERE wl.user_id = %s
            ORDER BY wl.workout_date, wl.id;
            """,
            (user_id,),
        )
        workout_exercises = [dict(r) for r in cur.fetchall()]

        cur.execute(
            "SELECT * FROM meal_logs WHERE user_id = %s ORDER BY meal_date;",
            (user_id,),
        )
        meals = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """
            SELECT ml.*, mf.food_id, mf.quantity
            FROM meal_logs ml
            LEFT JOIN meal_foods mf ON ml.id = mf.meal_id
            WHERE ml.user_id = %s
            ORDER BY ml.meal_date, ml.id;
            """,
            (user_id,),
        )
        meal_foods_rows = [dict(r) for r in cur.fetchall()]

    data = {
        "user_id": user_id,
        "workouts": workouts,
        "workout_exercises": workout_exercises,
        "meals": meals,
        "meal_foods": meal_foods_rows,
    }

    filename = f"user_{user_id}_export.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, default=str, indent=2)

    print(f"Data exported to {filename}\n")


# ------------- MENUS ---------------------------------------------------------

def logged_in_menu(user_id: int, name: str):
    while True:
        print(f"=== Main Menu (logged in as {name}) ===")
        print("1) Add workout")
        print("2) Add exercise to workout")
        print("3) Add meal")
        print("4) Add food to meal")
        print("5) Daily report")
        print("6) Weekly report (7 days)")
        print("7) Export all data as JSON")
        print("0) Log out")
        choice = input("Choose: ").strip()

        if choice == "1":
            add_workout(user_id)
        elif choice == "2":
            add_exercise_to_workout()
        elif choice == "3":
            add_meal(user_id)
        elif choice == "4":
            add_food_to_meal()
        elif choice == "5":
            daily_report(user_id)
        elif choice == "6":
            weekly_report(user_id)
        elif choice == "7":
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
