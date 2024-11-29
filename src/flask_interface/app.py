#app.py
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO

from utils.config import Config, initialize_groq_client
from utils.database_utils import fetch_user_progress
from utils.conversation_utils import (
    initialize_conversation,
    restart_conversation_logic,
    process_user_message,
    log_end_conversation,
    evaluate_conversation
)

client = initialize_groq_client()
MODEL = Config.MODEL
app = Flask(__name__, template_folder='templates')
socketio = SocketIO(app)
conversations = {}



@app.route('/start-evaluation', methods=['POST'])
def start_evaluation():
    data = request.json
    username, language = data['username'], data['language']
    conversations[username] = initialize_conversation(language)
    return jsonify({'response': conversations[username]['history'][0]['content']})


@app.route('/restart-conversation', methods=['POST'])
def restart_conversation():
    data = request.json
    username, language = data['username'], data['language']
    conversations[username] = restart_conversation_logic(conversations, username, language)
    return jsonify({'response': conversations[username]['history'][0]['content']})


@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    username, user_message = data['username'], data['message']
    if username not in conversations:
        return jsonify({'error': 'No active conversation found.'}), 404

    response = process_user_message(conversations, client, MODEL, username, user_message)
    if isinstance(response, dict) and 'error' in response:
        return jsonify(response), 500
    return jsonify({'response': response})


@app.route('/end-conversation', methods=['POST'])
def end_conversation():
    username = request.json['username']
    if username not in conversations:
        return jsonify({'error': 'No active conversation found.'}), 404

    summary = log_end_conversation(conversations, username)
    return jsonify(summary)


@app.route('/evaluate', methods=['POST'])
def evaluate():
    data = request.json
    username = data.get('username')
    if username not in conversations:
        return jsonify({'error': 'No active conversation found.'}), 404

    result = evaluate_conversation(conversations, username)
    if isinstance(result, dict) and 'error' in result:
        return jsonify(result), 400
    return jsonify({'evaluation': result})


@app.route('/fetch-progress', methods=['POST'])
def fetch_progress():
    username = request.json['username']
    progress = fetch_user_progress(username)
    if isinstance(progress, dict) and 'error' in progress:
        return jsonify(progress), 500
    return jsonify({'progress': progress})


@app.route('/track_progress')
def track_progress():
    return render_template('track_progress.html')


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
