# app.py
import getpass
import hashlib
import json
from datetime import date, timedelta

import psycopg2
from psycopg2.extras import DictCursor

DB_NAME = "fitness_tracker"
DB_USER = "postgres"   # change to match run.sh
DB_PASSWORD = "saimanish123"       # fill in if needed
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
    age = int(input("Age: ").strip())
    gender = input("Gender: ").strip()
    height_cm = int(input("Height (cm): ").strip())
    weight_kg = int(input("Weight (kg): ").strip()) 
    bmi = weight_kg / height_cm / height_cm * 10000

    with get_connection() as conn, conn.cursor(cursor_factory=DictCursor) as cur:
        # Create user row
        cur.execute(
            "INSERT INTO users (name, age, gender, height_cm, weight_kg, bmi) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;",
            (name, age, gender, height_cm, weight_kg, bmi),
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


def add_exercise_catalog():
    print("\n=== Add Exercise (Catalog) ===")
    name = input("Exercise name: ").strip()
    category = input("Category (optional): ").strip() or None
    muscle_group = input("Muscle group (optional): ").strip() or None
    equipment = input("Equipment (optional): ").strip() or None

    with get_connection() as conn, conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(
            """
            INSERT INTO exercises (exercise_name, category, muscle_group, equipment)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (exercise_name) DO NOTHING
            RETURNING id;
            """,
            (name, category, muscle_group, equipment),
        )
        row = cur.fetchone()
        conn.commit()

    if row:
        print(f"Exercise added with id {row['id']}.\n")
    else:
        print("Exercise already exists (by name) or was not added.\n")


def list_exercises():
    print("\n=== Exercises ===")
    with get_connection() as conn, conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(
            """
            SELECT id, exercise_name, category, muscle_group, equipment
            FROM exercises
            ORDER BY id;
            """
        )
        rows = cur.fetchall()

    if not rows:
        print("No exercises found.\n")
        return

    for r in rows:
        print(
            f"{r['id']}: {r['exercise_name']} | "
            f"category={r['category'] or '-'} | "
            f"muscle={r['muscle_group'] or '-'} | "
            f"equipment={r['equipment'] or '-'}"
        )
    print("")


def add_exercise_to_workout():
    print("\n=== Add Exercise To Workout ===")
    workout_id = int(input("Workout id: "))

    with get_connection() as conn, conn.cursor(cursor_factory=DictCursor) as cur:
        # Show existing exercises for convenience
        cur.execute("SELECT id, exercise_name FROM exercises ORDER BY id;")
        rows = cur.fetchall()
        if not rows:
            print("No exercises exist yet.")
            print("Use 'Add Exercise (Catalog)' first.\n")
            return

        print("Exercises:")
        for r in rows:
            print(f"  {r['id']}: {r['exercise_name']}")

        exercise_id = int(input("Exercise id: "))
        valid_ids = {r["id"] for r in rows}
        if exercise_id not in valid_ids:
            print("Invalid exercise id.\n")
            return

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


def update_workout(user_id: int):
    print("\n=== Update Workout ===")
    workout_id_in = input("Workout id to update: ").strip()
    if not workout_id_in:
        print("No workout id provided.\n")
        return

    workout_id = int(workout_id_in)

    new_type = input("New workout type (blank = no change): ").strip()
    new_duration = input("New duration minutes (blank = no change): ").strip()
    new_intensity = input("New intensity (blank = no change): ").strip()
    new_calories = input("New calories burned (blank = no change): ").strip()
    new_date = input("New workout date YYYY-MM-DD (blank = no change): ").strip()

    with get_connection() as conn, conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(
            """
            SELECT workout_type, duration_min, intensity, calories_burned, workout_date
            FROM workout_logs
            WHERE id = %s AND user_id = %s;
            """,
            (workout_id, user_id),
        )
        row = cur.fetchone()

        if not row:
            print("Workout not found (or not owned by you).\n")
            return

        workout_type = new_type or row["workout_type"]
        duration_min = float(new_duration) if new_duration else row["duration_min"]
        intensity = new_intensity or row["intensity"]
        calories_burned = float(new_calories) if new_calories else row["calories_burned"]
        workout_date = new_date or row["workout_date"]

        cur.execute(
            """
            UPDATE workout_logs
            SET workout_type = %s,
                duration_min = %s,
                intensity = %s,
                calories_burned = %s,
                workout_date = %s
            WHERE id = %s AND user_id = %s;
            """,
            (workout_type, duration_min, intensity, calories_burned, workout_date, workout_id, user_id),
        )
        conn.commit()

    print("Workout updated successfully.\n")


def delete_workout(user_id: int):
    print("\n=== Delete Workout ===")
    workout_id_in = input("Workout id to delete: ").strip()
    if not workout_id_in:
        print("No workout id provided.\n")
        return

    workout_id = int(workout_id_in)

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM workout_logs WHERE id = %s AND user_id = %s;",
            (workout_id, user_id),
        )
        if not cur.fetchone():
            print("Workout not found (or not owned by you).\n")
            return

        # Explicit child delete (even though CASCADE exists)
        cur.execute("DELETE FROM workout_exercises WHERE workout_id = %s;", (workout_id,))
        cur.execute("DELETE FROM workout_logs WHERE id = %s AND user_id = %s;", (workout_id, user_id))

        conn.commit()

    print("Workout deleted successfully.\n")


