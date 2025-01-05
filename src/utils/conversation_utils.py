import re

# conversation_utils.py
from datetime import datetime
from typing import Any, Dict, List

from evaluation_utils.evaluate import (
    evaluate_last_conversation,
    format_duration,
    get_last_conversation,
)
from utils.config import Config, initialize_groq_client
from utils.database_utils import log_conversation_to_db

client = initialize_groq_client()
MODEL = Config.MODEL


def clean_response(response: str) -> str:
    response = response.strip(' "\'"')
    response = re.sub(r"\(.*?\)", "", response).strip()
    return response


def get_groq_response(conversation_history: List[Dict[str, str]]) -> str:
    try:
        chat_completion = client.chat.completions.create(
            messages=conversation_history,
            model=MODEL,
        )
        return clean_response(chat_completion.choices[0].message.content)
    except Exception as e:
        return f"Error: {e}"


def create_system_prompt(language: str, username: str, theme: str) -> str:
    return (
        f"As a certified {language} instructor, I will communicate with {username} exclusively in {language}. "
        f"Our conversations will be tailored to a beginner's level, maintaining natural conversational patterns "
        f"while exploring the theme of {theme}. Responses will be limited to 50 words."
    )


def initialize_conversation(language: str, theme: str, username: str) -> Dict[str, Any]:
    welcome_prompt = (
        f"Compose a warm and inviting message to welcome {username} to a relaxed chat "
        f"about {theme}. As a language learning coach, use only {language} to provide "
        f"guidance and encouragement. Limit your response "
        f"to 50 words or less."
    )
    welcome_message = get_groq_response([{"role": "user", "content": welcome_prompt}])

    return {
        "history": [{"role": "assistant", "content": welcome_message}],
        "start_time": datetime.now(),
        "interaction_count": 0,
        "logging_enabled": True,
        "language": language,
        "theme": theme,
        "username": username,
    }


def restart_conversation_logic(
    conversations: Dict[str, Any],
    username: str,
    language: str,
    theme: str,
) -> Dict[str, Any]:
    if username in conversations:
        del conversations[username]
    return initialize_conversation(language, theme, username)


def process_user_message(
    conversations: Dict[str, Any],
    client: Any,
    model: str,
    username: str,
    user_message: str,
) -> str:
    try:
        conversation = conversations[username]
        system_prompt = create_system_prompt(
            conversation["language"].lower(), username, conversation["theme"]
        )

        conversation["history"].append({"role": "user", "content": user_message})
        conversation["interaction_count"] += 1

        history = [{"role": "system", "content": system_prompt}] + conversation[
            "history"
        ]

        chat_completion = client.chat.completions.create(messages=history, model=model)
        response = clean_response(chat_completion.choices[0].message.content)

        conversation["history"].append({"role": "assistant", "content": response})
        log_conversation_to_db(
            username,
            user_message,
            response,
            conversation["start_time"],
            datetime.now(),
            conversation["interaction_count"],
            conversation["language"],
            conversation["theme"],
        )

        return response
    except Exception as e:
        return {"error": str(e)}


def log_end_conversation(
    conversations: Dict[str, Any], username: str
) -> Dict[str, Any]:
    conversation = conversations[username]
    end_time = datetime.now()
    duration = end_time - conversation["start_time"]

    log_conversation_to_db(
        username,
        "",
        "",
        conversation["start_time"],
        end_time,
        conversation["interaction_count"],
        conversation["language"],
        conversation["theme"],
    )

    evaluation, _, _ = evaluate_last_conversation(username, conversation["language"])

    result = {
        "interaction_count": conversation["interaction_count"],
        "total_duration": format_duration(duration),
        "evaluation": evaluation,
        "theme": conversation["theme"],
        "language": conversation["language"],
    }

    del conversations[username]
    return result


def evaluate_conversation(
    conversations: Dict[str, Any], username: str
) -> Dict[str, Any]:
    conversation_history, _, _ = get_last_conversation(username)
    if not conversation_history:
        return {"error": "No conversation history available for evaluation."}

    language = conversations[username]["language"]
    return evaluate_last_conversation(conversation_history, language)
