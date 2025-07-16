
import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from datetime import datetime # Import datetime for mock API

# SCOPES required for Calendar API access
SCOPES = ['https://www.googleapis.com/auth/calendar']
TOKEN_FILE = 'token.json'
CREDENTIALS_FILE = 'credentials.json' # Your OAuth 2.0 client secrets file

def get_google_calendar_service():
    """Authenticates and returns a Google Calendar API service."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    return build('calendar', 'v3', credentials=creds)

class MockGoogleCalendarAPI:
    def __init__(self):
        self.events = []  # Stores mock events

    def list_events(self, calendarId, timeMin, timeMax):
        """Simulates listing events for conflict checking."""
        print(f"Mock API (Fallback): Checking conflicts in {calendarId} from {timeMin} to {timeMax}")
        min_dt = datetime.fromisoformat(timeMin)
        max_dt = datetime.fromisoformat(timeMax)

        conflicting = [
            event for event in self.events
            if datetime.fromisoformat(event['start']['dateTime']) < max_dt and
               datetime.fromisoformat(event['end']['dateTime']) > min_dt
        ]
        return {'items': conflicting}

    def insert_event(self, calendarId, eventBody):
        """Simulates inserting a new event."""
        print(f"Mock API (Fallback): Inserting event into {calendarId}:", eventBody)
        new_event = {
            'id': f"mock_event_{len(self.events) + 1}",
            'status': 'confirmed',
            'summary': eventBody['summary'],
            'start': eventBody['start'],
            'end': eventBody['end'],
            'htmlLink': f"https://mockcalendar.google.com/event/{len(self.events) + 1}"
        }
        self.events.append(new_event)
        return new_event

    def events(self):
        return type('EventsService', (object,), {
            'list': lambda **kwargs: type('ListRequest', (object,), {
                'execute': lambda: self.list_events(
                    calendarId=kwargs.get('calendarId'),
                    timeMin=kwargs.get('timeMin'),
                    timeMax=kwargs.get('timeMax')
                )
            })(),
            'insert': lambda **kwargs: type('InsertRequest', (object,), {
                'execute': lambda: self.insert_event(
                    calendarId=kwargs.get('calendarId'),
                    eventBody=kwargs.get('body')
                )
            })()
        })()

# Initialize the API resource (real or mock) when this module is imported
try:
    api_resource = get_google_calendar_service()
    print("Google Calendar API service initialized successfully.")
except Exception as e:
    print(f"Error initializing Google Calendar API service: {e}")
    print("Please ensure 'credentials.json' is present and you have completed the OAuth flow to generate 'token.json'.")
    api_resource = MockGoogleCalendarAPI()
    print("Using Mock Google Calendar API as a fallback.")