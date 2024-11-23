# chat.py
import argparse
from datetime import datetime
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from config import Config, create_db_connection, initialize_groq_client
from learning_themes import LEARNING_THEMES
import random



client = initialize_groq_client()
MODEL = Config.MODEL

def log_conversation_to_db(username, prompt, response, start_time, end_time, interaction_count):
    if start_time is None or end_time is None:
        print(f"Start time or end time is None for user: {username}. Cannot log conversation.")
        return

    duration = end_time - start_time
    conn = create_db_connection()
    if conn is None:
        raise Exception("conn is None")

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

def get_groq_response(conversation_history):
    try:
        return groq_llm_api_call(conversation_history).strip()
    except Exception as e:
        return f"Error: {e}"

def groq_llm_api_call(conversation_history):
    """Call the Groq LLM API."""
    chat_completion = client.chat.completions.create(
        messages=conversation_history,
        model=MODEL,
    )
    return chat_completion.choices[0].message.content

def display_learning_themes():
    print("\nAvailable Learning Themes:")
    for category, topics in LEARNING_THEMES.items():
        print(f"\n{category}:")
        for topic in topics:
            print(f"  - {topic}")

def chat_with_groq_llm(username):
    """Main chat loop with Groq LLM."""
    session = PromptSession(history=InMemoryHistory())
    language = input("Please enter your preferred language (e.g., 'fr' for French): ")

    conversation_history = []
    interaction_count = 0
    logging_enabled = False
    start_time = None

    welcome_prompt = f"Generate a welcoming message for a language learning chatbot just in {language}. Reply in 50 words or less."
    welcome_message = get_groq_response([{"role": "user", "content": welcome_prompt}])
    print(f"\033[92mGroq LLM: {welcome_message}\033[0m\n")
    conversation_history.append({'role': 'assistant', 'content': welcome_message})

    print("Type 'exit' to quit, 'start evaluation' to begin logging, 'stop evaluation' to stop logging, or 'learning themes' to explore available learning topics.\n")
    while True:
        try:
            prompt = session.prompt("You: ")
            if prompt.lower() == "exit":
                if logging_enabled:
                    end_time = datetime.now()
                    log_conversation_to_db(username, "Conversation ended.", "Goodbye!", start_time, end_time, interaction_count)
                print("Exiting Groq LLM Chat. Goodbye!")
                break
            elif prompt.lower() == "start evaluation":
                logging_enabled = True
                start_time = datetime.now()
                print("Evaluation logging started.")
                continue
            elif prompt.lower() == "stop evaluation":
                logging_enabled = False
                print("Evaluation logging stopped.")
                continue
            elif prompt.lower() == "learning themes":
                display_learning_themes()
                continue

            conversation_history.append({"role": "user", "content": prompt})
            interaction_count += 1

            if interaction_count == 1:
                start_conversation_prompt = f"Generate a message just in {language} to start a conversation and ask what the user would like to talk about. Reply in 50 words or less."
                start_conversation_message = get_groq_response([{"role": "user", "content": start_conversation_prompt}])
                conversation_history.append({'role': 'assistant', 'content': start_conversation_message})
                print(f"\033[92mGroq LLM: {start_conversation_message}\033[0m\n")
                continue

            if interaction_count == 3:
                themes = list(LEARNING_THEMES.keys())
                random_theme = random.choice(themes)
                theme_prompt = f"Generate a theme proposal just in {language} for discussing {random_theme} and ask if the user has a specific subject in mind. Reply in 50 words or less."
                theme_message = get_groq_response([{"role": "user", "content": theme_prompt}])
                conversation_history.append({'role': 'assistant', 'content': theme_message})
                print(f"\033[92mGroq LLM: {theme_message}\033[0m\n")

            model_history = [
                {"role": "system", "content": f"You are a language coach. Reply in 50 words or less in {language}."},
            ] + conversation_history
            
            response = get_groq_response(model_history)
            print(f"\033[92mGroq LLM: {response}\033[0m\n")

            if logging_enabled:
                log_conversation_to_db(
                    username,
                    prompt,
                    response,
                    start_time,
                    datetime.now(),
                    interaction_count
                )

            conversation_history.append({"role": "assistant", "content": response})

        except (EOFError, KeyboardInterrupt):
            if logging_enabled:
                end_time = datetime.now()
                log_conversation_to_db(username, "Session interrupted.", "Goodbye!", start_time, end_time, interaction_count)
            print("\nExiting Groq LLM Chat. Goodbye!")
            break
if __name__ == "__main__":  
    parser = argparse.ArgumentParser(description="Chat with Groq LLM and log conversations.")  
    parser.add_argument("-u", "--user", required=True, help="Specify the username for logging")  
    args = parser.parse_args()  
    chat_with_groq_llm(args.user)  
