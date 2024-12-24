# app.py
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO

from utils.config import Config, initialize_groq_client
from utils.learning_themes import LEARNING_THEMES
from utils.database_utils import fetch_progress_data
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
    username, language, theme, emoji = data['username'], data['language'], data['theme'], data['emoji']
    conversations[username] = initialize_conversation(language, theme, emoji, username)
    return jsonify({'response': conversations[username]['history'][0]['content']})

@app.route('/restart-conversation', methods=['POST'])
def restart_conversation():
    data = request.json
    username, language, theme, emoji = data['username'], data['language'], data['theme'], data['emoji']
    conversations[username] = restart_conversation_logic(conversations, username, language, theme, emoji)
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
    data = request.json
    username = data.get('username')
    sort_order = data.get('sort_order', 'asc') 
    language_filter = data.get('language', 'all') 
    theme_filter = data.get('theme', 'all')
    progress = fetch_progress_data(username, sort_order, language_filter, theme_filter)
    if progress is None:
        return jsonify({'error': 'Failed to fetch progress data'}), 500
    elif not progress: 
        return jsonify({'message': 'No progress data available for this user.'}), 404
    return jsonify({'progress': progress}), 200  

@app.route('/track_progress')
def track_progress():
    return render_template('track_progress.html', learning_themes=LEARNING_THEMES.keys())

@app.route('/chat-interface')
def chat_interface():
    username = request.args.get('username')
    assistant_name = request.args.get('assistantName', 'Default Assistant')
    language = request.args.get('language')
    theme = request.args.get('theme')
    emoji = request.args.get('emoji', '😊')
    return render_template('chat_interface.html', username=username, assistant_name=assistant_name, language=language, theme=theme, learning_themes=LEARNING_THEMES.keys(), emoji=emoji)

@app.route('/')
def welcome():
    return render_template('welcome.html', learning_themes=LEARNING_THEMES.keys())

if __name__ == '__main__':
    app.run(debug=True)