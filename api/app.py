from flask import Flask, request, jsonify, make_response
import os
from openai import OpenAI
from dotenv import load_dotenv
from flask_cors import CORS
from datetime import datetime, timedelta
import sys
import pytz

# Add the parent directory to Python path so we can import the models
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from models.base import Database
from models.todo import Todo, TaskState

load_dotenv()

# Initialize database with the correct path
db_path = os.path.join(parent_dir, "nosy_bot.db")
print(f"Using database at: {db_path}")
db = Database(db_path)

# Update Todo class to use our database instance
Todo.db = db

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
TIMEZONE = pytz.timezone('Asia/Bangkok')  # UTC+7

# Add a simple GET endpoint
@app.route('/api/test', methods=['GET', 'OPTIONS'])
def test():
    response = make_response(jsonify({
        'message': 'API is working!',
        'status': 'success'
    }))
    # Add CORS header
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    return response

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    # Handle preflight request
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response

    try:
        data = request.get_json(force=True)
        prompt = data.get('prompt')
        
        if not prompt:
            response = make_response(jsonify({'error': 'No prompt provided'}), 400)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
        
        llm_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        response = make_response(jsonify({
            'response': llm_response.choices[0].message.content
        }))
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        error_response = make_response(jsonify({'error': str(e)}), 500)
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response

@app.route('/api/summarize_done', methods=['POST', 'OPTIONS'])
def summarize_done():
    try:
        data = request.get_json(force=True)
        user_id = data.get('user_id')
        days = data.get('days', 7)  # Default to last 7 days if not specified
        
        if not user_id:
            response = make_response(jsonify({'error': 'No user_id provided'}), 400)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
        
        # Calculate date range
        end_date = datetime.now(TIMEZONE)
        start_date = end_date - timedelta(days=days)
        print('start_date: ', start_date)
        print('end_date: ', end_date)
        print('user_id: ', user_id)
        
        # Get completed tasks from database
        completed_tasks = Todo.get_done_tasks(user_id)
        print('completed_tasks: ', completed_tasks)
        
        if not completed_tasks:
            response = make_response(jsonify({
                'summary': f"No completed tasks found in the last {days} days."
            }))
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
        
        # Format tasks for GPT
        task_list = "\n".join([f"- {task}" for _, task, _, _ in completed_tasks])
        
        # Generate summary using GPT
        llm_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": """
                    You are a personal assistant. 
                    tell me a brief summary of my accomplishments based on my completed tasks. 
                    Do not modify the tags mentioned in the tasks list. Make it short and concise.
                    Split the summary into 2 paragraphs: professional and personal.
                    """
                },
                {
                    "role": "user", 
                    "content": f"Here are the tasks I completed in the past {days} days:\n{task_list}"
                }
            ]
        )
        
        response = make_response(jsonify({
            'summary': llm_response.choices[0].message.content,
            'tasks': [task for _, task, _, _ in completed_tasks],
            'total_tasks': len(completed_tasks)
        }))
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        print('Error:', str(e))  # Add this for debugging
        error_response = make_response(jsonify({'error': str(e)}), 500)
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response

if __name__ == '__main__':
    app.run(debug=True, port=2108)