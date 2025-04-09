# AI Chatbot & Image Generator

A Streamlit web application that combines an AI chatbot powered by GPT-3.5 and an image generator using DALL-E.

## Features

- Interactive chat interface with GPT-3.5
- Real-time streaming responses
- Image generation using DALL-E
- Secure API key management
- Modern and responsive UI

## Setup

1. Clone this repository
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the root directory and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```
   Or you can enter it directly in the application's sidebar.

## Usage

1. Run the application:
   ```bash
   streamlit run app.py
   ```
2. Open your web browser and navigate to the URL shown in the terminal (usually http://localhost:8501)
3. Enter your OpenAI API key in the sidebar if you haven't set it in the .env file
4. Use the chat interface to ask questions or switch to the Image Generation tab to create images

## Requirements

- Python 3.7+
- OpenAI API key
- Internet connection

## Note

This application uses OpenAI's API, which may incur costs based on your usage. Please refer to OpenAI's pricing page for more information. 