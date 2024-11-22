from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from datetime import datetime
from chat import log_conversation_to_db,  get_groq_response
from evaluate import evaluate_last_conversation, get_last_conversation, format_duration
from config import Config, create_db_connection, initialize_groq_client
from learning_themes import LEARNING_THEMES
import random
import re

client = initialize_groq_client()
MODEL = Config.MODEL
app = Flask(__name__, template_folder='templates')
socketio = SocketIO(app)



conversations = {}

@app.route('/start-evaluation', methods=['POST'])
def start_evaluation():
    username = request.json['username']
    language = request.json['language']

    conversations[username] = {
        'history': [],
        'start_time': datetime.now(),
        'interaction_count': 0,
        'logging_enabled': True,
        'language': language  
    }


    welcome_prompt = f"Generate a welcoming message for a language learning chatbot just in {language}. Reply in 50 words or less."
    welcome_message = get_groq_response([{"role": "user", "content": welcome_prompt}])
    conversations[username]['history'].append({'role': 'assistant', 'content': welcome_message})

    return jsonify({'response': welcome_message})

@app.route('/restart-conversation', methods=['POST'])
def restart_conversation():
    username = request.json['username']
    language = request.json['language']

    if username in conversations:
        del conversations[username]
    conversations[username] = {
        'history': [],
        'start_time': datetime.now(),
        'interaction_count': 0,
        'logging_enabled': True,
        'language': language
    }

    welcome_prompt = f"Generate a welcoming message for a language learning chatbot just in {language}. Reply in 50 words or less."
    welcome_message = get_groq_response([{"role": "user", "content": welcome_prompt}])
    welcome_message = welcome_message.replace('"', '').strip()  
    conversations[username]['history'].append({'role': 'assistant', 'content': welcome_message})

    return jsonify({'response': welcome_message})

@app.route('/chat', methods=['POST'])
def chat():
    username = request.json['username']
    user_message = request.json['message']
    language = conversations[username]['language'].lower()  

    if user_message.strip(): 
        conversations[username]['history'].append({'role': 'user', 'content': user_message})
        conversations[username]['interaction_count'] += 1

        # Prepare conversation history for the model
        conversation_history = [
            {"role": "system", "content": f"You are a language coach. Reply in 50 words or less in {language}."},
        ] + conversations[username]['history']  
        conversation_history.append({"role": "user", "content": user_message})

        try:
            chat_completion = client.chat.completions.create(
                messages=conversation_history,
                model=MODEL,
            )
            response = chat_completion.choices[0].message.content.strip()
            response = response.replace('"', '').strip() 
            response = re.sub(r'\(.*?\)', '', response).strip() 
            conversations[username]['history'].append({'role': 'assistant', 'content': response})


            if conversations[username]['interaction_count'] == 1:
                start_conversation_prompt = f"what would you like to talk about  just in {language} in 50 words or less . "
                start_conversation_message = get_groq_response([{"role": "user", "content": start_conversation_prompt}])
                start_conversation_message = start_conversation_message.replace('"', '').strip()  
                start_conversation_message = re.sub(r'\(.*?\)', '', start_conversation_message).strip() 
                conversations[username]['history'].append({'role': 'assistant', 'content': start_conversation_message})
                response = start_conversation_message 

            elif conversations[username]['interaction_count'] == 3:
                themes = list(LEARNING_THEMES.keys())
                random_theme = random.choice(themes)
                theme_prompt = f"Let's dive in {random_theme} for discussing or  if you have a specific subject in mind, all this just in {language} and in 50 words or less."
                
                theme_message = get_groq_response([{"role": "user", "content": theme_prompt}])
                theme_message = theme_message.replace('"', '').strip() 
                theme_message = re.sub(r'\(.*?\)', '', theme_message).strip() 
                conversations[username]['history'].append({'role': 'assistant', 'content': theme_message})
                response += "\n" + theme_message  
            log_conversation_to_db(
                username,
                user_message,
                response,
                conversations[username]['start_time'],
                datetime.now(),    
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

    end_time = datetime.now()
    start_time = conversations[username]['start_time']
    interaction_count = conversations[username]['interaction_count']
    duration = end_time - start_time

    log_conversation_to_db(username , '', '', start_time , end_time, interaction_count)
    language = conversations[username]['language'] 
    evaluation, _, _ = evaluate_last_conversation(username, language)
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
    language = conversations[username]['language'] 
    conversation_history, _, _ = get_last_conversation(username)

    if not conversation_history:
        return jsonify({'error': 'No conversation history available for evaluation.'}), 400

    evaluation = evaluate_last_conversation(conversation_history, language)
    return jsonify({'evaluation': evaluation})

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
                duration = row[0]  
                formatted_duration = format_duration(duration) 

                result.append({
                    'duration': formatted_duration, 
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