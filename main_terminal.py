
import os
from datetime import datetime, timedelta
import pytz
from typing import Dict, Any
from dateutil.parser import parse as dateutil_parse # Import parse from dateutil
from functools import partial # Import partial for binding arguments to tool functions
import asyncio # For asynchronous operations
import uuid # For generating unique session IDs
from google.auth.transport.requests import Request # Required for creds.refresh()
import nest_asyncio # For allowing nested asyncio event loops

# Apply nest_asyncio to allow asyncio.run() to be called from a running event loop
nest_asyncio.apply()

# New imports for StructuredTool
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

# Google API imports
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow # Needed for generating token.json if not present
from dotenv import load_dotenv
load_dotenv()
# STT/TTS imports
import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment # Re-added: pydub for audio segment manipulation
from pydub.playback import play # Re-added: pydub for audio playback


# --- Google Calendar API Setup ---
# SCOPES required for Calendar API access
SCOPES = ['https://www.googleapis.com/auth/calendar']
TOKEN_FILE = 'token.json'
CREDENTIALS_FILE = 'credentials.json' # Your OAuth 2.0 client secrets file

def get_google_calendar_service():
    """Authenticates and returns a Google Calendar API service."""
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request()) # Requires 'from google.auth.transport.requests import Request'
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    return build('calendar', 'v3', credentials=creds)

# Initialize the actual Google Calendar API resource
# This will prompt for authentication if token.json is not found or invalid
try:
    api_resource = get_google_calendar_service()
    print("Google Calendar API service initialized successfully.")
except Exception as e:
    print(f"Error initializing Google Calendar API service: {e}")
    print("Please ensure 'credentials.json' is present and you have completed the OAuth flow to generate 'token.json'.")
    # Fallback to mock API if real API fails to initialize (for testing without full auth)
    class MockGoogleCalendarAPI:
        def __init__(self):
            self.events = []  # Stores mock events
        def list_events(self, calendarId, timeMin, timeMax):
            print(f"Mock API (Fallback): Checking conflicts in {calendarId} from {timeMin} to {timeMax}")
            min_dt = datetime.fromisoformat(timeMin)
            max_dt = datetime.fromisoformat(timeMax)
            conflicting = [event for event in self.events if datetime.fromisoformat(event['start']['dateTime']) < max_dt and datetime.fromisoformat(event['end']['dateTime']) > min_dt]
            return {'items': conflicting}
        def insert_event(self, calendarId, eventBody):
            print(f"Mock API (Fallback): Inserting event into {calendarId}:", eventBody)
            new_event = {'id': f"mock_event_{len(self.events) + 1}", 'status': 'confirmed', 'summary': eventBody['summary'], 'start': eventBody['start'], 'end': eventBody['end'], 'htmlLink': f"https://mockcalendar.google.com/event/{len(self.events) + 1}"}
            self.events.append(new_event)
            return new_event
        def events(self):
            return type('EventsService', (object,), {
                'list': lambda **kwargs: type('ListRequest', (object,), {'execute': lambda: self.list_events(calendarId=kwargs.get('calendarId'), timeMin=kwargs.get('timeMin'), timeMax=kwargs.get('timeMax'))})(),
                'insert': lambda **kwargs: type('InsertRequest', (object,), {'execute': lambda: self.insert_event(calendarId=kwargs.get('calendarId'), eventBody=kwargs.get('body'))})()
            })()
    api_resource = MockGoogleCalendarAPI()
    print("Using Mock Google Calendar API as a fallback.")


# --- Tool Functions ---

# Tool 1: Get Current Datetime
def get_current_datetime_with_timezone() -> str:
    """Returns the current date and time including the timezone in ISO format."""
    time_zone = 'Asia/Kolkata'
    tz = pytz.timezone(time_zone)
    now = datetime.now(tz)
    return now.isoformat()

