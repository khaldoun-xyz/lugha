# migrate_data.py
from utils.config import create_db_connection


def migrate_data():
    conn = create_db_connection()
    if conn is None:
        return
    try:
        with conn.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO conversations_parameters (
                    user_name, created_at, language, theme, start_time, user_prompt, bot_messages
                )
                SELECT
                    username, created_at, language, theme, start_time, prompt, response
                FROM conversations;
            """
            )

            cursor.execute(
                """
                INSERT INTO conversations_evaluations (
                    conversation_id, evaluation, end_time, duration, interaction_count
                )
                SELECT
                    cp.conversation_id, c.evaluation, c.end_time, c.duration, c.interaction_count
                FROM conversations c
                JOIN conversations_parameters cp ON c.username = cp.user_name
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


if __name__ == "__main__":
    migrate_data()
