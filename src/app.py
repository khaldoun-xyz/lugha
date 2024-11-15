from flask import Flask, render_template, request, jsonify
from datetime import datetime
import os
import psycopg2
from dotenv import load_dotenv
from groq import Groq
from chat import log_conversation_to_db, get_groq_response
from evaluate import evaluate_last_conversation

load_dotenv()

app = Flask(__name__)

# Load environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("MODEL")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PW = os.getenv("POSTGRES_PW")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")

client = Groq(api_key=GROQ_API_KEY)

# In-memory storage for active conversations
conversations = {}

def create_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PW,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    username = data['username']
    user_message = data['message']
    language = data['language']

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
        {"role": "system", "content": "You reply in the language the user sends you."},
        {"role": "user", "content": user_message},
    ]

    # Get response from Groq LLM
    try:
        response = get_groq_response(conversation_history)
        conversations[username]['history'].append({'role': 'assistant', 'content': response})

        # Log the conversation to the database
        log_conversation_to_db(username, user_message, response, datetime.now(), None, conversations[username]['interaction_count'])

        return jsonify({'response': response})
    except Exception as e:
        print(f"Error getting response from Groq: {e}")
        return jsonify({'error': 'Failed to get response from LLM.'}), 500

@app.route('/end-chat', methods=['POST'])
def end_chat():
    username = request.json['username']
    
    if username not in conversations:
        return jsonify({'error': 'No active conversation found.'}), 404

    # Calculate duration
    end_time = datetime.now()
    start_time = conversations[username]['start_time']
    duration = (end_time - start_time).total_seconds()

    # Log the end of the conversation in the database
    log_conversation_to_db(username, '', '', start_time, end_time, conversations[username]['interaction_count'])

    # Clear conversation state
    del conversations[username]

    return jsonify({'message': 'Chat ended successfully.'})

@app.route('/evaluate', methods=['POST'])
def evaluate():
    data = request.json
    username = data['username']
    language = data['language']

    # Evaluate the last conversation
    evaluation, interaction_count, duration = evaluate_last_conversation(username, language)

    if evaluation is None:
        return jsonify({'error': 'No valid evaluation found.'}), 400

    return jsonify({
        'evaluation': evaluation,
        'interaction_count': interaction_count,
        'duration': duration
    })

if __name__ == '__main__':
    app.run(debug=True)