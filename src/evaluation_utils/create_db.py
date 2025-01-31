# create_db.py
from utils.config import create_db_connection

create_tables_query = """
CREATE TABLE IF NOT EXISTS Conversations_parameters (
    conversation_id SERIAL PRIMARY KEY,
    user_name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    language VARCHAR(50),
    theme VARCHAR(50),
    start_time TIMESTAMPTZ NOT NULL,
    user_prompt TEXT NOT NULL,
    bot_messages TEXT NOT NULL,
    end_time TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS Conversations_evaluations (
    conversation_id INT PRIMARY KEY REFERENCES Conversations_parameters(conversation_id),
    evaluation TEXT,
    end_time TIMESTAMPTZ NOT NULL
    duration INTERVAL NOT NULL,
    interaction_count INTEGER NOT NULL
);
"""


def migrate_data():
    conn = create_db_connection()
    if conn is None:
        return
    try:
        with conn.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO Conversations_parameters (
                    user_name, created_at, language, theme, start_time, user_prompt, bot_messages, end_time
                )
                SELECT
                    username, created_at, language, theme, start_time, prompt, response, end_time
                FROM conversations;
            """
            )

            cursor.execute(
                """
                INSERT INTO Conversations_evaluations (
                    conversation_id, evaluation, duration, interaction_count
                )
                SELECT
                    cp.conversation_id, c.evaluation, c.duration, c.interaction_count
                FROM conversations c
                JOIN Conversations_parameters cp ON c.username = cp.user_name
                    AND c.start_time = cp.start_time
                    AND c.end_time = cp.end_time;
            """
            )

            conn.commit()
            print("Data migration completed successfully.")
    except Exception as e:
        print(f"Error migrating data: {e}")
    finally:
        conn.close()


def create_tables():
    conn = create_db_connection()
    if conn is None:
        return
    try:
        with conn.cursor() as cursor:
            cursor.execute(create_tables_query)
            conn.commit()
    except Exception as e:
        print(f"Error creating tables: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    create_tables()
    migrate_data()
