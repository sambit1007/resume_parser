print("--- I AM RUNNING THE NEW, CORRECTED APP.PY FILE ---")
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import os
import json
from werkzeug.utils import secure_filename
import re
from datetime import datetime
import PyPDF2
import docx2txt
import spacy
from collections import Counter
import sqlite3
from pathlib import Path
import shutil
import google.generativeai as genai # <<< NEW
from dotenv import load_dotenv # <<< NEW

# <<< NEW: Load environment variables and configure API >>>
load_dotenv()
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in .env file")
    genai.configure(api_key=api_key)
except Exception as e:
    print(f"Error configuring Google AI: {e}")
    print("Please make sure you have a valid GOOGLE_API_KEY in your .env file.")
    genai = None

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# ... (The rest of your setup code is mostly the same) ...
# Add JSON filter for templates
@app.template_filter('from_json')
def from_json_filter(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    return value

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx'}
DATABASE_FILE = 'resumes.db'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# <<< We can keep spaCy for future use, but it's no longer the primary parser >>>
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("spaCy model 'en_core_web_sm' not found. This is optional for the LLM parser.")
    nlp = None

def init_database():
    schema = """
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            name TEXT,
            email TEXT,
            phone TEXT,
            skills TEXT,
            current_location TEXT,
            education TEXT,
            companies TEXT,
            raw_text TEXT,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ); """
    conn = sqlite3.connect(DATABASE_FILE)
    conn.executescript(schema)
    conn.commit()
    conn.close()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_path):
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = "".join(page.extract_text() for page in reader.pages if page.extract_text())
        return text
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return ""

def extract_text_from_docx(file_path):
    try:
        return docx2txt.process(file_path)
    except Exception as e:
        print(f"Error extracting DOCX text: {e}")
        return ""

# <<< NEW: The LLM Parsing Function >>>
# In app.py, replace the old function with this one

def parse_resume_with_llm(text):
    if not genai:
        print("Google AI SDK not configured. Cannot parse with LLM.")
        return None

    # THE ONLY CHANGE IS ON THE NEXT LINE
    model = genai.GenerativeModel('gemini-1.5-flash-latest') 
    
    prompt = f"""
    You are an expert HR recruitment assistant. Your task is to analyze the following resume text and extract key information in a structured JSON format.

    Please extract the following fields:
    - "name": The full name of the candidate.
    - "email": The primary email address.
    - "phone": The primary phone number.
    - "location": The candidate's current city and country (e.g., "San Francisco, USA").
    - "skills": A list of the top 10-15 most relevant technical and soft skills.
    - "education": A list of strings, where each string is a degree or certification (e.g., "Bachelor of Science in Computer Science, University of California").
    - "companies": A list of company names the candidate has worked for.

    Rules for extraction:
    1. If a field is not found, return null for that field.
    2. For lists (skills, education, companies), return an empty list `[]` if none are found.
    3. The entire output must be a single, valid JSON object enclosed in ```json ... ```.

    Resume Text:
    ---
    {text}
    ---
    """
    
    try:
        response = model.generate_content(prompt)
        # Find the JSON block in the response text
        json_match = re.search(r'```json\n(.*?)\n```', response.text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            parsed_data = json.loads(json_str)
            return parsed_data
        else:
            print("LLM did not return a valid JSON block.")
            return None
    except Exception as e:
        print(f"An error occurred while calling the LLM API: {e}")
        return None

# <<< MODIFIED: Main parsing function now uses the LLM >>>
def parse_resume(file_path, filename):
    text = ""
    if filename.lower().endswith('.pdf'):
        text = extract_text_from_pdf(file_path)
    elif filename.lower().endswith('.docx'):
        text = extract_text_from_docx(file_path)
    
    if not text:
        return None

    # Use the new LLM parser
    llm_data = parse_resume_with_llm(text)

    if not llm_data:
        # Fallback or error handling
        return {
            'filename': filename, 'name': "Error Parsing", 'email': None, 'phone': None,
            'skills': [], 'current_location': None, 'education': [], 'companies': [],
            'raw_text': text[:2000]
        }
    
    # Structure the data for the database
    return {
        'filename': filename,
        'name': llm_data.get('name'),
        'email': llm_data.get('email'),
        'phone': llm_data.get('phone'),
        'skills': llm_data.get('skills', []),
        'current_location': llm_data.get('location'),
        'education': "; ".join(llm_data.get('education', [])),
        'companies': llm_data.get('companies', []),
        'raw_text': text[:2000]
    }

def save_to_database(parsed_data):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO resumes (filename, name, email, phone, skills, current_location, education, companies, raw_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        parsed_data['filename'], parsed_data['name'], parsed_data['email'],
        parsed_data['phone'], json.dumps(parsed_data['skills']),
        parsed_data['current_location'], parsed_data['education'],
        json.dumps(parsed_data['companies']), parsed_data['raw_text']
    ))
    conn.commit()
    conn.close()

