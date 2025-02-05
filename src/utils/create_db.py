# create_db.py
from utils.config import create_db_connection

CREATE_TABLES_QUERY = """
CREATE TABLE IF NOT EXISTS conversations_parameters (
    conversation_id SERIAL PRIMARY KEY,
    user_name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    language VARCHAR(50),
    theme VARCHAR(50),
    start_time TIMESTAMPTZ NOT NULL,
    user_prompt TEXT NOT NULL,
    bot_messages TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations_evaluations (
    conversation_id INT PRIMARY KEY REFERENCES conversations_parameters(conversation_id),
    evaluation TEXT,
    end_time TIMESTAMPTZ NOT NULL,
    duration INTERVAL NOT NULL,
    interaction_count INTEGER NOT NULL
);
"""


def create_tables():
    conn = create_db_connection()
    if conn is None:
        return
    try:
        with conn.cursor() as cursor:
            cursor.execute(CREATE_TABLES_QUERY)
            conn.commit()
    except Exception as e:
        print(f"Error creating tables: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    create_tables()
