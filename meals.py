# meals.py
from datetime import date

from psycopg2.extras import DictCursor

from db import get_connection


def add_meal(user_id: int):
    print("\n=== Add Meal ===")
    meal_type = input("Meal type (Breakfast/Lunch/etc.): ")
    meal_date_str = input("Meal date (YYYY-MM-DD, blank = today): ").strip()
    meal_date = meal_date_str or date.today().isoformat()

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
        _ = cur.fetchone()[0] or 0

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
