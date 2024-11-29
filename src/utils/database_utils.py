from datetime import datetime
from utils.config import create_db_connection
from cli_interface.evaluate import format_duration
from utils.learning_themes import LEARNING_THEMES

def log_conversation_to_db(username, prompt, response, start_time, end_time, interaction_count):
    if start_time is None or end_time is None:
        print(f"Start time or end time is None for user: {username}. Cannot log conversation.")
        return

    duration = end_time - start_time
    conn = create_db_connection()
    if conn is None:
        return

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO conversations (username, prompt, response, created_at, start_time, end_time, interaction_count, duration)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (username, prompt, response, datetime.now(), start_time, end_time, interaction_count, duration)
            )
            conn.commit()
    except Exception as e:
        print(f"Error logging conversation: {e}")
    finally:
        conn.close()

def fetch_user_progress(username):
    try:
        conn = create_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT duration, interaction_count, evaluation FROM conversations WHERE username = %s AND evaluation IS NOT NULL", (username,))
            progress = cursor.fetchall()
            result = []
            for row in progress:
                result.append({
                    'duration': format_duration(row[0]),
                    'interaction_count': row[1],
                    'evaluation': row[2]
                })
        return result
    except Exception as e:
        return {'error': f"Failed to fetch progress data: {str(e)}"}
    finally:
        conn.close()