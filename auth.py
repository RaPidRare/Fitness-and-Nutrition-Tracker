# auth.py
import getpass
import hashlib

from psycopg2.extras import DictCursor

from db import get_connection


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
            "INSERT INTO users (name, age, gender, height_cm, weight_kg, bmi) "
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;",
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
