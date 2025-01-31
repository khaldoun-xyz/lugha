# conversation_utils.py
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from evaluation_utils.evaluate import (
    check_evaluation_criteria,
    evaluate_last_conversation,
    format_duration,
)
from utils.config import Config, initialize_groq_client
from utils.database_utils import log_conversation_to_db

client = initialize_groq_client()
MODEL = Config.MODEL


class ConversationManager:
    def __init__(self):
        self.client = client
        self.model = MODEL

    def clean_response(self, response: str) -> str:
        response = response.strip(' "\'"')
        return re.sub(r"\(.*?\)", "", response).strip()

    def get_groq_response(self, messages: List[Dict[str, str]]) -> str:
        try:
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
            )
            return self.clean_response(chat_completion.choices[0].message.content)
        except Exception as e:
            return f"Error: {e}"

    def create_system_prompt(self, language: str, username: str, theme: str) -> str:
        return (
            f"As a certified {language} instructor, I will communicate with {username} exclusively in {language}. "
            f"Our conversations will be tailored to a beginner's level, maintaining natural conversational patterns "
            f"while exploring the theme of {theme}. Responses will be limited to 50 words."
        )

    def initialize_conversation(
        self, language: str, theme: str, username: str
    ) -> Dict[str, Any]:
        welcome_prompt = (
            f"Compose a warm and inviting message to welcome {username} to a relaxed chat "
            f"about {theme}. As a language learning coach, use only {language} to provide "
            f"guidance and encouragement. Limit your response to 50 words or less."
        )
        welcome_message = self.get_groq_response(
            [{"role": "user", "content": welcome_prompt}]
        )

        return {
            "history": [{"role": "assistant", "content": welcome_message}],
            "start_time": datetime.now(),
            "interaction_count": 0,
            "logging_enabled": True,
            "language": language,
            "theme": theme,
            "username": username,
        }

    def process_user_message(
        self,
        conversations: Dict[str, Any],
        username: str,
        user_message: str,
    ) -> str:
        try:
            conversation = conversations[username]
            system_prompt = self.create_system_prompt(
                conversation["language"].lower(), username, conversation["theme"]
            )

            conversation["history"].append({"role": "user", "content": user_message})
            conversation["interaction_count"] += 1

            history = [{"role": "system", "content": system_prompt}] + conversation[
                "history"
            ]
            response = self.get_groq_response(history)

            conversation["history"].append({"role": "assistant", "content": response})
            self._log_conversation(conversation, username, user_message, response)

            return response
        except Exception as e:
            return {"error": str(e)}

    def _log_conversation(
        self,
        conversation: Dict[str, Any],
        username: str,
        user_message: str,
        response: str,
    ) -> None:
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

    def end_conversation(
        self, conversations: Dict[str, Any], username: str
    ) -> Dict[str, Any]:
        conversation = conversations[username]
        end_time = datetime.now()
        duration = end_time - conversation["start_time"]
        messages = [
            (msg["content"], "", 0)
            for msg in conversation["history"]
            if msg["role"] == "user"
        ]
        meets_criteria, total_user_words = check_evaluation_criteria(messages)

        evaluation = None
        if meets_criteria:
            evaluation, _, _ = evaluate_last_conversation(
                username, conversation["language"]
            )

        log_conversation_to_db(
            username,
            (
                conversation["history"][-1]["content"]
                if conversation["history"]
                else "No prompt"
            ),
            (
                conversation["history"][-1]["content"]
                if conversation["history"]
                else "No response"
            ),
            conversation["start_time"],
            end_time,
            conversation["interaction_count"],
            conversation["language"],
            conversation["theme"],
            is_final=True,
            evaluation=evaluation,
        )

        result = {
            "interaction_count": conversation["interaction_count"],
            "total_duration": format_duration(duration),
            "theme": conversation["theme"],
            "language": conversation["language"],
            "evaluation": (
                evaluation
                if meets_criteria
                else "Your conversation didn't meet the criteria for evaluation. Please send at least 10 words to receive meaningful feedback."
            ),
        }

        del conversations[username]
        return result
