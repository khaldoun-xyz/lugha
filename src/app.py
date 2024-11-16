from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from datetime import datetime
from create_db import initialize_groq_client
from chat import log_conversation_to_db, create_db_connection
from evaluate import evaluate_last_conversation,get_last_conversation, format_duration


app = Flask(__name__, template_folder='templates')
socketio = SocketIO(app)


config = initialize_groq_client()
client = config["client"]

POSTGRES_DB = config["POSTGRES_DB"]
POSTGRES_USER = config["POSTGRES_USER"]
POSTGRES_PW = config["POSTGRES_PW"]
POSTGRES_HOST = config["POSTGRES_HOST"]
POSTGRES_PORT = config["POSTGRES_PORT"]
MODEL = config["MODEL"]



# Store active conversations
conversations = {}

@app.route('/chat', methods=['POST'])
def chat():
    username = request.json['username']
    user_message = request.json['message']
    language = request.json['language']

    # Initialize conversation if not already started
    if username not in conversations:
        conversations[username] = {
            'history': [],
            'start_time': datetime.now(),
            'interaction_count': 0
        }

    # Append user message to history and increment interaction count
    conversations[username]['history'].append({'role': 'user', 'content': user_message})
    conversations[username]['interaction_count'] += 1

    # Prepare conversation history for the model
    conversation_history = [
        {"role": "system", "content": "You reply in 50 words or less in the language the user sends you."},
    ] + conversations[username]['history']  
    conversation_history.append({"role": "user", "content": user_message})

    try:
        chat_completion = client.chat.completions.create(
            messages=conversation_history,
            model=MODEL,
        )
        response = chat_completion.choices[0].message.content.strip()
        conversations[username]['history'].append({'role': 'assistant', 'content': response})

        # Log the conversation to the database
        log_conversation_to_db(
            username,
            user_message,
            response,
            conversations[username]['start_time'],
            datetime.now(),  # End time
            conversations[username]['interaction_count']
        )

        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/end-conversation', methods=['POST'])
def end_conversation():
    username = request.json['username']
    
    if username not in conversations:
        return jsonify({'error': 'No active conversation found.'}), 404

    # Calculate end time and duration
    end_time = datetime.now()
    start_time = conversations[username]['start_time']
    interaction_count = conversations[username]['interaction_count']
    duration = end_time - start_time

    log_conversation_to_db(username, '', '', start_time, end_time, interaction_count)
    language = request.json.get('language')
    evaluation, _, _ = evaluate_last_conversation(username, language)
    # Clear conversation state
    del conversations[username]

    return jsonify({
        'interaction_count': interaction_count,
        'total_duration': format_duration(duration),
        'evaluation': evaluation
    })

@app.route('/evaluate', methods=['POST'])
def evaluate():
    data = request.json
    required_keys = ['username', 'language', 'start_time', 'end_time']
    
    for key in required_keys:
        if key not in data:
            return jsonify({'error': f'Missing required key: {key}'}), 400

    username = data['username']
    language = data['language']
    conversation_history, _, _ = get_last_conversation(username)

    if not conversation_history:
        return jsonify({'error': 'No conversation history available for evaluation.'}), 400

    evaluation = evaluate_last_conversation(conversation_history, language)
    return jsonify ({'evaluation': evaluation})

@app.route('/track_progress')
def track_progress():
    return render_template('track_progress.html')

@app.route('/fetch-progress', methods=['POST'])
def fetch_progress():
    username = request.json['username']
    try:
        conn = create_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT duration, interaction_count, evaluation FROM conversations WHERE username = %s AND evaluation IS NOT NULL",
                (username,)
            )
            progress = cursor.fetchall()
            result = []
            for row in progress:
                duration = row[0]  # This should be a timedelta object
                formatted_duration = format_duration(duration)  # Use your existing formatting function

                result.append({
                    'duration': formatted_duration,  # Use the formatted duration
                    'interaction_count': row[1],
                    'evaluation': row[2]
                })
    except Exception as e:
        print(f"Error fetching progress data: {e}")
        return jsonify({'error': 'Failed to fetch progress data'}), 500
    finally:
        conn.close()

    return jsonify({'progress': result})

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)