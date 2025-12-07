-- schema.sql
-- Fitness & Nutrition Logger schema (PostgreSQL)

DROP TABLE IF EXISTS meal_foods CASCADE;
DROP TABLE IF EXISTS meal_logs CASCADE;
DROP TABLE IF EXISTS foods CASCADE;
DROP TABLE IF EXISTS workout_exercises CASCADE;
DROP TABLE IF EXISTS workout_logs CASCADE;
DROP TABLE IF EXISTS exercises CASCADE;
DROP TABLE IF EXISTS user_profiles CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- USERS ------------------------------------------------------------

CREATE TABLE users (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR(120) NOT NULL,
    age         SMALLINT CHECK (age BETWEEN 5 AND 120),
    gender      VARCHAR(20),
    height_cm   DECIMAL(5,2),
    weight_kg   DECIMAL(6,2),
    bmi         DECIMAL(5,2),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_profiles (
    user_id       BIGINT PRIMARY KEY,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(100) NOT NULL,
    date_joined   DATE DEFAULT CURRENT_DATE,
    CONSTRAINT fk_user_profiles_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
);

-- EXERCISES --------------------------------------------------------

CREATE TABLE exercises (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    exercise_name VARCHAR(120) NOT NULL UNIQUE,
    category      VARCHAR(60),
    muscle_group  VARCHAR(60),
    equipment     VARCHAR(80)
);

-- WORKOUT LOGGING --------------------------------------------------

CREATE TABLE workout_logs (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         BIGINT NOT NULL,
    workout_type    VARCHAR(60),
    duration_min    DECIMAL(5,2) CHECK (duration_min >= 0),
    intensity       VARCHAR(30),
    calories_burned DECIMAL(7,2) CHECK (calories_burned >= 0),
    workout_date    DATE DEFAULT CURRENT_DATE,
    CONSTRAINT fk_workout_logs_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE TABLE workout_exercises (
    workout_id    BIGINT NOT NULL,
    exercise_id   BIGINT NOT NULL,
    sets          SMALLINT CHECK (sets >= 0),
    reps          SMALLINT CHECK (reps >= 0),
    weight_used_kg DECIMAL(6,2) CHECK (weight_used_kg >= 0),
    PRIMARY KEY (workout_id, exercise_id),
    CONSTRAINT fk_we_workout
        FOREIGN KEY (workout_id) REFERENCES workout_logs(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_we_exercise
        FOREIGN KEY (exercise_id) REFERENCES exercises(id)
        ON DELETE RESTRICT
);

-- FOODS & MEALS ----------------------------------------------------

CREATE TABLE foods (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    food_name        VARCHAR(160) NOT NULL UNIQUE,
    serving_size     VARCHAR(60),
    calories_per_serv DECIMAL(7,2) CHECK (calories_per_serv >= 0),
    protein_g        DECIMAL(6,2) CHECK (protein_g >= 0),
    carbs_g          DECIMAL(6,2) CHECK (carbs_g >= 0),
    fats_g           DECIMAL(6,2) CHECK (fats_g >= 0)
);

CREATE TABLE meal_logs (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id    BIGINT NOT NULL,
    meal_type  VARCHAR(40),
    calories   DECIMAL(7,2),
    protein_g  DECIMAL(6,2),
    carbs_g    DECIMAL(6,2),
    fats_g     DECIMAL(6,2),
    meal_date  DATE DEFAULT CURRENT_DATE,
    CONSTRAINT fk_meal_logs_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE TABLE meal_foods (
    meal_id  BIGINT NOT NULL,
    food_id  BIGINT NOT NULL,
    quantity DECIMAL(8,3) DEFAULT 1 CHECK (quantity > 0),
    PRIMARY KEY (meal_id, food_id),
    CONSTRAINT fk_mf_meal
        FOREIGN KEY (meal_id) REFERENCES meal_logs(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_mf_food
        FOREIGN KEY (food_id) REFERENCES foods(id)
        ON DELETE RESTRICT
);