# Tool 2: Parse Natural Datetime
def parse_natural_datetime(input_string: str, current_datetime_str: str) -> Dict[str, str]:
    """
    Converts natural language like 'tomorrow at 10 AM' or 'next Friday 3pm'
    into a precise datetime in ISO format (yyyy-mm-ddThh:mm:ss).
    Uses dateutil.parser for robust parsing.
    """
    time_zone = 'Asia/Kolkata'
    tz = pytz.timezone(time_zone)

    try:
        # Parse the current_datetime_str to a timezone-aware datetime object
        current_dt = tz.localize(datetime.fromisoformat(current_datetime_str).replace(tzinfo=None))

        # Use dateutil.parser.parse to intelligently parse the input string
        # fuzzy=True allows for partial matches and ignores unrecognized text
        # dayfirst=False, yearfirst=False for common formats
        # default=current_dt provides a base datetime for relative parsing (e.g., "tomorrow")
        parsed_dt = dateutil_parse(input_string, fuzzy=True, default=current_dt)

        # Ensure the parsed datetime is timezone-aware in the desired timezone
        if parsed_dt.tzinfo is None:
            parsed_dt = tz.localize(parsed_dt)
        else:
            parsed_dt = parsed_dt.astimezone(tz)

        return {"parsed_datetime": parsed_dt.isoformat()}
    except Exception as e:
        return {"error": f"Could not parse natural datetime: {e}. Please try a more specific format."}

