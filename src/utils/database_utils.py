# database_utils.py
from datetime import datetime
from utils.config import create_db_connection
from evaluation_utils.evaluate import format_duration
from utils.learning_themes import LEARNING_THEMES

def log_conversation_to_db(username, prompt, response, start_time, end_time, interaction_count, language, theme):
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
                INSERT INTO conversations (username, prompt, response, created_at, start_time, end_time, interaction_count, duration, language, theme)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (username, prompt, response, datetime.now(), start_time, end_time, interaction_count, duration, language, theme)
            )
            conn.commit()
    except Exception as e:
        print(f"Error logging conversation: {e}")
    finally:
        conn.close()

def fetch_progress_data(username, sort_order='asc', language_filter='all', theme_filter='all'):
    try:
        conn = create_db_connection()
        with conn.cursor() as cursor:
            order_direction = 'ASC' if sort_order == 'asc' else 'DESC'
            
            query = """
                SELECT created_at, language, theme, duration, interaction_count, evaluation 
                FROM conversations 
                WHERE username = %s AND evaluation IS NOT NULL AND theme IS NOT NULL AND language IS NOT NULL
            """
            params = [username]

            if language_filter != 'all':
                query += " AND language = %s"
                params.append(language_filter)

            if theme_filter != 'all':
                query += " AND theme = %s"
                params.append(theme_filter)

            query += f" ORDER BY created_at {order_direction}"

            cursor.execute(query, params)
            progress = cursor.fetchall()
            if not progress:
                print(f"No progress data available for username: {username}")
                return []
            result = []
            for row in progress:
                created_at = row[0] 
                language = row[1]
                theme = row[2]
                duration = row[3]  
                formatted_duration = format_duration(duration) 
                result.append({
                    'date': created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'language': language,
                    'theme': theme,
                    'duration': formatted_duration, 
                    'interaction_count': row[4],
                    'evaluation': row[5]
                })
            return result
    except Exception as e:
        print(f"Error fetching progress data: {e}")
        return None
    finally:
        if conn:
            conn.close()