# --- All your Flask routes (@app.route(...)) remain exactly the same! ---
# The beauty of this change is that it only affects the "backend" parsing logic.
# The user-facing web pages do not need to be changed at all.

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part in request')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)
            flash('File uploaded, now parsing with AI. This may take a moment...')
            
            parsed_data = parse_resume(filepath, unique_filename)
            
            if parsed_data and parsed_data['name'] != "Error Parsing":
                save_to_database(parsed_data)
                flash(f'Resume "{filename}" parsed successfully with AI!')
                return redirect(url_for('search'))
            else:
                flash('Error parsing resume with AI. Please check the file format or server logs.')
                os.remove(filepath)
                return redirect(request.url)
        else:
            flash('Invalid file format. Only PDF and DOCX are allowed.')
            return redirect(request.url)
    return render_template('upload.html')

@app.route('/search')
def search():
    name_query = request.args.get('name', '').strip()
    skill_filter = request.args.get('skill', '').strip()
    company_query = request.args.get('company', '').strip()
    location_query = request.args.get('location', '').strip()
    results = []
    
    if any([name_query, skill_filter, company_query, location_query]):
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        sql = "SELECT * FROM resumes WHERE 1=1"
        params = []
        if name_query:
            sql += " AND name LIKE ?"
            params.append(f'%{name_query}%')
        if skill_filter:
            sql += " AND skills LIKE ?"
            params.append(f'%"{skill_filter}"%')
        if company_query:
            sql += " AND companies LIKE ?"
            params.append(f'%{company_query}%')
        if location_query:
            sql += " AND current_location LIKE ?"
            params.append(f'%{location_query}%')
        sql += " ORDER BY upload_date DESC"
        cursor.execute(sql, params)
        results = cursor.fetchall()
        conn.close()
    
    return render_template('search.html', results=results, name_query=name_query,
                           skill_filter=skill_filter, company_query=company_query,
                           location_query=location_query)

@app.route('/resume/<int:resume_id>')
def view_resume(resume_id):
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM resumes WHERE id = ?", (resume_id,))
    resume = cursor.fetchone()
    conn.close()
    if resume:
        return render_template('view_resume.html', resume=resume)
    else:
        flash('Resume not found')
        return redirect(url_for('search'))

@app.route('/api/stats')
def api_stats():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM resumes")
    total_resumes = cursor.fetchone()[0]
    cursor.execute("SELECT skills FROM resumes WHERE skills IS NOT NULL AND skills != ''")
    all_skills_json = cursor.fetchall()
    skill_counter = Counter()
    for skill_json in all_skills_json:
        try:
            skills = json.loads(skill_json[0])
            skill_counter.update(skills)
        except (json.JSONDecodeError, TypeError):
            continue
    conn.close()
    return jsonify({
        'total_resumes': total_resumes,
        'top_skills': dict(skill_counter.most_common(10))
    })

if __name__ == '__main__':
    init_database()
    app.run(debug=True, port=8000
            )