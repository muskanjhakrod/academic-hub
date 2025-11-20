# routes/chat.py (New File) or integrated into posts.py
import os
from flask import Blueprint, request, jsonify, session
from google import genai
from google.genai import types

# Assuming you initialize 'chat' blueprint elsewhere. If not, use 'app.route'
chat_bp = Blueprint('chat', __name__) 

# Initialize the Gemini Client
try:
    # Client will automatically look for the GEMINI_API_KEY environment variable
    client = genai.Client()
except Exception as e:
    print(f"Error initializing Gemini Client: {e}")
    client = None

# We use a simple in-memory structure to hold conversation history per user session
# In a real app, you would use a database or a proper session object for persistence.
session_history = {}

@chat_bp.route('/api/chat', methods=['POST'])
def chat_mentor():
    if not client:
        return jsonify({'error': 'Gemini Client not initialized.'}), 500

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User not logged in.'}), 401

    data = request.get_json()
    user_message = data.get('message')

    if not user_message:
        return jsonify({'error': 'No message provided.'}), 400

    # 1. Get or create the chat session for this user
    if user_id not in session_history:
        # Configuration for the mentor persona
        config = types.GenerateContentConfig(
            system_instruction="You are 'Academic Mentor.' Your primary goal is to provide **brief, actionable, and highly concise** advice for academic topics and platform use. Keep all responses to the essential information."
            ,max_output_tokens=250
        )
        # Start a new chat session with the configuration and a model (e.g., gemini-2.5-flash)
        chat = client.chats.create(
            model='gemini-2.5-flash', 
            config=config
        )
        session_history[user_id] = chat
    
    chat = session_history[user_id]

    try:
        # 2. Send the message to the model
        response = chat.send_message(user_message)
        
        # 3. Return the model's response
        return jsonify({'response': response.text})

    except Exception as e:
        return jsonify({'error': f'API Error: {e}'}), 500