# Tool 3: Smart Schedule Meeting
# This function now takes api_resource as an explicit argument
def smart_schedule_meeting(
    summary: str,
    preferred_start: str,
    preferred_end: str,
    calendar_id: str = 'primary',
    api_resource: Any = None # Add api_resource as an argument
) -> Dict[str, Any]:
    """
    Smartly schedules a meeting, checking for conflicts and suggesting alternative slots.
    """
    if api_resource is None:
        return {"status": "error", "message": "Google Calendar API resource not provided to the tool."}

    time_zone = 'Asia/Kolkata' # Fixed timezone for demonstration

    if not all([summary, preferred_start, preferred_end]):
        return {"status": "error", "message": "Missing required meeting details (summary, preferred_start, preferred_end)."}

    try:
        tz = pytz.timezone(time_zone)
        # Ensure datetimes are timezone-aware from the start
        start_dt = tz.localize(datetime.fromisoformat(preferred_start).replace(tzinfo=None))
        end_dt = tz.localize(datetime.fromisoformat(preferred_end).replace(tzinfo=None))

        start_iso = start_dt.isoformat()
        end_iso = end_dt.isoformat()

        # Step 1: List events that might conflict
        events_result = api_resource.events().list(
            calendarId=calendar_id,
            timeMin=start_iso,
            timeMax=end_iso,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        conflicting_events = events_result.get('items', [])

        # Step 2: If no conflict -> create event
        if not conflicting_events:
            event = {
                'summary': summary,
                'start': {'dateTime': start_iso, 'timeZone': time_zone},
                'end': {'dateTime': end_iso, 'timeZone': time_zone},
            }
            created_event = api_resource.events().insert(calendarId=calendar_id, body=event).execute()
            return {"status": "success", "message": "Meeting scheduled.", "event": created_event}
        else:
            # Step 3: Conflict detected -> suggest next available 30-min slot
            suggested_start_dt = end_dt
            # Find the end time of the last conflicting event
            for conflict in conflicting_events:
                conflict_end_dt = tz.localize(datetime.fromisoformat(conflict['end']['dateTime']).replace(tzinfo=None))
                if conflict_end_dt > suggested_start_dt:
                    suggested_start_dt = conflict_end_dt

            # Add a small buffer and round up to the next 30-minute mark
            suggested_start_dt += timedelta(minutes=5)
            minutes = suggested_start_dt.minute
            remainder = minutes % 30
            if remainder != 0:
                suggested_start_dt += timedelta(minutes=(30 - remainder))
            suggested_start_dt = suggested_start_dt.replace(second=0, microsecond=0)

            duration = end_dt - start_dt
            suggested_end_dt = suggested_start_dt + duration

            # Check if the suggested slot is also free
            suggested_events_result = api_resource.events().list(
                calendarId=calendar_id,
                timeMin=suggested_start_dt.isoformat(),
                timeMax=suggested_end_dt.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            if not suggested_events_result.get('items', []):
                return {
                    "status": "conflict",
                    "message": "Preferred time is busy. Suggested next available slot:",
                    "suggested_start": suggested_start_dt.isoformat(),
                    "suggested_end": suggested_end_dt.isoformat()
                }
            else:
                return {
                    "status": "conflict",
                    "message": "Preferred time is busy and next suggested time is also unavailable. Please try another slot."
                }
    except Exception as e:
        print(f"Error in smart_schedule_meeting: {e}")
        return {"status": "error", "message": f"An error occurred: {str(e)}"}

# --- LangChain Agent Setup ---

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage

# Set your Google API Key
# It's recommended to load this from an environment variable or a .env file
# os.environ["GOOGLE_API_KEY"] = "YOUR_GEMINI_API_KEY" # Uncomment and replace if not using env vars

# Initialize the LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.05)

# Define Pydantic models for tool input schemas
class GetCurrentDatetimeInput(BaseModel):
    """Input for GetCurrentDatetime tool. Takes no arguments."""
    pass

class ParseNaturalDatetimeInput(BaseModel):
    """Input for ParseNaturalDatetime tool."""
    input_string: str = Field(description="The natural language phrase to parse (e.g., 'tomorrow 10 AM', 'next Friday 3pm').")
    current_datetime_str: str = Field(description="The current datetime in ISO format, provided by GetCurrentDatetime tool.")

class ScheduleMeetingInput(BaseModel):
    """Input for ScheduleMeeting tool."""
    summary: str = Field(description="Summary or title of the meeting.")
    preferred_start: str = Field(description="Preferred start time in ISO format (e.g., '2025-07-17T10:00:00+05:30').")
    preferred_end: str = Field(description="Preferred end time in ISO format (e.g., '2025-07-17T10:30:00+05:30').")
    calendar_id: str = Field(default='primary', description="ID of the calendar to schedule the meeting in (default 'primary').")


# Define the tools for the agent using StructuredTool
tools = [
    StructuredTool.from_function(
        func=get_current_datetime_with_timezone,
        name="GetCurrentDatetime",
        description="Returns the current date and time including the timezone in ISO format (e.g., '2025-07-17T10:00:00+05:30').",
        args_schema=GetCurrentDatetimeInput, # Specify the input schema
    ),
    StructuredTool.from_function(
        func=parse_natural_datetime,
        name="ParseNaturalDatetime",
        description="Converts natural language like 'tomorrow at 10 AM' or 'next Friday 3pm' into a precise datetime in ISO format (yyyy-mm-ddThh:mm:ss).",
        args_schema=ParseNaturalDatetimeInput, # Specify the input schema
    ),
    StructuredTool.from_function(
        # Use partial to bind the api_resource to smart_schedule_meeting
        func=partial(smart_schedule_meeting, api_resource=api_resource),
        name="ScheduleMeeting",
        description="Smartly schedules a meeting. If the preferred time is busy, it suggests the next available 30-min slot.",
        args_schema=ScheduleMeetingInput, # Specify the input schema
    ),
]

# Define the prompt for the agent
# The prompt guides the LLM on how to use the tools and respond.
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful AI assistant that can schedule meetings and understand natural language dates and times. Use the provided tools to assist the user. If you need more information to schedule a meeting (e.g., summary, start time, end time, duration), please ask the user clarifying questions. Always try to provide a clear summary of the scheduled meeting or suggested time."),
    ("placeholder", "{chat_history}"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

# Create the tool-calling agent
agent = create_tool_calling_agent(llm, tools, prompt)

# Create the agent executor
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# --- Chat Loop ---
# Dictionary to store chat history for different sessions
chat_sessions: Dict[str, list] = {}

# Recognizer instance for STT
r = sr.Recognizer()

async def get_voice_input() -> str:
    """Captures voice input from the microphone and converts it to text."""
    with sr.Microphone() as source:
        print("\nSay something!")
        r.adjust_for_ambient_noise(source) # Adjust for ambient noise
        try:
            audio = await asyncio.to_thread(r.listen, source, timeout=5, phrase_time_limit=5) # Listen for up to 5 seconds
            print("Recognizing...")
            text = await asyncio.to_thread(r.recognize_google, audio) # Use Google Web Speech API
            print(f"You said: {text}")
            return text
        except sr.WaitTimeoutError:
            print("No speech detected. Please try again.")
            return ""
        except sr.UnknownValueError:
            print("Could not understand audio. Please try again.")
            return ""
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")
            return ""
        except Exception as e:
            print(f"An unexpected error occurred during voice input: {e}")
            return ""

async def speak_text(text: str):
    """Converts text to speech and plays it using gTTS and pydub."""
    if not text:
        return
    print(f"Bot speaking: {text}")
    try:
        tts = gTTS(text=text, lang='en')
        audio_file = "bot_response.mp3"
        
        # Save the gTTS output to a temporary MP3 file
        await asyncio.to_thread(tts.save, audio_file)
        
        # Load the MP3 file using pydub
        audio = AudioSegment.from_file(audio_file, format="mp3")
        
        # Play the AudioSegment using pydub's playback.play
        # This will use ffplay (from FFmpeg) for MP3 playback.
        await asyncio.to_thread(play, audio)
        
        os.remove(audio_file) # Clean up the temporary file
    except Exception as e:
        print(f"Error during text-to-speech or playback: {e}")
        print("Please ensure FFmpeg is installed and accessible in your system's PATH for MP3 playback with pydub.")

async def chat_with_scheduler():
    print("Welcome to the Meeting Scheduler Voice Bot!")
    print("To start a new session, type 'new'. To load an existing session, type 'load' and then provide the session ID.")
    print("Type 'exit' to quit.")

    session_id = None
    while session_id is None:
        session_choice = input("\nNew session or load existing? (new/load): ").lower()
        if session_choice == 'new':
            session_id = str(uuid.uuid4())
            chat_sessions[session_id] = []
            print(f"New session started. Your session ID is: {session_id}")
        elif session_choice == 'load':
            input_session_id = input("Enter existing session ID: ")
            if input_session_id in chat_sessions:
                session_id = input_session_id
                print(f"Session '{session_id}' loaded.")
            else:
                print("Session ID not found. Please try again or start a new session.")
        else:
            print("Invalid choice. Please type 'new' or 'load'.")

    current_chat_history = chat_sessions[session_id]

    while True:
        user_input = await get_voice_input() # Get voice input
        if not user_input: # If no valid speech was recognized, loop again
            continue

        if user_input.lower() == 'exit':
            print("Exiting chat. Your session history is saved.")
            await speak_text("Exiting chat. Goodbye!")
            break

        print("Bot is thinking...") # Indicate processing

        try:
            # Invoke the agent with the user's input and current chat history
            result = await agent_executor.ainvoke({
                "input": user_input,
                "chat_history": current_chat_history
            })
            ai_response = result["output"]
            print(f"Bot: {ai_response}")
            await speak_text(ai_response) # Speak the bot's response

            # Update chat history for the current session
            current_chat_history.append(HumanMessage(content=user_input))
            current_chat_history.append(AIMessage(content=ai_response))
            chat_sessions[session_id] = current_chat_history # Ensure it's saved back

        except Exception as e:
            error_message = f"Bot: An error occurred: {e}. Please try again."
            print(error_message)
            await speak_text("I'm sorry, an error occurred. Please try again.")
            # Optionally, log the full traceback for debugging
            # import traceback
            # traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(chat_with_scheduler())
