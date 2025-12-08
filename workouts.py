# workouts.py
from datetime import date

from psycopg2.extras import DictCursor

from db import get_connection


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
