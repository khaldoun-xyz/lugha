# app.py
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO

from evaluation_utils.evaluate import evaluate_last_conversation
from utils.config import Config, initialize_groq_client
from utils.conversation_utils import ConversationManager
from utils.database_utils import fetch_all_users, fetch_progress_data

client = initialize_groq_client()
MODEL = Config.MODEL
app = Flask(__name__, template_folder="templates")
socketio = SocketIO(app)

CONVERSATIONS = {}
CONVERSATION_MANAGER = ConversationManager()


@app.route("/start-evaluation", methods=["POST"])
def start_evaluation():
    data = request.json
    username, language, mode = data["username"], data["language"], data["mode"]
    conversation_data = CONVERSATION_MANAGER.initialize_conversation(
        language, mode, username
    )
    CONVERSATIONS[username] = conversation_data
    return jsonify({"response": conversation_data["history"][0]["content"]})


@app.route("/restart-conversation", methods=["POST"])
def restart_conversation():
    data = request.json
    username, language, mode = data["username"], data["language"], data["mode"]
    conversation_data = CONVERSATION_MANAGER.initialize_conversation(
        language, mode, username
    )
    CONVERSATIONS[username] = conversation_data
    return jsonify({"response": conversation_data["history"][0]["content"]})


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    username, user_message = data["username"], data["message"]
    if username not in CONVERSATIONS:
        return jsonify({"error": "No active conversation found."}), 404

    response = CONVERSATION_MANAGER.process_user_message(
        CONVERSATIONS, username, user_message
    )
    if isinstance(response, dict) and "error" in response:
        return jsonify(response), 500
    return jsonify({"response": response})


@app.route("/end-conversation", methods=["POST"])
def end_conversation():
    username = request.json["username"]
    if username not in CONVERSATIONS:
        return jsonify({"error": "No active conversation found."}), 404

    summary = CONVERSATION_MANAGER.log_end_conversation(CONVERSATIONS, username)
    return jsonify(summary)


@app.route("/evaluate", methods=["POST"])
def evaluate():
    data = request.json
    username = data.get("username")
    if username not in CONVERSATIONS:
        return jsonify({"error": "No active conversation found."}), 404

    result = evaluate_last_conversation(username, CONVERSATIONS[username]["language"])
    if isinstance(result, dict) and "error" in result:
        return jsonify(result), 400
    return jsonify({"evaluation": result})


@app.route("/fetch-progress", methods=["POST"])
def fetch_progress():
    try:
        data = request.json
        username = data.get("username")
        sort_order = data.get("sort_order", "asc")

        progress = fetch_progress_data(
            username=username,
            sort_order=sort_order,
        )

        if progress is None:
            return (
                jsonify({"error": "An error occurred while fetching progress data"}),
                500,
            )

        if not progress:
            return (
                jsonify(
                    {
                        "progress": [],
                        "message": "No data found for the selected filters",
                    }
                ),
                200,
            )

        return jsonify({"progress": progress}), 200

    except Exception as e:
        return jsonify({"error": "An unexpected error occurred"}), 500


@app.route("/track_progress")
def track_progress():
    return render_template("lugha/track_progress.html")


@app.route("/chat-interface")
def chat_interface():
    username = request.args.get("username")
    language = request.args.get("language")
    mode = request.args.get("mode")
    return render_template(
        "lugha/chat_interface.html",
        username=username,
        language=language,
        mode=mode,
    )


@app.route("/")
def welcome():
    return render_template("lugha/welcome.html")


@app.route("/admin")
def admin_page():
    users = fetch_all_users()
    return render_template("lugha/admin.html", users=users)


@app.route("/api/conversations/<username>")
def get_conversations(username):
    conversations_data = fetch_progress_data(username)
    return jsonify(conversations_data)


@app.route("/api/users")
def get_users():
    users = fetch_all_users()
    return jsonify(users)


if __name__ == "__main__":
    app.run(debug=True)
