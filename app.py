import streamlit as st
import requests
from PIL import Image
import io
import os
from dotenv import load_dotenv
import time
from duckduckgo_search import DDGS
import uuid
import smtplib
from email.mime.text import MIMEText
from streamlit_lottie import st_lottie
import json
import wikipedia

# Helper functions
def get_wikipedia_content(topic):
    """Fetch content from Wikipedia"""
    try:
        # Search for the topic
        search_results = wikipedia.search(topic)
        if not search_results:
            return None
        
        # Get the first result
        page = wikipedia.page(search_results[0])
        
        # Get the summary
        summary = page.summary
        
        # Get the main content
        content = page.content
        
        return {
            "title": page.title,
            "summary": summary,
            "content": content,
            "url": page.url
        }
    except Exception as e:
        st.error(f"Error fetching from Wikipedia: {str(e)}")
        return None

def create_assistant_prompt(user_query, search_results=None):
    """Create a well-structured prompt for GPT-like responses"""
    if "essay" in user_query.lower() or "write about" in user_query.lower():
        # Extract the topic from the query
        topic = user_query.lower().replace("write essay on", "").replace("essay on", "").replace("write about", "").strip()
        
        # Get Wikipedia content
        wiki_content = get_wikipedia_content(topic)
        
        if wiki_content:
            return f"""Based on Wikipedia information about {topic}, provide a comprehensive overview. Include:

1. Introduction: {wiki_content['summary']}

2. Main Content: Present the key information from the Wikipedia article in a clear, organized manner.

3. Additional Details: Include relevant facts and explanations from the article.

Source: {wiki_content['url']}"""
        else:
            return f"""Please provide a detailed and informative response about:
{user_query}

Include relevant facts and explanations."""
    elif "story" in user_query.lower():
        base_prompt = """Create an engaging story about:
{query}

Make it creative and entertaining with a clear plot."""
    elif "song" in user_query.lower():
        base_prompt = """Write song lyrics about:
{query}

Include verses and a chorus."""
    else:
        # For general queries, try to get Wikipedia content first
        wiki_content = get_wikipedia_content(user_query)
        if wiki_content:
            return f"""Based on Wikipedia information about {user_query}, provide a comprehensive overview. Include:

1. Introduction: {wiki_content['summary']}

2. Main Content: Present the key information from the Wikipedia article in a clear, organized manner.

3. Additional Details: Include relevant facts and explanations from the article.

Source: {wiki_content['url']}"""
        else:
            return f"""Please provide a detailed and informative response about:
{user_query}

Include relevant facts and explanations."""
    
    if search_results:
        context = "\n".join([
            f"Reference Information:\n{result['body']}\n"
            for i, result in enumerate(search_results)
        ])
        base_prompt += f"""

Using the following reference information, create your response:
{context}

Please write a well-structured response incorporating this information:"""
    
    return base_prompt.format(query=user_query)

def is_greeting(text):
    """Check if the input is a greeting"""
    greetings = ['hi', 'hello', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening', 'hi there']
    return text.lower().strip() in greetings

def get_greeting_response():
    """Return a friendly greeting response"""
    import random
    responses = [
        "Hello! How can I help you today? 😊",
        "Hi there! I'm here to assist you. What's on your mind?",
        "Hey! Great to see you. What would you like to know?",
        "Greetings! I'm ready to help you with any questions.",
        "Hello! I'm your AI assistant. How may I help you today?"
    ]
    return random.choice(responses)

def should_use_web_search(text):
    """Determine if web search is needed"""
    # Don't search for greetings
    if is_greeting(text):
        return False
    
    # Search for essays, factual queries, and explanations
    return True

def make_api_request(url, payload, max_retries=3):
    """Make API request with retries"""
    headers = {"Authorization": f"Bearer {st.session_state.hf_token}"}
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 503:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
            # Check for model loading
            if response.status_code == 200 and isinstance(response.json(), dict) and response.json().get("error") == "Model is loading":
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
            return response
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise e
    return None

def search_web(query, num_results=5):
    """Search the web using DuckDuckGo"""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=num_results))
        return results
    except Exception as e:
        st.error(f"Search error: {str(e)}")
        return []

