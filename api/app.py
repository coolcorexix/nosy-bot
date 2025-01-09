from flask import Flask, request, jsonify, make_response
import os
from openai import OpenAI
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

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

if __name__ == '__main__':
    app.run(debug=True, port=2108)