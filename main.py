
import os
import asyncio
import uuid
import nest_asyncio # For allowing nested asyncio event loops
from typing import Dict, List, Any
import streamlit as st
import tempfile # For temporary audio files

# Apply nest_asyncio to allow asyncio.run() to be called from a running event loop
nest_asyncio.apply()

# Import components from your refactored files
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, AIMessage
# from functools import partial # No longer needed for smart_schedule_meeting

# Import your tool functions and Pydantic schemas
from tools import (
    get_current_datetime_with_timezone,
    parse_natural_datetime,
    smart_schedule_meeting, # smart_schedule_meeting now uses module-level api_resource
    GetCurrentDatetimeInput,
    ParseNaturalDatetimeInput,
    ScheduleMeetingInput
)

# Import the API resource initialization from its module
# The api_resource is initialized here when this module is imported
from google_calendar_api import api_resource # Import the already initialized api_resource

# Import voice I/O functions and related libraries
import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play # Keep play for direct use if needed, but st.audio is preferred for web
from dotenv import load_dotenv
load_dotenv()
# --- Streamlit App Setup ---
st.set_page_config(page_title="Voice Meeting Scheduler", layout="centered")
st.title("🗣️ Voice Meeting Scheduler Bot")

# --- Initialize Session State ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.chat_history.append(AIMessage(content="Welcome! I can help schedule meetings. Say 'new' to start a new session or 'load' to enter a session ID."))
    st.session_state.current_session_id = None # To hold the ID the user is working with
# The api_resource is now initialized directly from google_calendar_api.py on module import
# No need to re-initialize it in session state unless you want a per-session API instance.
# For simplicity, we assume one global api_resource for the app's lifetime.


# --- LangChain Agent Setup (initialized once per session) ---
if "agent_executor" not in st.session_state:
    # Set your Google API Key
    # It's recommended to load this from an environment variable or a .env file
    # os.environ["GOOGLE_API_KEY"] = "YOUR_GEMINI_API_KEY" # Uncomment and replace if not using env vars

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)

    tools = [
        StructuredTool.from_function(
            func=get_current_datetime_with_timezone,
            name="GetCurrentDatetime",
            description="Returns the current date and time including the timezone in ISO format (e.g., '2025-07-17T10:00:00+05:30').",
            args_schema=GetCurrentDatetimeInput,
        ),
        StructuredTool.from_function(
            func=parse_natural_datetime,
            name="ParseNaturalDatetime",
            description="Converts natural language like 'tomorrow at 10 AM' or 'next Friday 3pm' into a precise datetime in ISO format (yyyy-mm-ddThh:mm:ss).",
            args_schema=ParseNaturalDatetimeInput,
        ),
        StructuredTool.from_function(
            func=smart_schedule_meeting, # Directly use smart_schedule_meeting, it now accesses api_resource globally
            name="ScheduleMeeting",
            description="Smartly schedules a meeting. If the preferred time is busy, it suggests the next available 30-min slot.",
            args_schema=ScheduleMeetingInput,
        ),
    ]

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful AI assistant that can schedule meetings and understand natural language dates and times. Use the provided tools to assist the user. If you need more information to schedule a meeting (e.g., summary, start time, end time, duration), please ask the user clarifying questions. Always try to provide a clear summary of the scheduled meeting or suggested time."),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    st.session_state.agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# --- Voice I/O Functions for Streamlit ---
r = sr.Recognizer()

async def get_voice_input_streamlit() -> str:
    """Captures voice input from the microphone and converts it to text for Streamlit."""
    with st.spinner("Listening... Say something!"):
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source)
            try:
                audio = await asyncio.to_thread(r.listen, source, timeout=10, phrase_time_limit=10)
                st.info("Recognizing...")
                text = await asyncio.to_thread(r.recognize_google, audio)
                return text
            except sr.WaitTimeoutError:
                st.warning("No speech detected.")
                return ""
            except sr.UnknownValueError:
                st.warning("Could not understand audio.")
                return ""
            except sr.RequestError as e:
                st.error(f"Could not request results from Google Speech Recognition service; {e}")
                return ""
            except Exception as e:
                st.error(f"An unexpected error occurred during voice input: {e}")
                return ""

