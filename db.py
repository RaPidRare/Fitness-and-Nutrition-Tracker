# db.py
import psycopg2

DB_NAME = "fitness_tracker"
DB_USER = "postgres" # change if needed
DB_PASSWORD = "" # see report for setup
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
