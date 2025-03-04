# conversation_utils.py
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from evaluation_utils.evaluate import (
    check_evaluation_criteria,
    evaluate_last_conversation,
    format_duration,
)
from utils.config import Config, initialize_groq_client
from utils.database_utils import (
    log_conversation_to_db,
    log_evaluation_to_db,
    log_message_to_db,
)

CLIENT = initialize_groq_client()
MODEL = Config.MODEL


class ConversationManager:
    def __init__(self):
        pass

    def clean_response(self, response: str) -> str:
        response = response.strip(' "\'"')
        response = re.sub(r"\(.*?\)", "", response).strip()
        return response

    def get_groq_response(self, conversation_history: List[Dict[str, str]]) -> str:
        try:
            chat_completion = CLIENT.chat.completions.create(
                messages=conversation_history,
                model=MODEL,
            )
            return self.clean_response(chat_completion.choices[0].message.content)
        except Exception as e:
            return f"Error: {e}"

    def create_system_prompt(self, language: str, username: str, mode: str) -> str:
        if mode == "learn":
            return (
                f"As a certified {language} instructor, you are required to speak primarily in {language} during our lessons. "
                f"You will translate your sentences into English to ensure {username} understands each phrase. In addition, you will "
                f"correct {username}'s messages, providing explanations when needed to clarify any mistakes. The learning process will "
                f"focus on simple dialogues, with English translations and corrections, ensuring a gradual and beginner-friendly learning experience "
                f"you through each step of the conversation, ensuring clarity and improvement. Responses will be limited to 50 words."
            )
        else:  # mode == "talk"
            return (
                f"As a certified {language} instructor, I will communicate with {username} exclusively in {language}. "
                f"Our conversations will be tailored to a beginner's level, maintaining natural conversational patterns "
                f"Responses will be limited to 50 words."
            )

    def initialize_conversation(
        self, language: str, mode: str, username: str
    ) -> Dict[str, Any]:
        mode = mode.strip()
        if mode == "learn":
            welcome_prompt = (
                f"Create a direct and friendly message to greet {username} in 'learn' mode. "
                f"As a language learning coach,In 'learn' mode, {username} will have the opportunity to expand their vocabulary,  and receive corrections for any mistakes. "
                f"Encourage {username} to practice by typing words or sentences in {language} that they wish to learn. "
                f"All explanations and guidance will be provided in {language}, ensuring a full immersion experience. "
                f"If {language} is different from English, please translate your message into English for better understanding. "
                f"Keep your response friendly, clear, and concise at A1 level. Limit your response to 50 words."
                f"Don't add phrases like Here is a friendly message to greetin 'learn' mode give the greetings directly"
            )
        else:  # mode == "talk"
            welcome_prompt = (
                f"Compose a warm and inviting message to welcome {username} to a relaxed chat. "
                f"As a language learning coach, use only {language} to provide guidance and encouragement. "
                f"Limit your response to 50 words or less."
            )

        welcome_message = self.get_groq_response(
            [{"role": "user", "content": welcome_prompt}]
        )

        conversation_id = log_conversation_to_db(username, language, mode)
        print(f"Initialized conversation with ID: {conversation_id}")

        return {
            "history": [{"role": "assistant", "content": welcome_message}],
            "start_time": datetime.now(),
            "interaction_count": 0,
            "logging_enabled": True,
            "language": language,
            "mode": mode,
            "username": username,
            "conversation_id": conversation_id,
        }

    def process_user_message(
        self, conversations: Dict[str, Any], username: str, user_message: str
    ) -> str:
        try:
            conversation = conversations[username]
            system_prompt = self.create_system_prompt(
                conversation["language"].lower(), username, conversation["mode"]
            )

            conversation["history"].append({"role": "user", "content": user_message})
            conversation["interaction_count"] += 1

            history = [{"role": "system", "content": system_prompt}] + conversation[
                "history"
            ]

            chat_completion = CLIENT.chat.completions.create(
                messages=history, model=MODEL
            )
            response = self.clean_response(chat_completion.choices[0].message.content)

            conversation["history"].append({"role": "assistant", "content": response})

            log_message_to_db(conversation["conversation_id"], user_message, response)

            return response
        except Exception as e:
            return {"error": str(e)}

    def log_end_conversation(
        self, conversations: Dict[str, Any], username: str
    ) -> Dict[str, Any]:
        conversation = conversations[username]

        if conversation.get("ended", False):
            return {"error": "Conversation already ended"}

        end_time = datetime.now()
        duration = end_time - conversation["start_time"]
        evaluation_result = evaluate_last_conversation(
            username, conversation["language"]
        )
        evaluation_text = evaluation_result[0]
        success = log_evaluation_to_db(
            conversation["conversation_id"],
            evaluation_text,
            end_time,
            duration,
            conversation["interaction_count"],
        )

        if not success:
            return {"error": "Failed to log evaluation"}

        conversation["ended"] = True
        formatted_duration = format_duration(duration)

        result = {
            "interaction_count": conversation["interaction_count"],
            "total_duration": formatted_duration,
            "evaluation": evaluation_text,
            "mode": conversation["mode"],
            "language": conversation["language"],
        }

        del conversations[username]
        return result
