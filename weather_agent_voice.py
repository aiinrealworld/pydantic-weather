import streamlit as st
import asyncio
from httpx import AsyncClient
import os
from dotenv import load_dotenv
from weather_agent import Deps, weather_agent  # Assuming your weather_agent is in weather_agent.py
import speech_recognition as sr  # For Speech Recognition
from gtts import gTTS  # For Text-to-Speech
import io  # For handling audio data
import base64
import time

# Load environment variables
load_dotenv()

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent_message_history" not in st.session_state:
    st.session_state.agent_message_history = []
if "user_input" not in st.session_state:
    st.session_state.user_input = ""

# STT and TTS functions
def recognize_speech():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Say something!")  # Use st.info for messages
        audio = r.listen(source, timeout=5)  # Listen with a timeout
        try:
            text = r.recognize_google(audio)
            st.success(f"You said: {text}")
            return text
        except sr.UnknownValueError:
            st.warning("Could not understand audio")
            return ""
        except sr.RequestError as e:
            st.error(f"Could not request results from Google Speech Recognition service; {e}")
            return ""

def speak(text):
    try:
        tts = gTTS(text=text, lang='en')
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        audio_data = mp3_fp.getvalue()

        b64 = base64.b64encode(audio_data).decode()

        # JavaScript code to create and play audio dynamically
        js_code = f"""
        <script>
        var audio = new Audio("data:audio/mp3;base64,{b64}");
        audio.play();
        </script>
        """
        
        # Add a small delay to ensure Streamlit UI updates before playing audio
        time.sleep(0.5)
        
        # Render JavaScript in Streamlit
        st.components.v1.html(js_code, height=0)

    except Exception as e:
        st.error(f"Error during text-to-speech: {e}")

async def get_weather_response(query: str, message_history=None):
    # [Rest of your weather_agent logic, as before]
    if message_history is None:
        message_history = []

    try:
        with st.spinner("Getting weather information..."):
            async with AsyncClient() as client:
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

# Define the send_message function to handle both text and voice input
def send_message(user_input=None):
    if user_input is None:
        user_input = st.session_state.user_input  # Get from the text input

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        try:
            response, updated_messages = asyncio.run(get_weather_response(
                user_input,
                st.session_state.agent_message_history
            ))
            st.session_state.agent_message_history = updated_messages
            st.session_state.messages.append({"role": "assistant", "content": response})

            speak(response)  # Speak the assistant's response

            st.session_state.user_input = ""  # Clear the text input after processing

        except Exception as e:
            st.error(f"An error occurred: {type(e).__name__}: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

        #st.rerun() #rerun to show the new message

# App Layout and Logic
st.title("🌤️ Weather Voice Assistant")
st.markdown("Ask me about the weather using your voice!")

# Microphone Button
if st.button("Speak"):
    voice_input = recognize_speech()
    if voice_input:
        st.session_state.user_input = voice_input  # Store recognized speech
        send_message(voice_input)  # Process the voice input

st.text_input("Or type your message here:", key="user_input", on_change=send_message)

# Display Chat History
for message in st.session_state.messages:
    role = message["role"]
    content = message["content"]
    if role == "user":
        st.markdown(f'<div style="padding: 10px; border-radius: 5px; background-color: #D0E8FF; color: #000000;"><strong>You:</strong> {content}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="padding: 10px; border-radius: 5px; background-color: #D8D8D8; color: #000000;"><strong>Assistant:</strong> {content}</div>', unsafe_allow_html=True)