async def speak_text_streamlit(text: str):
    """Converts text to speech and plays it using gTTS and pydub for Streamlit."""
    if not text:
        return
    
    with st.spinner("Bot is speaking..."):
        try:
            tts = gTTS(text=text, lang='en')
            
            # Use tempfile to create a temporary audio file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                audio_file_path = fp.name
                await asyncio.to_thread(tts.save, audio_file_path)
            
            # Load and play using pydub, then display with st.audio
            audio_segment = AudioSegment.from_file(audio_file_path, format="mp3")
            
            # Export to a BytesIO object for st.audio
            from io import BytesIO
            audio_bytes_io = BytesIO()
            audio_segment.export(audio_bytes_io, format="mp3")
            audio_bytes_io.seek(0) # Rewind to the beginning
            
            st.audio(audio_bytes_io.read(), format="audio/mp3", start_time=0)
            
            os.remove(audio_file_path) # Clean up the temporary file
        except Exception as e:
            st.error(f"Error during text-to-speech or playback: {e}")
            st.warning("Please ensure FFmpeg is installed and accessible in your system's PATH for MP3 playback with pydub.")

# --- Chat Processing Function ---
async def process_chat_message(user_input: str):
    st.session_state.chat_history.append(HumanMessage(content=user_input))

    with st.spinner("Bot is thinking..."):
        try:
            # Define a synchronous wrapper function to run the agent's synchronous invoke method
            def sync_invoke_agent(agent_exec: AgentExecutor, input_data: str, chat_history_data: List[Any]) -> Dict[str, Any]:
                # This function runs in a separate thread.
                # It calls the synchronous 'invoke' method of the AgentExecutor.
                return agent_exec.invoke({
                    "input": input_data,
                    "chat_history": chat_history_data
                })

            # Use asyncio.to_thread to run the synchronous agent invocation in a separate thread.
            # This avoids nested asyncio.run() calls and potential loop conflicts.
            result = await asyncio.to_thread(
                sync_invoke_agent,
                st.session_state.agent_executor, # Pass the agent_executor instance
                user_input,
                st.session_state.chat_history
            )

            ai_response = result["output"]
            st.session_state.chat_history.append(AIMessage(content=ai_response))
            await speak_text_streamlit(ai_response) # Speak the response
        except Exception as e:
            st.error(f"An error occurred: {e}. Please try again.")
            st.session_state.chat_history.append(AIMessage(content=f"I'm sorry, an error occurred: {e}. Please try again."))
            await speak_text_streamlit("I'm sorry, an error occurred. Please try again.")

# --- Streamlit UI Layout ---

# Display chat messages
for message in st.session_state.chat_history:
    if isinstance(message, HumanMessage):
        with st.chat_message("user"):
            st.markdown(message.content)
    else:
        with st.chat_message("assistant"):
            st.markdown(message.content)

# Input area for text messages
user_text_input = st.chat_input("Type your message here...", key="text_input")
if user_text_input:
    asyncio.run(process_chat_message(user_text_input))

# Buttons for voice input and session management
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    if st.button("Speak", key="speak_button"):
        st.session_state.text_input_value = "" # Clear text input when speaking
        user_voice_input = asyncio.run(get_voice_input_streamlit())
        if user_voice_input:
            asyncio.run(process_chat_message(user_voice_input))

with col2:
    if st.button("New Session", key="new_session_button"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.chat_history = [AIMessage(content=f"New session started. Your ID is: {st.session_state.session_id}")]
        st.session_state.current_session_id = None # Reset current session ID
        st.rerun() # Rerun to update UI with new session

with col3:
    # Option to load a session by ID
    load_session_id = st.text_input("Load Session ID:", value=st.session_state.get('load_session_input', ''), key='load_session_input_box')
    if st.button("Load Session", key="load_session_button"):
        if load_session_id in st.session_state.get('all_sessions', {}): # Assuming a way to store all sessions
            st.session_state.session_id = load_session_id
            st.session_state.chat_history = st.session_state.all_sessions[load_session_id]
            st.session_state.current_session_id = load_session_id
            st.success(f"Session '{load_session_id}' loaded.")
            st.rerun()
        else:
            st.error("Session ID not found.")

# Display current session ID (for user reference)
st.sidebar.markdown(f"**Current Session ID:** `{st.session_state.session_id}`")
st.sidebar.markdown("---")
st.sidebar.markdown("### Instructions")
st.sidebar.markdown("Type or speak your meeting request. Example: 'Schedule a meeting for tomorrow at 10 AM about project updates for 30 minutes.'")
st.sidebar.markdown("Click 'Speak' to use your microphone.")
st.sidebar.markdown("Use 'New Session' to start fresh.")
st.sidebar.markdown("Enter an ID and click 'Load Session' to continue a previous chat.")

# --- Persistence for chat_sessions (Simple in-memory for now) ---
# In a real app, you'd save st.session_state.chat_history to a database/file
# For demonstration, we'll use a simple in-memory dictionary for 'all_sessions'
# that gets updated on reruns. This is not truly persistent across app restarts.
if 'all_sessions' not in st.session_state:
    st.session_state.all_sessions = {}
st.session_state.all_sessions[st.session_state.session_id] = st.session_state.chat_history
