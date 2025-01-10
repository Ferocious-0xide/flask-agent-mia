import os
from flask import Flask, request, jsonify, render_template
import requests
from functools import wraps
import json
from typing import Dict, Any, List
import logging
import tempfile
from collections import deque

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get Heroku configuration from environment variables
HEROKU_API_KEY = os.getenv('HEROKU_API_KEY')
HEROKU_APP_NAME = os.getenv('HEROKU_APP_NAME')
MODEL_API_KEY = os.getenv('HEROKU_MANAGED_INFERENCE_API_KEY')

# Store recent Q&As in memory (you could replace this with a database)
recent_qa = deque(maxlen=5)

# Sample Q&A data - you can expand this or connect to an actual QA service
qa_data = {
    "web browsing": "The agent can perform both single-page and multi-page web browsing, extracting content and data from websites securely.",
    "database": "The agent can interact with PostgreSQL databases, including schema inspection and secure query execution.",
    "code execution": "The agent can execute code in various languages and run commands on Heroku dynos safely.",
    "pdf": "The agent can read and extract content from PDF documents for analysis.",
    "search": "The agent can perform web searches and return relevant results.",
    "default": "I'm not sure about that specific capability. Please ask about web browsing, database operations, code execution, PDF processing, or web search functionality."
}

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != os.getenv('APP_API_KEY'):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

[Rest of the HerokuAgent class and API routes remain the same...]

@app.route('/', methods=['GET', 'POST'])
def qa_interface():
    question = None
    answer = None
    
    if request.method == 'POST':
        question = request.form.get('question', '').strip().lower()
        
        # Simple keyword-based answer matching
        answer = None
        for keyword, response in qa_data.items():
            if keyword in question:
                answer = response
                break
        
        if not answer:
            answer = qa_data['default']
            
        # Add to recent questions
        if question and answer:
            recent_qa.appendleft({
                'question': question,
                'answer': answer
            })
    
    return render_template('index.html',
                         question=question,
                         answer=answer,
                         recent_qa=list(recent_qa))

@app.route('/api/ask', methods=['POST'])
def api_ask():
    data = request.get_json()
    question = data.get('question', '').strip().lower()
    
    # Simple keyword-based answer matching
    answer = None
    for keyword, response in qa_data.items():
        if keyword in question:
            answer = response
            break
    
    if not answer:
        answer = qa_data['default']
        
    return jsonify({
        'question': question,
        'answer': answer
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)