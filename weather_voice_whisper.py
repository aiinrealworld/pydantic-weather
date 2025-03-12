import streamlit as st
import asyncio
from httpx import AsyncClient
import os
from dotenv import load_dotenv
from weather_agent import Deps, weather_agent
import speech_recognition as sr
import io
from typing import List
import whisper
import numpy as np
import pyttsx3
import threading
import queue

# Load environment variables
load_dotenv()

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent_message_history" not in st.session_state:
    st.session_state.agent_message_history = []
if "user_input" not in st.session_state:
    st.session_state.user_input = ""
if "tts_queue" not in st.session_state:
    st.session_state.tts_queue = queue.Queue()
if "tts_thread_running" not in st.session_state:
    st.session_state.tts_thread_running = False

# Load the Whisper model
@st.cache_resource
def load_model():
    model = whisper.load_model("base")
    return model

whisper_model = load_model()

# Global TTS worker thread
def tts_worker():
    """Background thread for TTS processing"""
    engine = pyttsx3.init()
    st.session_state.tts_thread_running = True
    
    while True:
        try:
            # Get text from queue, blocks until item is available
            text = st.session_state.tts_queue.get(timeout=1)
            if text == "STOP":  # Special signal to stop the thread
                break
                
            # Process TTS
            engine.say(text)
            engine.runAndWait()
            
            # Mark task as done
            st.session_state.tts_queue.task_done()
            
        except queue.Empty:
            # No items in queue, continue waiting
            continue
        except Exception as e:
            st.error(f"TTS error: {str(e)}")
            st.session_state.tts_queue.task_done()  # Mark as done even on error
            
    # Clean up
    st.session_state.tts_thread_running = False

# Start TTS thread if not already running
def ensure_tts_thread():
    if not st.session_state.tts_thread_running:
        thread = threading.Thread(target=tts_worker)
        thread.daemon = True
        thread.start()

# Speak function now adds text to the queue
def speak(text):
    """Add text to TTS queue for processing"""
    ensure_tts_thread()
    st.session_state.tts_queue.put(text)

# STT function
def recognize_speech_whisper():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Say something!")
        audio = r.listen(source, timeout=5)
        try:
            # Convert audio data to numpy array
            raw_audio = audio.get_raw_data()
            np_audio = np.frombuffer(raw_audio, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Get sample rate
            sample_rate = audio.sample_rate
            
            # Resample if needed (Whisper expects 16kHz)
            if sample_rate != 16000:
                st.info(f"Resampling audio from {sample_rate}Hz to 16000Hz")
                factor = 16000 / sample_rate
                new_length = int(len(np_audio) * factor)
                indices = np.round(np.linspace(0, len(np_audio) - 1, new_length)).astype(int)
                np_audio = np_audio[indices]
            
            # Transcribe audio
            result = whisper_model.transcribe(np_audio, fp16=False)
            text = result["text"]

            st.success(f"You said: {text}")
            return text
        except sr.UnknownValueError:
            st.warning("Could not understand audio")
            return ""
        except sr.RequestError as e:
            st.error(f"Could not request results from speech recognition service; {e}")
            return ""
        except Exception as e:
            st.error(f"Error processing audio: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
            return ""

async def get_weather_response(query: str, message_history=None):
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
        user_input = st.session_state.user_input

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        try:
            response, updated_messages = asyncio.run(get_weather_response(
                user_input,
                st.session_state.agent_message_history
            ))
            st.session_state.agent_message_history = updated_messages
            st.session_state.messages.append({"role": "assistant", "content": response})

            # Speak the response
            speak(response)

            st.session_state.user_input = ""  # Clear input

        except Exception as e:
            st.error(f"An error occurred: {type(e).__name__}: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

        st.rerun()  # Show new message

# App Layout and Logic
st.title("🌤️ Weather Voice Assistant")
st.markdown("Ask me about the weather using your voice!")

# Microphone Button
if st.button("Speak"):
    voice_input = recognize_speech_whisper()
    if voice_input:
        st.session_state.user_input = voice_input
        send_message(voice_input)

st.text_input("Or type your message here:", key="user_input", on_change=send_message)

# Display Chat History
for message in st.session_state.messages:
    role = message["role"]
    content = message["content"]
    if role == "user":
        st.markdown(f'<div style="padding: 10px; border-radius: 5px; background-color: #E6F3FF;"><strong>You:</strong> {content}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="padding: 10px; border-radius: 5px; background-color: #F0F2F6;"><strong>Assistant:</strong> {content}</div>', unsafe_allow_html=True)

# Clear Chat Button
if st.button("Clear Chat"):
    # Stop TTS thread before clearing everything
    if st.session_state.tts_thread_running:
        st.session_state.tts_queue.put("STOP")
        
    st.session_state.messages = []
    st.session_state.agent_message_history = []
    st.session_state.user_input = ""
    
    # Reset TTS queue
    st.session_state.tts_queue = queue.Queue()
    st.session_state.tts_thread_running = False
    
    st.rerun()

# Clean shutdown
def handle_shutdown():
    if st.session_state.tts_thread_running:
        st.session_state.tts_queue.put("STOP")

# Register shutdown handler
try:
    st.on_session_end(handle_shutdown)
except:
    # If not available, we'll rely on daemon thread nature for cleanup
    pass