from datetime import datetime
import random
import re
from utils.database_utils import log_conversation_to_db
from cli_interface.evaluate import evaluate_last_conversation, get_last_conversation, format_duration
from utils.learning_themes import LEARNING_THEMES
from utils.config import initialize_groq_client, Config

client = initialize_groq_client()
MODEL = Config.MODEL

def get_groq_response(conversation_history):
    """Call the Groq LLM API."""
    try:
        chat_completion = client.chat.completions.create(
            messages=conversation_history,
            model=MODEL,
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

def initialize_conversation(language):
    welcome_prompt = f"Generate a welcoming message for a language learning chatbot just in {language}. Reply in 50 words or less."
    welcome_message = get_groq_response([{"role": "user", "content": welcome_prompt}])
    return {
        'history': [{'role': 'assistant', 'content': welcome_message.strip()}],
        'start_time': datetime.now(),
        'interaction_count': 0,
        'logging_enabled': True,
        'language': language
    }

def restart_conversation_logic(conversations, username, language):
    if username in conversations:
        del conversations[username]
    return initialize_conversation(language)

def process_user_message(conversations, client, model, username, user_message):
    try:
        language = conversations[username]['language'].lower()
        conversations[username]['history'].append({'role': 'user', 'content': user_message})
        conversations[username]['interaction_count'] += 1

        history = [{"role": "system", "content": f"You are a language coach. Reply in 50 words or less in {language}."}]
        history += conversations[username]['history']
        chat_completion = client.chat.completions.create(messages=history, model=model)
        response = chat_completion.choices[0].message.content.strip()
        response = re.sub(r'\(.*?\)', '', response).strip()
        conversations[username]['history'].append({'role': 'assistant', 'content': response})

        if conversations[username]['interaction_count'] == 1:
            response += "\n" + initialize_first_topic(conversations, username, language)
        elif conversations[username]['interaction_count'] == 3:
            response += "\n" + suggest_random_theme(conversations, username, language)

        log_conversation_to_db(username, user_message, response, conversations[username]['start_time'], datetime.now(), conversations[username]['interaction_count'])
        return response
    except Exception as e:
        return {'error': str(e)}

def initialize_first_topic(conversations, username, language):
    prompt = f"What would you like to talk about just in {language}? Reply in 50 words or less."
    response = get_groq_response([{"role": "user", "content": prompt}])
    conversations[username]['history'].append({'role': 'assistant', 'content': response.strip()})
    return response.strip()

def suggest_random_theme(conversations, username, language):
    random_theme = random.choice(list(LEARNING_THEMES.keys()))
    prompt = f"Let's discuss {random_theme} in {language}. Reply in 50 words or less."
    response = get_groq_response([{"role": "user", "content": prompt}])
    conversations[username]['history'].append({'role': 'assistant', 'content': response.strip()})
    return response.strip()

def log_end_conversation(conversations, username):
    start_time = conversations[username]['start_time']
    end_time = datetime.now()
    interaction_count = conversations[username]['interaction_count']
    language = conversations[username]['language']
    duration = end_time - start_time

    log_conversation_to_db(username, '', '', start_time, end_time, interaction_count)
    evaluation, _, _ = evaluate_last_conversation(username, language)
    del conversations[username]
    return {
        'interaction_count': interaction_count,
        'total_duration': format_duration(duration),
        'evaluation': evaluation
    }

def evaluate_conversation(conversations, username):
    conversation_history, _, _ = get_last_conversation(username)
    if not conversation_history:
        return {'error': 'No conversation history available for evaluation.'}
    language = conversations[username]['language']
    return evaluate_last_conversation(conversation_history, language)
