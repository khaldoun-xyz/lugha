import argparse
import os
import psycopg2
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
from chat import create_db_connection

# Load environment variables
load_dotenv()
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PW = os.getenv("POSTGRES_PW")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("MODEL")

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)

def get_last_conversation(username):
    conn = None
    last_conversation = []
    interaction_count = 0
    duration = None
    start_time = None
    end_time = None

    try:
        conn = psycopg2.connect(
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PW,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
        )
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT start_time, end_time 
                FROM conversations 
                WHERE username = %s 
                AND start_time IS NOT NULL 
                AND end_time IS NOT NULL 
                ORDER BY created_at DESC 
                LIMIT 1
                """, 
                (username,)
            )
            session_times = cursor.fetchone()

            if session_times:
                start_time, end_time = session_times
                cursor.execute(
                    """
                    SELECT prompt, response, interaction_count 
                    FROM conversations WHERE username = %s 
                    AND start_time >= %s 
                    AND end_time <= %s 
                    ORDER BY created_at ASC
                    """, 
                    (username, start_time, end_time)
                )
                results = cursor.fetchall()
                
                if results:
                    for row in results:
                        prompt, response, interaction_count = row
                        last_conversation.append(f"You: {prompt}\nGroq LLM: {response}\n")
                    
                    if start_time and end_time:
                        duration = end_time - start_time
                    else:
                        print(f"Start time or end time is missing for user: {username}")
                else:
                    print(f"No conversations found for the last evaluation session of username: {username}")
            else:
                print(f"No evaluation sessions found for username: {username}")

    except Exception as e:
        print(f"Error retrieving last conversation: {e}")
    finally:
        if conn:
            conn.close()
    
    return "\n".join(last_conversation), interaction_count, duration

def log_evaluation_to_db(username, evaluation, start_time, end_time):
    conn = create_db_connection()
    if conn is None:
        print("Could not connect to database.")
        return
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE conversations 
                SET evaluation = %s 
                WHERE username = %s AND start_time = %s AND end_time = %s
                """,
                (evaluation, username, start_time, end_time)
            )
            conn.commit()
    except Exception as e:
        print(f"Error logging evaluation: {e}")
    finally:
        conn.close()

def evaluate_last_conversation(username, language):
    last_conversation, interaction_count, duration = get_last_conversation(username)

    if duration is None:
        print(f"No valid duration found for user: {username}.")
        return "No valid duration found.", interaction_count, duration

    formatted_duration = format_duration(duration)

    prompt = (
        f"Based on the following conversation history, rate the {language} proficiency of the user on a scale from 0 to 100 and only consider the messages in that language, "
        "mentioning their strong and weak points:\n\n"
        f"{last_conversation}\n\n"
    )

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are an expert language evaluator."},
                {"role": "user", "content": prompt},
            ],
            model=MODEL,
        )
        response = chat_completion.choices[0].message.content
        
        # Log the evaluation to the database
        if last_conversation:
            start_time, end_time = get_last_conversation_times(username)
            log_evaluation_to_db(username, response.strip(), start_time, end_time)
        
        return response.strip(), interaction_count, formatted_duration
    except Exception as e:
        return f"Error during LLM evaluation: {e}", interaction_count, duration

def get_last_conversation_times(username):
    conn = None
    start_time = None
    end_time = None

    try:
        conn = psycopg2.connect(
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PW,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
        )
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT start_time, end_time 
                FROM conversations 
                WHERE username = %s 
                AND start_time IS NOT NULL 
                AND end_time IS NOT NULL 
                ORDER BY created_at DESC 
                LIMIT 1
                """, 
                (username,)
            )
            session_times = cursor.fetchone()
            if session_times:
                start_time, end_time = session_times
    except Exception as e:
        print(f"Error retrieving last conversation times: {e}")
    finally:
        if conn:
            conn.close()
    
    return start_time, end_time

def format_duration(duration):
    if duration is None:
        return "Duration data not available."
    
    total_seconds = int(duration.total_seconds())
    
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return f"{hours:02}:{minutes:02}:{seconds:02}" if hours > 0 else f"{minutes:02}:{seconds:02}" if minutes > 0 else f"{seconds}s"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evaluate a user's language proficiency based on the last conversation."
    )
    parser.add_argument("-u", "--username", required=True, help="Username to evaluate ")
    parser.add_argument(
        "-l",
        "--language",
        required=True,
        help="Language to evaluate (e.g., English, French, German)",
    )

    args = parser.parse_args()
    username = args.username
    language = args.language

    evaluation, interaction_count, duration = evaluate_last_conversation(username, language)

    print(f"You have interacted with the LLM {interaction_count} times.")
    print(f"Duration of the last conversation: {duration}")
    print(f"Your evaluation result: {evaluation}")