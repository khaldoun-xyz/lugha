from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from datetime import datetime
import os
import psycopg2
from dotenv import load_dotenv
from groq import Groq
from chat import log_conversation_to_db
from evaluate import evaluate_last_conversation,get_last_conversation



load_dotenv()

app = Flask(__name__, template_folder='templates')
socketio = SocketIO(app)



# Load environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("MODEL")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PW = os.getenv("POSTGRES_PW")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")

client = Groq(api_key=GROQ_API_KEY)

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

    # Append user message to history
    conversations[username]['history'].append({'role': 'user', 'content': user_message})
    conversations[username]['interaction_count'] += 1

    # Prepare conversation history for the model
    conversation_history = [
        {"role": "system", "content": "You reply in 50 words or less in the language the user sends you."},
        {"role": "user", "content": user_message},
    ]

    try:
        chat_completion = client.chat.completions.create(
            messages=conversation_history,
            model=MODEL,
        )
        response = chat_completion.choices[0].message.content.strip()
        conversations[username]['history'].append({'role': 'assistant', 'content': response})

        # Log the conversation to the database
        start_time = conversations[username]['start_time']
        end_time = datetime.now()  # Set end time for each interaction
        log_conversation_to_db(username, user_message, response, start_time, end_time, conversations[username]['interaction_count'])

        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': str(e)})

def format_duration(seconds):
    """Format the duration from seconds to a human-readable format."""
    if seconds < 60:
        return f"{int(seconds)} seconds"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02}:{seconds:02}"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"
@app.route('/end-conversation', methods=['POST'])
def end_conversation():
    username = request.json['username']
    
    if username not in conversations:
        return jsonify({'error': 'No active conversation found.'}), 404

    # Calculate duration
    end_time = datetime.now()
    start_time = conversations[username]['start_time']
    duration = (end_time - start_time).total_seconds()

    formatted_duration = format_duration(duration)
    interaction_count = conversations[username]['interaction_count']
    language = request.json.get('language')
    conversation_history, _, _ = get_last_conversation(username)

    if not conversation_history:
        return jsonify({'error': 'No conversation history available for evaluation.'}), 400
    evaluation, _, _ = evaluate_last_conversation(username, language)
    log_conversation_to_db(username, '', '', start_time, end_time, interaction_count)

    # Clear conversation state
    del conversations[username]

    response_data = {
        'interaction_count': interaction_count,
        'total_duration': formatted_duration,
        'evaluation': evaluation
    }
    
    return jsonify(response_data)

@app.route('/evaluate', methods=['POST'])
def evaluate():
    data = request.json
    required_keys = ['username', 'language', 'start_time', 'end_time']
    
    for key in required_keys:
        if key not in data:
            return jsonify({'error': f'Missing required key: {key}'}), 400

    username = data['username']
    language = data['language']
    start_time = data['start_time']
    end_time = data['end_time']
    print(f"Received evaluation request: {data}")
    conversation_history = get_last_conversation(username, start_time, end_time)

    if not conversation_history:
        return jsonify({'error': 'No conversation history available for evaluation.'}), 400

    evaluation = evaluate_last_conversation(conversation_history, language)
    return jsonify({'evaluation': evaluation})

@app.route('/track_progress')
def track_progress():
    return render_template('track_progress.html')


@app.route('/track_progress')
def get_track_progress():
    username = request.json['username']
    try:
        conn = psycopg2.connect(
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PW,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
        )
        with conn.cursor() as cursor:
            cursor.execute(
            "SELECT * FROM conversations ORDER BY created_at DESCWHERE username = %s",
                    (username,)
                )
            progress = cursor.fetchall()
    finally:
        if conn:
            conn.close()
    return jsonify([dict(row) for row in progress])

@app.route('/fetch-progress', methods=['POST'])
def fetch_progress():
    username = request.json['username']
    try:
        conn = psycopg2.connect(
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PW,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
        )
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT duration, interaction_count, evaluation FROM conversations WHERE username = %s",
                (username,)
            )
            progress = cursor.fetchall()
            result = [{'duration': row[0], 'interaction_count': row[1], 'evaluation':row[2]} for row in progress]
    except Exception as e:
        print(f"Error fetching progress data: {e}")
        return jsonify({'error': 'Failed to fetch progress data'}), 500
    finally:
        if conn:
            conn.close()

    return jsonify({'progress': result})

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)