def format_response(response_text):
    """Simple response formatting"""
    return response_text.strip()

def save_image(image_bytes):
    """Save image bytes to a temporary file and return the path"""
    import tempfile
    import os
    
    # Create a temporary file with .png extension
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"lumo_art_{int(time.time())}.png")
    
    # Save the image
    with open(temp_path, "wb") as f:
        f.write(image_bytes)
    
    return temp_path

# Load environment variables
load_dotenv()

def create_new_chat():
    """Create a new chat and return its ID"""
    chat_id = str(uuid.uuid4())
    st.session_state.current_chat = chat_id
    st.session_state.messages = []
    return chat_id

# Set page config
st.set_page_config(
    page_title="Lumo.ai",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = {}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = str(uuid.uuid4())
if "hf_token" not in st.session_state:
    st.session_state.hf_token = os.getenv("HUGGINGFACE_TOKEN")

# Add CSS for modern styling
st.markdown("""
<style>
    /* Main content gradient background */
    .main .block-container {
        background: linear-gradient(135deg, #1a1f2e 0%, #2d3748 50%, #374151 100%) !important;
        min-height: 100vh !important;
        border-radius: 20px !important;
        padding: 2rem !important;
        margin: 1rem !important;
    }

    /* Chat message styling */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        border-radius: 16px !important;
        padding: 1rem !important;
        margin: 0.5rem 0 !important;
    }

    /* Input container styling */
    .stChatInputContainer {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        border-radius: 20px !important;
        padding: 0.5rem 1rem !important;
        margin-top: 1rem !important;
    }

    /* Input field styling */
    .stChatInputContainer textarea {
        border-radius: 12px !important;
        padding: 10px 15px !important;
    }

    /* Button styling */
    button {
        border-radius: 12px !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.3s ease !important;
    }

    /* Tabs styling */
    .stTabs {
        background: transparent !important;
    }

    .stTab {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        margin: 0 0.25rem !important;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] .block-container {
        background: linear-gradient(180deg, #1a1f2e, #2d3748) !important;
        border-radius: 0 20px 20px 0 !important;
    }

    /* Sidebar buttons */
    [data-testid="stSidebar"] button {
        border-radius: 12px !important;
        margin: 0.25rem 0 !important;
    }

    /* Text color */
    .main .block-container {
        color: #ffffff !important;
    }

    /* Settings and expander styling */
    .streamlit-expanderHeader {
        border-radius: 12px !important;
        background: rgba(255, 255, 255, 0.05) !important;
    }

    /* Token warning styling */
    .token-warning {
        background: rgba(255, 200, 0, 0.1) !important;
        border: 1px solid rgba(255, 200, 0, 0.2) !important;
        border-radius: 12px !important;
        padding: 1rem !important;
        margin: 1rem 0 !important;
    }

    /* Footer styling */
    footer {
        border-radius: 20px !important;
        margin-top: 2rem !important;
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
    }
</style>
""", unsafe_allow_html=True)

# Update sidebar with modern styling
with st.sidebar:
    st.markdown('<div class="sidebar-header">💬 Chat History</div>', unsafe_allow_html=True)
    
    # New chat button with modern styling
    if st.button("+ New Chat", key="new_chat_btn", use_container_width=True):
        create_new_chat()
        st.rerun()
    
    st.markdown("<div style='height: 1px; background-color: var(--border-color); margin: 1rem 0;'></div>", unsafe_allow_html=True)
    
    # Display chat history with modern styling
    for chat_id, messages in st.session_state.chat_history.items():
        if st.button(
            f"💭 Chat {chat_id[:8]}...",
            key=chat_id,
            use_container_width=True,
            help="Click to load this chat"
        ):
            st.session_state.current_chat = chat_id
            st.session_state.messages = messages
            st.rerun()
    
    st.markdown("<div style='height: 1px; background-color: var(--border-color); margin: 1rem 0;'></div>", unsafe_allow_html=True)
    
    # Settings section
    st.markdown('<div class="sidebar-header">⚙️ Settings</div>', unsafe_allow_html=True)
    with st.expander("API Token"):
        st.markdown("""
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
                <span style="
                    color: #000000;
                    background-color: #E2E8F0;
                    padding: 4px 8px;
                    border-radius: 6px;
                    font-weight: 500;
                ">↓</span>
                <span style="color: #FF4444; font-weight: 500;">Enter your token below</span>
            </div>
        """, unsafe_allow_html=True)
        hf_token = st.text_input(
            "Enter your Hugging Face Token",
            type="password",
            value=st.session_state.hf_token or "",
            help="Required for AI functionality"
        )
        if hf_token and hf_token != st.session_state.hf_token:
            st.session_state.hf_token = hf_token
            st.success("Token updated!")

# Check if token is set
if not st.session_state.hf_token:
    st.markdown(
        '<div class="token-warning">'
        '<span>⚠️</span>'
        '<span>Please enter your Hugging Face token in the sidebar</span>'
        '<span style="color: #000000;">↗</span>'
        '</div>',
        unsafe_allow_html=True
    )
    st.stop()

# Create tabs
tab1, tab2 = st.tabs(["💬 Chat", "🎨 Create"])

# Chat tab
with tab1:
    # Container for messages with scrolling
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    
    # Message container
    st.markdown('<div class="message-container">', unsafe_allow_html=True)
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Fixed chat input at the bottom
    st.markdown('<div class="chat-input-container">', unsafe_allow_html=True)
    if prompt := st.chat_input("Message your AI assistant..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Immediately display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Process and display assistant response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            try:
                if is_greeting(prompt):
                    response_text = get_greeting_response()
                    message_placeholder.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                else:
                    search_results = search_web(prompt) if should_use_web_search(prompt) else None
                    enhanced_prompt = create_assistant_prompt(prompt, search_results)
                    
                    with st.spinner("Thinking..."):
                        # Try different models in order of preference (faster models first)
                        models = [
                            "facebook/opt-350m",  # Fastest model
                            "gpt2",  # Quick response
                            "EleutherAI/gpt-neo-125M",  # Lightweight
                            "google/flan-t5-small"  # Efficient for short responses
                        ]
                        
                        response = None
                        response_text = ""
                        
                        for model in models:
                            try:
                                API_URL = f"https://api-inference.huggingface.co/models/{model}"
                                # Add parameters for faster generation
                                payload = {
                                    "inputs": enhanced_prompt,
                                    "parameters": {
                                        "max_length": 500,  # Limit response length
                                        "num_return_sequences": 1,
                                        "temperature": 0.7,  # Balance between creativity and speed
                                        "top_p": 0.9,
                                        "do_sample": True
                                    }
                                }
                                response = make_api_request(API_URL, payload)
                                if response and response.status_code == 200:
                                    response_json = response.json()
                                    if isinstance(response_json, list) and len(response_json) > 0:
                                        response_text = response_json[0].get("generated_text", "").strip()
                                        if response_text and len(response_text) > 20:  # Lower threshold for faster responses
                                            break
                            except Exception:
                                continue
                        
                        if response and response.status_code == 200 and response_text:
                            formatted_response = format_response(response_text)
                            message_placeholder.markdown(formatted_response)
                            st.session_state.messages.append({"role": "assistant", "content": formatted_response})
                        else:
                            message_placeholder.error("I apologize, but I'm having trouble generating a response right now. Please try again in a moment.")
                
                # Save chat history
                st.session_state.chat_history[st.session_state.current_chat] = st.session_state.messages
            
            except Exception as e:
                message_placeholder.error(f"I apologize, but an error occurred. Please try again. Error details: {str(e)}")
    st.markdown('</div>', unsafe_allow_html=True)

# Image Generation tab
with tab2:
    st.markdown("### Create AI Art")
    
    # Check for API token first
    if not st.session_state.hf_token:
        st.error("Please enter your Hugging Face API token in the sidebar settings first.")
        with st.expander("How to get a Hugging Face API token"):
            st.markdown("""
            1. Go to [Hugging Face](https://huggingface.co/)
            2. Sign up or log in to your account
            3. Go to Settings > Access Tokens
            4. Create a new token with write access
            5. Copy the token and paste it in the sidebar settings
            """)
    else:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            image_prompt = st.text_input(
                "Describe your image",
                placeholder="A magical forest with glowing butterflies..."
            )
        
        with col2:
            if st.button("🎨 Generate", use_container_width=True):
                if not image_prompt:
                    st.warning("Please enter a description")
                else:
                    try:
                        with st.spinner("Creating your masterpiece..."):
                            # Try different models in order of preference
                            models = [
                                "stabilityai/stable-diffusion-2-1",
                                "CompVis/stable-diffusion-v1-4",
                                "runwayml/stable-diffusion-v1-5"
                            ]
                            
                            response = None
                            error_messages = []
                            image_bytes = None
                            
                            for model in models:
                                try:
                                    API_URL = f"https://api-inference.huggingface.co/models/{model}"
                                    headers = {"Authorization": f"Bearer {st.session_state.hf_token}"}
                                    
                                    payload = {
                                        "inputs": image_prompt,
                                        "parameters": {
                                            "num_inference_steps": 30,
                                            "guidance_scale": 7.5,
                                            "width": 512,
                                            "height": 512,
                                            "negative_prompt": "blurry, distorted, low quality, bad anatomy",
                                            "num_images_per_prompt": 1
                                        }
                                    }
                                    
                                    response = requests.post(
                                        API_URL,
                                        headers=headers,
                                        json=payload,
                                        timeout=30
                                    )
                                    
                                    if response.status_code == 200:
                                        image_bytes = response.content
                                        try:
                                            image = Image.open(io.BytesIO(image_bytes))
                                            # Create container for image and download button
                                            st.markdown('<div class="image-container">', unsafe_allow_html=True)
                                            st.image(image, caption=image_prompt, use_container_width=True)
                                            
                                            # Save image and create download button
                                            if image_bytes:
                                                temp_path = save_image(image_bytes)
                                                with open(temp_path, "rb") as f:
                                                    btn = st.download_button(
                                                        label="⬇ Download Image",
                                                        data=f,
                                                        file_name=f"lumo_art_{int(time.time())}.png",
                                                        mime="image/png",
                                                        use_container_width=True
                                                    )
                                            st.markdown('</div>', unsafe_allow_html=True)
                                            break
                                        except Exception as e:
                                            error_messages.append(f"Failed to process image from {model}: {str(e)}")
                                            continue
                                    elif response.status_code == 401:
                                        st.error("Invalid API token. Please check your Hugging Face API token in the sidebar settings.")
                                        break
                                    else:
                                        error_messages.append(f"Model {model} failed with status {response.status_code}")
                                        continue
                                        
                                except requests.exceptions.Timeout:
                                    error_messages.append(f"Model {model} timed out")
                                    continue
                                except Exception as e:
                                    error_messages.append(f"Model {model}: {str(e)}")
                                    continue
                            
                            if not response or response.status_code != 200:
                                st.error("Failed to generate image. Please try again.")
                                with st.expander("Error Details"):
                                    for error in error_messages:
                                        st.error(error)
                                    st.info("Tips:\n1. Try a simpler prompt\n2. Check your API token\n3. Try again in a few moments")
                                        
                    except Exception as e:
                        st.error(f"An unexpected error occurred: {str(e)}")
                        st.info("Please make sure your API token is valid and try again.")

# Footer
st.markdown("---")
st.markdown("""
<footer>
    <p>LUMO.AI - MADE WITH ❤️ BY M.SUBHAN</p>
</footer>
""", unsafe_allow_html=True) 