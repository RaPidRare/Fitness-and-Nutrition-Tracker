# reports.py
import json
from datetime import date, timedelta

from psycopg2.extras import DictCursor

from db import get_connection


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