def search_workouts(user_id: int):
    print("\n=== Search Workouts ===")
    print("Search by:")
    print("1) Date range")
    print("2) Workout type (partial match)")
    mode = input("Choose (1/2): ").strip()

    with get_connection() as conn, conn.cursor(cursor_factory=DictCursor) as cur:
        if mode == "1":
            start = input("Start date (YYYY-MM-DD): ").strip()
            end = input("End date (YYYY-MM-DD): ").strip()

            cur.execute(
                """
                SELECT wl.id AS workout_id, wl.workout_date, wl.workout_type, wl.duration_min,
                    wl.intensity, wl.calories_burned,
                    e.id AS exercise_id, e.exercise_name,
                    we.sets, we.reps, we.weight_used_kg
                FROM workout_logs wl
                LEFT JOIN workout_exercises we ON we.workout_id = wl.id
                LEFT JOIN exercises e ON e.id = we.exercise_id
                WHERE wl.user_id = %s
                AND wl.workout_date BETWEEN %s AND %s
                ORDER BY wl.workout_date, wl.id;
                """,
                (user_id, start, end),
            )

        elif mode == "2":
            wtype = input("Enter workout type keyword: ").strip()
            cur.execute(
                """
                SELECT wl.id AS workout_id, wl.workout_date, wl.workout_type, wl.duration_min,
                    wl.intensity, wl.calories_burned,
                    e.id AS exercise_id, e.exercise_name,
                    we.sets, we.reps, we.weight_used_kg
                FROM workout_logs wl
                LEFT JOIN workout_exercises we ON we.workout_id = wl.id
                LEFT JOIN exercises e ON e.id = we.exercise_id
                WHERE wl.user_id = %s
                AND COALESCE(wl.workout_type, '') ILIKE %s
                ORDER BY wl.workout_date, wl.id;
                """,
                (user_id, f"%{wtype}%"),
            )
        else:
            print("Invalid choice.\n")
            return

        rows = cur.fetchall()

    if not rows:
        print("No workouts found for that search.\n")
        return

    # Group printing by workout_id
    current = None
    for r in rows:
        if r["workout_id"] != current:
            current = r["workout_id"]
            print(
                f"\nWorkout {r['workout_id']} | {r['workout_date']} | "
                f"type={r['workout_type'] or '-'} | "
                f"duration={r['duration_min'] or 0} | "
                f"intensity={r['intensity'] or '-'} | "
                f"cals={r['calories_burned'] or 0}"
            )

        if r["exercise_id"]:
            print(
                f"  - Exercise {r['exercise_id']}: {r['exercise_name']} | "
                f"sets={r['sets'] or 0} reps={r['reps'] or 0} "
                f"weight_kg={r['weight_used_kg'] or 0}"
            )

    print("")

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


