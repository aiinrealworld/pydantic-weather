import streamlit as st
import asyncio
from httpx import AsyncClient
import os
from typing import List, Dict, Any
from dotenv import load_dotenv
import json

# Import from your weather_agent.py file in the same directory
from weather_agent import Deps, weather_agent

# Load environment variables
load_dotenv()

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize raw message history for the agent
if "agent_message_history" not in st.session_state:
    st.session_state.agent_message_history = []

# Initialize user input in session state
if "user_input" not in st.session_state:
    st.session_state.user_input = ""


# Configure the Streamlit page
st.set_page_config(
    page_title="Weather Chat Assistant",
    page_icon="🌤️",
    layout="wide"
)

# Custom CSS for better UI
st.markdown("""
    <style>
    .stTextInput > div > div > input {
        background-color: #f0f2f6;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #e6f3ff;
    }
    .assistant-message {
        background-color: #f0f2f6;
    }
    </style>
""", unsafe_allow_html=True)

async def get_weather_response(query: str, message_history=None):
    """Get response from weather agent"""
    if message_history is None:
        message_history = []

    try:
        with st.spinner("Getting weather information..."):
            # Create fresh client for each request
            async with AsyncClient() as client:
                # Create deps with the fresh client
                deps = Deps(
                    client=client,
                    weather_api_key=os.getenv('WEATHER_API_KEY'),
                    geo_api_key=os.getenv('GEO_API_KEY')
                )
                result = await weather_agent.run(query, deps=deps, message_history=message_history)
                return result.data, result.all_messages()
    except Exception as e:
        st.error(f"Error in weather agent: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return f"Error: {str(e)}", message_history

# Main app layout
st.title("🌤️ Weather Chat Assistant")
st.markdown("Ask me about the weather anywhere in the world!")

# Display chat history
for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(f"""
            <div class="chat-message user-message">
                <div><strong>You:</strong> {message["content"]}</div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div class="chat-message assistant-message">
                <div><strong>Assistant:</strong> {message["content"]}</div>
            </div>
        """, unsafe_allow_html=True)

# Message input and send button
def send_message():
    if st.session_state.user_input:
        current_input = st.session_state.user_input

        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": current_input})

        try:
            # Create and use a new event loop for each request
            response, updated_messages = asyncio.run(get_weather_response(
                current_input,
                st.session_state.agent_message_history
            ))

            # Store the updated message history
            st.session_state.agent_message_history = updated_messages

            # Add assistant response to UI chat history
            st.session_state.messages.append({"role": "assistant", "content": response})

            # Clear the input by setting the session state directly
            st.session_state.user_input = ""

        except Exception as e:
            st.error(f"An error occurred: {type(e).__name__}: {str(e)}")
            import traceback
            st.code(traceback.format_exc())


st.text_input("Type your message here", key="user_input", on_change=send_message)
# Add a clear chat button
if st.button("Clear Chat"):
    st.session_state.messages = []
    st.session_state.agent_message_history = []
    st.rerun()