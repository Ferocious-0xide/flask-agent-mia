import os
from flask import Flask, request, jsonify, render_template, redirect, url_for
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

class HerokuAgent:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = f"https://api.heroku.com"
        self.headers = {
            "Accept": "application/vnd.heroku+json; version=3",
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    async def web_browsing_single_page(self, url: str) -> Dict[str, Any]:
        """Browse a single web page and extract its content."""
        try:
            response = requests.post(
                f"{self.base_url}/managed-inference/browse",
                headers=self.headers,
                json={"url": url}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error in web_browsing_single_page: {str(e)}")
            raise

    async def web_browsing_multi_page(self, urls: List[str]) -> Dict[str, Any]:
        """Browse multiple web pages and extract their content."""
        try:
            response = requests.post(
                f"{self.base_url}/managed-inference/browse-multi",
                headers=self.headers,
                json={"urls": urls}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error in web_browsing_multi_page: {str(e)}")
            raise

    async def database_get_schema(self, database_url: str) -> Dict[str, Any]:
        """Get the schema of a database."""
        try:
            response = requests.get(
                f"{self.base_url}/managed-inference/database/schema",
                headers=self.headers,
                params={"database_url": database_url}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error in database_get_schema: {str(e)}")
            raise

    async def database_run_query(self, query: str, database_url: str) -> Dict[str, Any]:
        """Run a query against a database."""
        try:
            response = requests.post(
                f"{self.base_url}/managed-inference/database/query",
                headers=self.headers,
                json={
                    "query": query,
                    "database_url": database_url
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error in database_run_query: {str(e)}")
            raise

    async def code_exec(self, code: str, language: str) -> Dict[str, Any]:
        """Execute code in a specified language."""
        try:
            response = requests.post(
                f"{self.base_url}/managed-inference/code/execute",
                headers=self.headers,
                json={
                    "code": code,
                    "language": language
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error in code_exec: {str(e)}")
            raise

    async def dyno_run_command(self, command: str) -> Dict[str, Any]:
        """Run a command on a Heroku dyno."""
        try:
            response = requests.post(
                f"{self.base_url}/managed-inference/dyno/command",
                headers=self.headers,
                json={"command": command}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error in dyno_run_command: {str(e)}")
            raise

    async def pdf_read(self, pdf_url: str) -> Dict[str, Any]:
        """Read and extract content from a PDF file."""
        try:
            response = requests.post(
                f"{self.base_url}/managed-inference/pdf/read",
                headers=self.headers,
                json={"pdf_url": pdf_url}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error in pdf_read: {str(e)}")
            raise

    async def search_web(self, query: str) -> Dict[str, Any]:
        """Search the web using a query string."""
        try:
            response = requests.post(
                f"{self.base_url}/managed-inference/search",
                headers=self.headers,
                json={"query": query}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error in search_web: {str(e)}")
            raise

# Initialize the Heroku agent
agent = HerokuAgent(HEROKU_API_KEY)

@app.route('/clear', methods=['GET'])
def clear_chat():
    """Clear the chat history and redirect to home."""
    recent_qa.clear()
    return redirect(url_for('qa_interface'))

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

@app.route('/browse', methods=['POST'])
@require_api_key
async def browse():
    """Handle single page browsing requests."""
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        result = await agent.web_browsing_single_page(url)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/browse-multi', methods=['POST'])
@require_api_key
async def browse_multi():
    """Handle multi-page browsing requests."""
    data = request.get_json()
    urls = data.get('urls')
    if not urls or not isinstance(urls, list):
        return jsonify({'error': 'List of URLs is required'}), 400
    
    try:
        result = await agent.web_browsing_multi_page(urls)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/database/schema', methods=['GET'])
@require_api_key
async def get_schema():
    """Handle database schema requests."""
    database_url = request.args.get('database_url')
    if not database_url:
        return jsonify({'error': 'Database URL is required'}), 400
    
    try:
        result = await agent.database_get_schema(database_url)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/database/query', methods=['POST'])
@require_api_key
async def run_query():
    """Handle database query requests."""
    data = request.get_json()
    query = data.get('query')
    database_url = data.get('database_url')
    
    if not query or not database_url:
        return jsonify({'error': 'Query and database URL are required'}), 400
    
    try:
        result = await agent.database_run_query(query, database_url)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/code/execute', methods=['POST'])
@require_api_key
async def execute_code():
    """Handle code execution requests."""
    data = request.get_json()
    code = data.get('code')
    language = data.get('language')
    
    if not code or not language:
        return jsonify({'error': 'Code and language are required'}), 400
    
    try:
        result = await agent.code_exec(code, language)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/dyno/command', methods=['POST'])
@require_api_key
async def run_command():
    """Handle dyno command requests."""
    data = request.get_json()
    command = data.get('command')
    
    if not command:
        return jsonify({'error': 'Command is required'}), 400
    
    try:
        result = await agent.dyno_run_command(command)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/pdf/read', methods=['POST'])
@require_api_key
async def read_pdf():
    """Handle PDF reading requests."""
    data = request.get_json()
    pdf_url = data.get('pdf_url')
    
    if not pdf_url:
        return jsonify({'error': 'PDF URL is required'}), 400
    
    try:
        result = await agent.pdf_read(pdf_url)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search', methods=['POST'])
@require_api_key
async def search():
    """Handle web search requests."""
    data = request.get_json()
    query = data.get('query')
    
    if not query:
        return jsonify({'error': 'Search query is required'}), 400
    
    try:
        result = await agent.search_web(query)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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