def add_food_catalog():
    print("\n=== Add Food (Catalog) ===")
    name = input("Food name: ").strip()
    serving_size = input("Serving size (optional, e.g., '100g'): ").strip() or None

    calories = float(input("Calories per serving (blank=0): ") or 0)
    protein = float(input("Protein g per serving (blank=0): ") or 0)
    carbs = float(input("Carbs g per serving (blank=0): ") or 0)
    fats = float(input("Fats g per serving (blank=0): ") or 0)

    with get_connection() as conn, conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(
            """
            INSERT INTO foods (food_name, serving_size, calories_per_serv, protein_g, carbs_g, fats_g)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (food_name) DO NOTHING
            RETURNING id;
            """,
            (name, serving_size, calories, protein, carbs, fats),
        )
        row = cur.fetchone()
        conn.commit()

    if row:
        print(f"Food added with id {row['id']}.\n")
    else:
        print("Food already exists (by name) or was not added.\n")


def list_foods():
    print("\n=== Foods ===")
    with get_connection() as conn, conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(
            """
            SELECT id, food_name, serving_size, calories_per_serv, protein_g, carbs_g, fats_g
            FROM foods
            ORDER BY id;
            """
        )
        rows = cur.fetchall()

    if not rows:
        print("No foods found.\n")
        return

    for f in rows:
        print(
            f"{f['id']}: {f['food_name']} | "
            f"serving={f['serving_size'] or '-'} | "
            f"cal={f['calories_per_serv'] or 0} | "
            f"P={f['protein_g'] or 0} | "
            f"C={f['carbs_g'] or 0} | "
            f"F={f['fats_g'] or 0}"
        )
    print("")


def add_food_to_meal():
    print("\n=== Add Food To Meal ===")
    meal_id = int(input("Meal id: "))

    with get_connection() as conn, conn.cursor(cursor_factory=DictCursor) as cur:
        # Show some foods
        cur.execute("SELECT id, food_name FROM foods ORDER BY id LIMIT 20;")
        foods = cur.fetchall()
        if not foods:
            print("No foods exist yet.")
            print("Use 'Add Food (Catalog)' first.\n")
            return

        print("Foods:")
        for f in foods:
            print(f"  {f['id']}: {f['food_name']}")

        food_id = int(input("Food id: "))
        valid_ids = {f["id"] for f in foods}
        if food_id not in valid_ids:
            print("Invalid food id.\n")
            return

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

        # Recalculate meal totals
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

        cur.execute("SELECT calories FROM meal_logs WHERE id = %s;", (meal_id,))
        cals = cur.fetchone()[0] or 0

        conn.commit()

    print("Food added.")


def update_meal(user_id: int):
    print("\n=== Update Meal ===")
    meal_id_in = input("Meal id to update: ").strip()
    if not meal_id_in:
        print("No meal id provided.\n")
        return

    meal_id = int(meal_id_in)

    new_type = input("New meal type (blank = no change): ").strip()
    new_date = input("New meal date YYYY-MM-DD (blank = no change): ").strip()

    # Optional manual override (rubric-proof for UPDATE)
    new_cal = input("New total calories (blank = no change): ").strip()
    new_p = input("New protein_g (blank = no change): ").strip()
    new_c = input("New carbs_g (blank = no change): ").strip()
    new_f = input("New fats_g (blank = no change): ").strip()

    with get_connection() as conn, conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(
            """
            SELECT meal_type, meal_date, calories, protein_g, carbs_g, fats_g
            FROM meal_logs
            WHERE id = %s AND user_id = %s;
            """,
            (meal_id, user_id),
        )
        row = cur.fetchone()

        if not row:
            print("Meal not found (or not owned by you).\n")
            return

        meal_type = new_type or row["meal_type"]
        meal_date = new_date or row["meal_date"]

        calories = float(new_cal) if new_cal else row["calories"]
        protein_g = float(new_p) if new_p else row["protein_g"]
        carbs_g = float(new_c) if new_c else row["carbs_g"]
        fats_g = float(new_f) if new_f else row["fats_g"]

        cur.execute(
            """
            UPDATE meal_logs
            SET meal_type = %s,
                meal_date = %s,
                calories = %s,
                protein_g = %s,
                carbs_g = %s,
                fats_g = %s
            WHERE id = %s AND user_id = %s;
            """,
            (meal_type, meal_date, calories, protein_g, carbs_g, fats_g, meal_id, user_id),
        )
        conn.commit()

    print("Meal updated successfully.\n")


