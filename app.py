import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
app.secret_key = os.urandom(24)  # Required for session
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
ENV_VARS = {
    "INFERENCE_URL": os.getenv('INFERENCE_URL'),
    "INFERENCE_KEY": os.getenv('INFERENCE_KEY'),
    "INFERENCE_MODEL_ID": os.getenv('INFERENCE_MODEL_ID'),
    "HEROKU_API_KEY": os.getenv('HEROKU_API_KEY'),
    "HEROKU_APP_NAME": os.getenv('HEROKU_APP_NAME'),
    "APP_API_KEY": os.getenv('APP_API_KEY')
}

# Validate required environment variables
for env_var, value in ENV_VARS.items():
    if value is None:
        logger.error(f"Environment variable '{env_var}' is missing.")

# Store recent Q&As in memory
recent_qa = deque(maxlen=5)

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != ENV_VARS['APP_API_KEY']:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

class ClaudeAgent:
    def __init__(self, inference_url, inference_key, model_id):
        self.inference_url = inference_url
        self.headers = {
            "Authorization": f"Bearer {inference_key}",
            "Content-Type": "application/json"
        }
        self.model_id = model_id

    def generate_chat_completion(self, question: str) -> str:
        """Generate a response using Claude API."""
        try:
            endpoint_url = f"{self.inference_url}/v1/chat/completions"
            
            payload = {
                "model": self.model_id,
                "messages": [
                    {"role": "user", "content": question}
                ],
                "temperature": 0.7,
                "max_tokens": 500,
                "stream": False
            }

            response = requests.post(
                endpoint_url,
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                logger.error(f"API request failed: {response.status_code}, {response.text}")
                return f"I apologize, but I encountered an error: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error in generate_chat_completion: {str(e)}")
            return "I apologize, but I encountered an error processing your request."

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

class CohereAgent:
    def __init__(self, embedding_url, embedding_key, model_id):
        self.embedding_url = embedding_url
        self.model_id = model_id
        self.headers = {
            "Authorization": f"Bearer {embedding_key}",
            "Content-Type": "application/json"
        }

    def get_embeddings(self, texts: List[str], input_type: str = "search_document") -> Dict:
        """Generate embeddings for a list of texts."""
        try:
            payload = {
                "model": self.model_id,
                "input": texts,
                "input_type": input_type,
                "encoding_format": "base64",
                "embedding_types": ["float"]
            }

            response = requests.post(
                f"{self.embedding_url}/v1/embeddings",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Embedding API request failed: {response.status_code}, {response.text}")
                raise Exception(f"Embedding API request failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error in get_embeddings: {str(e)}")
            raise

def extract_text_from_file(file_path: str) -> str:
    """Extract text content from various file types."""
    file_ext = file_path.lower().split('.')[-1]
    
    try:
        if file_ext == 'txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        elif file_ext == 'pdf':
            text = []
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text.append(page.extract_text())
            return '\n'.join(text)
            
        elif file_ext in ['doc', 'docx']:
            doc = docx.Document(file_path)
            return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
            
    except Exception as e:
        logger.error(f"Error extracting text from file: {str(e)}")
        raise

# Initialize the agents
claude_agent = ClaudeAgent(
    ENV_VARS["INFERENCE_URL"],
    ENV_VARS["INFERENCE_KEY"],
    ENV_VARS["INFERENCE_MODEL_ID"]
)

heroku_agent = HerokuAgent(ENV_VARS["HEROKU_API_KEY"])

cohere_agent = CohereAgent(
    ENV_VARS["EMBEDDING_URL"],
    ENV_VARS["EMBEDDING_KEY"],
    ENV_VARS["EMBEDDING_MODEL_ID"]
)

import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/remove-file', methods=['POST'])
def remove_file():
    """Remove the current uploaded file."""
    if 'current_file' in session:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], session['current_file'])
        if os.path.exists(file_path):
            os.remove(file_path)
        session.pop('current_file', None)
    return '', 204

@app.route('/', methods=['GET', 'POST'])
def qa_interface():
    question = None
    answer = None
    current_file = session.get('current_file')
    
    if request.method == 'POST':
        # Handle file upload
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                try:
                    # Extract text from the file
                    text_content = extract_text_from_file(file_path)
                    
                    # Get embeddings for the text
                    embeddings = cohere_agent.get_embeddings([text_content])
                    
                    # Store the embeddings in the session
                    session['current_embeddings'] = embeddings
                    session['current_file'] = filename
                    
                except Exception as e:
                    logger.error(f"Error processing file: {str(e)}")
                    flash(f"Error processing file: {str(e)}", 'error')
        
        # Handle question
        question = request.form.get('question', '').strip()
        if question:
            try:
                # If we have embeddings, include them in the context
                context = ""
                if 'current_embeddings' in session:
                    context = f"Using the context of the uploaded document with embeddings: {session['current_embeddings']}\n\n"
                
                # Get response from Claude with context
                full_question = context + question if context else question
                answer = claude_agent.generate_chat_completion(full_question)
                
                # Check if this question is already in recent_qa
                existing_questions = [(i, qa) for i, qa in enumerate(recent_qa) 
                                   if qa['question'].lower() == question.lower()]
                for i, _ in existing_questions:
                    recent_qa.remove(recent_qa[i])
                
                # Add to recent questions
                recent_qa.appendleft({
                    'question': question,
                    'answer': answer
                })
                
            except Exception as e:
                logger.error(f"Error processing question: {str(e)}")
                answer = f"Error processing your question: {str(e)}"
    
    return render_template('index.html',
                         question=question,
                         answer=answer,
                         recent_qa=list(recent_qa),
                         current_file=current_file)
    question = request.form.get('question', '').strip()
    if question:
            # Get response from Claude
            answer = claude_agent.generate_chat_completion(question)
            
            # Check if this question is already in recent_qa
            # Remove previous instance if it exists
            existing_questions = [(i, qa) for i, qa in enumerate(recent_qa) if qa['question'].lower() == question.lower()]
            for i, _ in existing_questions:
                recent_qa.remove(recent_qa[i])
            
            # Add the new Q&A to the front
            recent_qa.appendleft({
                'question': question,
                'answer': answer
            })
    
    return render_template('index.html',
                         question=question,
                         answer=answer,
                         recent_qa=list(recent_qa))

@app.route('/clear', methods=['GET'])
def clear_chat():
    """Clear the chat history and redirect to home."""
    recent_qa.clear()
    return redirect(url_for('qa_interface'))

@app.route('/browse', methods=['POST'])
@require_api_key
async def browse():
    """Handle single page browsing requests."""
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        result = await heroku_agent.web_browsing_single_page(url)
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
        result = await heroku_agent.web_browsing_multi_page(urls)
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
        result = await heroku_agent.database_get_schema(database_url)
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
        result = await heroku_agent.database_run_query(query, database_url)
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
        result = await heroku_agent.code_exec(code, language)
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
        result = await heroku_agent.dyno_run_command(command)
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
        result = await heroku_agent.pdf_read(pdf_url)
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
        result = await heroku_agent.search_web(query)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ask', methods=['POST'])
def api_ask():
    """API endpoint for questions."""
    data = request.get_json()
    question = data.get('question', '').strip()
    
    if not question:
        return jsonify({'error': 'Question is required'}), 400
        
    answer = claude_agent.generate_chat_completion(question)
    
    return jsonify({
        'question': question,
        'answer': answer
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)