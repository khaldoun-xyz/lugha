#evaluate.py
import argparse
from utils.config import Config, create_db_connection, initialize_groq_client
client = initialize_groq_client()
MODEL = Config.MODEL


def fetch_last_conversation_times(username):
    """Fetch the start and end times of the last conversation."""
    query = """ 
        SELECT start_time, end_time 
        FROM conversations 
        WHERE username = %s 
        AND start_time IS NOT NULL 
        AND end_time IS NOT NULL 
        ORDER BY created_at DESC 
        LIMIT 1
    """
    with create_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (username,))
            return cursor.fetchone()

def fetch_last_conversation(username, start_time, end_time):
    """Fetch the last conversation details based on the times."""
    query = """
        SELECT prompt, response, interaction_count 
        FROM conversations 
        WHERE username = %s 
        AND start_time >= %s 
        AND end_time <= %s 
        ORDER BY created_at ASC
    """
    with create_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (username, start_time, end_time))
            return cursor.fetchall()

def get_last_conversation(username):
    """Get the last conversation details for a user."""
    session_times = fetch_last_conversation_times(username)
    
    if session_times:
        start_time, end_time = session_times
        results = fetch_last_conversation(username, start_time, end_time)
        
        last_conversation = [
            f"You: {prompt}\nGroq LLM: {response}\n" for prompt, response, _ in results
        ]
        
        duration = end_time - start_time if start_time and end_time else None
        interaction_count = results[-1][2] if results else 0
        
        return "\n".join(last_conversation), interaction_count, duration

    print(f"No evaluation sessions found for username: {username}")
    return [], 0, None

def log_evaluation_to_db(username, evaluation, start_time, end_time):
    """Log the evaluation result into the database."""
    conn = create_db_connection()
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

def format_duration(duration):
    """Format the duration into a human-readable string."""
    if duration is None:
        return "Duration data not available."
    
    total_seconds = int(duration.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return f"{hours:02}:{minutes:02}:{seconds:02}" if hours > 0 else f"{minutes:02}:{seconds:02}" if minutes > 0 else f"{seconds}s"

def evaluate_last_conversation(username, language):
    """Evaluate the last conversation for a user."""
    last_conversation, interaction_count, duration = get_last_conversation(username)

    if duration is None:
        print(f"No valid duration found for user: {username}.")
        return "No valid duration found.", interaction_count, duration

    formatted_duration = format_duration(duration)

    prompt = (
        f"Based on the following conversation history, please provide the following metrics for the user's {language} proficiency:\n"
        "Rate overall score (%), Grammar proficiency (%), Vocabulary usage (%), Communication clarity (%), Logical reasoning (%)\n\n"
        "Additionally, mention the user's strengths and weaknesses and provide advice for improvement.\n\n"
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
        response = chat_completion.choices[0].message.content.strip()
        
        # Log the evaluation to the database
        if last_conversation:
            start_time, end_time = fetch_last_conversation_times(username)
            log_evaluation_to_db(username, response, start_time, end_time)
        
        return response, interaction_count, formatted_duration
    except Exception as e:
        return f"Error during LLM evaluation: {e}", interaction_count, duration