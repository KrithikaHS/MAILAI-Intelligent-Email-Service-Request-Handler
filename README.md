# MailAI – Intelligent Email-Based Service Request Handler

MailAI is an AI-powered email auto-responder designed to help internal support teams respond faster, smarter, and with less manual effort. Built using Retrieval-Augmented Generation (RAG), it classifies, retrieves, and replies to service request emails automatically.

## Tech Stack

- **Frontend**: Chrome Extension (HTML, JavaScript)
- **Backend**: Python, Flask
- **AI/ML**: OpenAI GPT, SentenceTransformers, FAISS, LangChain

## Demo

[Watch Pitch Video](https://www.youtube.com/watch?v=oTZ-wOFbeWU)

## How It Works

1. Fetches unseen support request emails.
2. Filters out non-reply or unauthorized domains.
3. Classifies the intent using zero-shot learning.
4. Retrieves relevant KB documents via semantic search.
5. Generates personalized replies using GPT.
6. Sends response via email or escalates to human.

## Setup Instructions

### Clone the Repo
bash
```
git clone https://github.com/yourusername/MailAI.git
cd MailAI

pip install -r requirements.txt
```
Create a .env file in the project root and add the following:

OPENAI_API_KEY=your_openai_key
EMAIL_CREDENTIALS=your_email_credentials

Run the Server
bash
```python app.py```

Build Chrome Extension
-Open Chrome and go to chrome://extensions/.
-Enable Developer Mode.
-Click Load Unpacked and select the extension folder.
