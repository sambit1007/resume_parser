##AI-Powered Resume Parser with Google Gemini
This project is a Flask-based web application that intelligently parses resumes using Google's Gemini AI. It extracts key information like contact details, skills, education, and work history from PDF and DOCX files, stores it in a SQLite database, and provides a simple interface for searching and viewing candidates.

###Features
Intelligent Parsing: Leverages the gemini-1.5-flash-latest model via the Google Generative AI API for high-accuracy data extraction.

File Support: Handles resume uploads in both PDF and DOCX formats.

Structured Data Extraction: Pulls key information including:

Name

Email & Phone Number

Location

Skills (as a JSON list)

Education History

Companies Worked For (as a JSON list)

Database Storage: All parsed data is saved to a local SQLite database for persistence.

Search and Filter: A user-friendly web interface to search for candidates by name, skill, company, or location.

Statistics API: A simple /api/stats endpoint that provides the total number of resumes and a count of the top 10 most common skills.

⚙️ How It Works
The application's workflow is centered around the Google Gemini API for parsing:

File Upload: A user uploads a resume through the web interface.

Text Extraction: The application uses PyPDF2 or docx2txt to extract the raw text from the uploaded file.

AI-Powered Parsing: The raw text is sent to the Google Gemini API with a carefully crafted prompt, asking it to return a structured JSON object containing the desired information.

Data Storage: The application parses the JSON response from the AI and stores the extracted data in the resumes.db SQLite database.

Web Interface: Users can then interact with the stored data through the search and view pages.

🚀 Getting Started
Follow these instructions to get the project running on your local machine.

Prerequisites
Python 3.8+

A Google AI API Key. You can get one from Google AI Studio.

Installation
Clone the repository:

Bash

git clone https://github.com/CaptJack05/resumeParser.git
cd resumeParser
Create and activate a virtual environment (recommended):

Bash

# For macOS/Linux
python3 -m venv venv
source venv/bin/activate

# For Windows
python -m venv venv
.\venv\Scripts\activate
Install the required dependencies:

Bash

pip install -r requirements.txt
Set up your environment variables:
Create a new file named .env in the root of the project directory and add your Google AI API key to it:

GOOGLE_API_KEY="your_api_key_here"
Run the application:

Bash

python app.py
The application will initialize the SQLite database automatically and will be available at http://127.0.0.1:8000.

📋 Requirements File
For your convenience, here is the content for your requirements.txt file:

Plaintext

Flask
google-generative-ai
python-dotenv
PyPDF2
docx2txt
werkzeug
spacy
(Note: spaCy is included as it's still imported in app.py, though it is not the primary parser.)

📂 Project Structure
resumeParser/
│
├── app.py                # Main Flask application logic
├── resumes.db            # SQLite database file
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (contains API key)
├── README.md             # This file
│
├── templates/            # HTML templates for the web interface
│   ├── index.html
│   ├── search.html
│   └── view_resume.html
│
└── uploads/              # Directory where uploaded resumes are stored
⚖️ License
This project is licensed under the MIT License.

👤 Author
sambit rout

GitHub Repository:-"https://github.com/sambit1007/resume_parser"