def delete_meal(user_id: int):
    print("\n=== Delete Meal ===")
    meal_id_in = input("Meal id to delete: ").strip()
    if not meal_id_in:
        print("No meal id provided.\n")
        return

    meal_id = int(meal_id_in)

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM meal_logs WHERE id = %s AND user_id = %s;",
            (meal_id, user_id),
        )
        if not cur.fetchone():
            print("Meal not found (or not owned by you).\n")
            return

        # Explicit child delete (even though CASCADE exists)
        cur.execute("DELETE FROM meal_foods WHERE meal_id = %s;", (meal_id,))
        cur.execute("DELETE FROM meal_logs WHERE id = %s AND user_id = %s;", (meal_id, user_id))

        conn.commit()

    print("Meal deleted successfully.\n")


def search_meals(user_id: int):
    print("\n=== Search Meals ===")
    print("Search by:")
    print("1) Date (exact)")
    print("2) Food name keyword")
    mode = input("Choose (1/2): ").strip()

    with get_connection() as conn, conn.cursor(cursor_factory=DictCursor) as cur:
        if mode == "1":
            d = input("Meal date (YYYY-MM-DD): ").strip()
            cur.execute(
                """
                SELECT ml.id AS meal_id, ml.meal_date, ml.meal_type,
                       ml.calories, ml.protein_g, ml.carbs_g, ml.fats_g,
                       f.id AS food_id, f.food_name, mf.quantity
                FROM meal_logs ml
                LEFT JOIN meal_foods mf ON mf.meal_id = ml.id
                LEFT JOIN foods f ON f.id = mf.food_id
                WHERE ml.user_id = %s
                  AND ml.meal_date = %s
                ORDER BY ml.meal_date, ml.id;
                """,
                (user_id, d),
            )

        elif mode == "2":
            term = input("Enter part of food name: ").strip()
            cur.execute(
                """
                SELECT ml.id AS meal_id, ml.meal_date, ml.meal_type,
                       ml.calories, ml.protein_g, ml.carbs_g, ml.fats_g,
                       f.id AS food_id, f.food_name, mf.quantity
                FROM meal_logs ml
                JOIN meal_foods mf ON mf.meal_id = ml.id
                JOIN foods f ON f.id = mf.food_id
                WHERE ml.user_id = %s
                  AND f.food_name ILIKE %s
                ORDER BY ml.meal_date, ml.id;
                """,
                (user_id, f"%{term}%"),
            )
        else:
            print("Invalid choice.\n")
            return

        rows = cur.fetchall()

    if not rows:
        print("No meals found for that search.\n")
        return

    current = None
    for r in rows:
        if r["meal_id"] != current:
            current = r["meal_id"]
            print(
                f"\nMeal {r['meal_id']} | {r['meal_date']} | "
                f"type={r['meal_type'] or '-'} | "
                f"cal={r['calories'] or 0} | "
                f"P={r['protein_g'] or 0} C={r['carbs_g'] or 0} F={r['fats_g'] or 0}"
            )

        if r["food_id"]:
            print(f"  - Food {r['food_id']}: {r['food_name']} | qty={r['quantity']}")

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

        # Meals
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

        # Catalog
        elif choice == "11":
            add_exercise_catalog()
        elif choice == "12":
            list_exercises()
        elif choice == "13":
            add_food_catalog()
        elif choice == "14":
            list_foods()

        # Reports/export
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
