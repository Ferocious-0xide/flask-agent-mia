import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import requests
from functools import wraps
import json
from typing import Dict, Any, List
import logging
import tempfile
from collections import deque
import docx
import PyPDF2
import io
import base64

# Initialize Flask first
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Now this will work as app is defined

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup uploads folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Environment variables
ENV_VARS = {
    "INFERENCE_URL": os.getenv('INFERENCE_URL'),
    "INFERENCE_KEY": os.getenv('INFERENCE_KEY'),
    "INFERENCE_MODEL_ID": os.getenv('INFERENCE_MODEL_ID'),
    "HEROKU_API_KEY": os.getenv('HEROKU_API_KEY'),
    "HEROKU_APP_NAME": os.getenv('HEROKU_APP_NAME'),
    "APP_API_KEY": os.getenv('APP_API_KEY'),
    "EMBEDDING_URL": os.getenv('EMBEDDING_URL'),
    "EMBEDDING_KEY": os.getenv('EMBEDDING_KEY'),
    "EMBEDDING_MODEL_ID": os.getenv('EMBEDDING_MODEL_ID')
}

# Store recent Q&As in memory
recent_qa = deque(maxlen=5)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

class ClaudeAgent:
    def __init__(self, inference_url, inference_key, model_id):
        self.inference_url = inference_url
        self.headers = {
            "Authorization": f"Bearer {inference_key}",
            "Content-Type": "application/json"
        }
        self.model_id = model_id

    def generate_chat_completion(self, question: str) -> str:
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

class CohereAgent:
    def __init__(self, embedding_url, embedding_key, model_id):
        self.embedding_url = embedding_url
        self.model_id = model_id
        self.headers = {
            "Authorization": f"Bearer {embedding_key}",
            "Content-Type": "application/json"
        }

    def get_embeddings(self, texts: List[str], input_type: str = "search_document") -> Dict:
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

# Initialize the agents
claude_agent = ClaudeAgent(
    ENV_VARS["INFERENCE_URL"],
    ENV_VARS["INFERENCE_KEY"],
    ENV_VARS["INFERENCE_MODEL_ID"]
)

cohere_agent = CohereAgent(
    ENV_VARS["EMBEDDING_URL"],
    ENV_VARS["EMBEDDING_KEY"],
    ENV_VARS["EMBEDDING_MODEL_ID"]
)

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

@app.route('/clear', methods=['GET'])
def clear_chat():
    """Clear the chat history and redirect to home."""
    recent_qa.clear()
    return redirect(url_for('qa_interface'))

@app.route('/remove-file', methods=['POST'])
def remove_file():
    """Remove the current uploaded file."""
    if 'current_file' in session:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], session['current_file'])
        if os.path.exists(file_path):
            os.remove(file_path)
        session.pop('current_file', None)
    return '', 204

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)