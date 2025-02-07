# evaluation_utils/evaluate.py
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional, Tuple

from utils.config import Config, create_db_connection, initialize_groq_client

client = initialize_groq_client()
MODEL = Config.MODEL


@dataclass
class ConversationTimes:
    start_time: datetime
    end_time: datetime


@dataclass
class ConversationDetails:
    conversation_text: str
    interaction_count: int
    duration: Optional[datetime]


class DatabaseManager:
    @staticmethod
    def fetch_last_conversation_id(username: str) -> Optional[int]:
        query = """
        SELECT conversation_id
        FROM conversations_parameters
        WHERE user_name = %s
        ORDER BY created_at DESC
        LIMIT 1
        """
        with create_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (username,))
                result = cursor.fetchone()
                return result[0] if result else None

    @staticmethod
    def fetch_conversation_times(conversation_id: int) -> Optional[ConversationTimes]:
        query = """
        SELECT start_time, end_time
        FROM conversations_parameters cp
        LEFT JOIN conversations_evaluations ce ON cp.conversation_id = ce.conversation_id
        WHERE cp.conversation_id = %s
        """
        with create_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (conversation_id,))
                result = cursor.fetchone()
                if result:
                    return ConversationTimes(*result)
                return None

    @staticmethod
    def fetch_conversation_messages(conversation_id: int) -> List[Tuple]:
        query = """
        SELECT user_prompt, bot_messages, interaction_count
        FROM conversations_parameters cp
        LEFT JOIN conversations_evaluations ce ON cp.conversation_id = ce.conversation_id
        WHERE cp.conversation_id = %s
        ORDER BY cp.created_at ASC
        """
        with create_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (conversation_id,))
                return cursor.fetchall()

    @staticmethod
    def log_evaluation(
        conversation_id: int, evaluation: str, end_time: datetime
    ) -> None:
        query = """
        UPDATE conversations_evaluations
        SET evaluation = %s, end_time = %s
        WHERE conversation_id = %s
        """
        with create_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (evaluation, end_time, conversation_id))
                conn.commit()


class ConversationFormatter:
    @staticmethod
    def format_conversation(messages: List[Tuple]) -> str:
        formatted_messages = []
        for prompt, response, _ in messages:
            user_message = f":User  {prompt}" if prompt else ""
            bot_message = f"Instructor: {response}" if response else ""
            if user_message or bot_message:
                formatted_messages.extend(
                    [msg for msg in [user_message, bot_message] if msg]
                )
        return "\n".join(formatted_messages)

    @staticmethod
    def format_duration(duration: Optional[datetime]) -> str:
        if not duration:
            return "Duration not available"

        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return f"{hours:02}:{minutes:02}:{seconds:02}"
        if minutes > 0:
            return f"{minutes:02}:{seconds:02}"
        return f"{seconds}s"


def count_user_words(text: str) -> int:
    return len(text.split())


def check_evaluation_criteria(messages: List[Tuple]) -> Tuple[bool, int]:
    total_user_words = sum(count_user_words(msg[0]) for msg in messages if msg[0])
    meets_criteria = total_user_words >= 10
    return meets_criteria, total_user_words


class LanguageEvaluator:
    def __init__(self, client: Any, model: str):
        self.client = client
        self.model = model
        self.db = DatabaseManager()

    def create_evaluation_prompt(self, conversation: str, language: str) -> str:
        return (
            f"As an expert {language} language evaluator, analyze this conversation and provide:\n\n"
            f"1. **Brief Proficiency Overview:**\n"
            f"- Overall Score: __%\n"
            f"- Grammar Accuracy: __%\n"
            f"- Vocabulary Usage: __%\n"
            f"- Communication Effectiveness: __%\n\n"
            f"2. **Top 3-5 Most Impactful Mistakes:**\n"
            f"- Provide each mistake in the format: [original] → [correction]\n"
            f"3. **Quick Improvement Tips:**\n"
            f"- Include two actionable suggestions for focused practice.\n\n"
            f"Conversation to evaluate:\n{conversation}"
        )

    def get_evaluation(self, prompt: str) -> str:
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert language evaluator focusing on detailed, actionable feedback.",
                    },
                    {"role": "user", "content": prompt},
                ],
                model=self.model,
            )
            return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            return f"Evaluation error: {str(e)}"

    def evaluate_conversation(
        self, username: str, language: str
    ) -> Tuple[str, int, str]:
        conversation_id = self.db.fetch_last_conversation_id(username)
        if not conversation_id:
            return "No conversation found.", 0, "00:00"

        messages = self.db.fetch_conversation_messages(conversation_id)
        if not messages:
            return "No messages found.", 0, "00:00"

        formatted_conversation = ConversationFormatter.format_conversation(messages)
        interaction_count = messages[-1][2] if messages else 0
        times = self.db.fetch_conversation_times(conversation_id)
        duration = times.end_time - times.start_time if times else None

        meets_criteria, total_user_words = check_evaluation_criteria(messages)
        if not meets_criteria:
            return (
                "Your conversation didn’t meet the criteria for evaluation. Please send at least 10 words to receive meaningful feedback.",
                0,
                "00:00",
            )

        evaluation_prompt = self.create_evaluation_prompt(
            formatted_conversation, language
        )
        evaluation = self.get_evaluation(evaluation_prompt)

        self.db.log_evaluation(
            conversation_id, evaluation, times.end_time if times else datetime.now()
        )

        return (
            evaluation,
            interaction_count,
            ConversationFormatter.format_duration(duration),
        )


evaluator = LanguageEvaluator(client, MODEL)


def format_duration(duration: Optional[datetime]) -> str:
    return ConversationFormatter.format_duration(duration)


def get_last_conversation(username: str) -> Tuple[str, int, Optional[datetime]]:
    db = DatabaseManager()
    conversation_id = db.fetch_last_conversation_id(username)

    if not conversation_id:
        return "", 0, None

    messages = db.fetch_conversation_messages(conversation_id)
    formatted_conversation = ConversationFormatter.format_conversation(messages)
    interaction_count = messages[-1][2] if messages else 0
    times = db.fetch_conversation_times(conversation_id)
    duration = times.end_time - times.start_time if times else None

    return formatted_conversation, interaction_count, duration


def evaluate_last_conversation(username: str, language: str) -> Tuple[str, int, str]:
    evaluation, interaction_count, duration = evaluator.evaluate_conversation(
        username, language
    )
    return evaluation, interaction_count, duration


__all__ = [
    "format_duration",
    "get_last_conversation",
    "evaluate_last_conversation",
    "ConversationFormatter",
    "DatabaseManager",
    "LanguageEvaluator",
    "count_user_words",
    "check_evaluation_criteria",
]
