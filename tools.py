
from datetime import datetime, timedelta
import pytz
from typing import Dict, Any
from dateutil.parser import parse as dateutil_parse
from pydantic import BaseModel, Field

# Import api_resource from google_calendar_api module
# This api_resource is already initialized (either real or mock) when this module is imported.
from google_calendar_api import api_resource

# --- Tool Functions ---

def get_current_datetime_with_timezone() -> str:
    """Returns the current date and time including the timezone in ISO format."""
    time_zone = 'Asia/Kolkata'
    tz = pytz.timezone(time_zone)
    now = datetime.now(tz)
    return now.isoformat()

def parse_natural_datetime(input_string: str, current_datetime_str: str) -> Dict[str, str]:
    """
    Converts natural language like 'tomorrow at 10 AM' or 'next Friday 3pm'
    into a precise datetime in ISO format (yyyy-mm-ddThh:mm:ss).
    Uses dateutil.parser for robust parsing.
    """
    time_zone = 'Asia/Kolkata'
    tz = pytz.timezone(time_zone)

    try:
        current_dt = tz.localize(datetime.fromisoformat(current_datetime_str).replace(tzinfo=None))
        parsed_dt = dateutil_parse(input_string, fuzzy=True, default=current_dt)
        
        if parsed_dt.tzinfo is None:
            parsed_dt = tz.localize(parsed_dt)
        else:
            parsed_dt = parsed_dt.astimezone(tz)

        return {"parsed_datetime": parsed_dt.isoformat()}
    except Exception as e:
        return {"error": f"Could not parse natural datetime: {e}. Please try a more specific format."}

def smart_schedule_meeting(
    summary: str,
    preferred_start: str,
    preferred_end: str,
    calendar_id: str = 'primary'
) -> Dict[str, Any]:
    """
    Smartly schedules a meeting, checking for conflicts and suggesting alternative slots.
    This function now directly uses the 'api_resource' imported at the module level.
    """
    # Access api_resource directly from the module scope
    global api_resource 

    time_zone = 'Asia/Kolkata' 

    if not all([summary, preferred_start, preferred_end]):
        return {"status": "error", "message": "Missing required meeting details (summary, preferred_start, preferred_end)."}

    try:
        tz = pytz.timezone(time_zone)
        start_dt = tz.localize(datetime.fromisoformat(preferred_start).replace(tzinfo=None))
        end_dt = tz.localize(datetime.fromisoformat(preferred_end).replace(tzinfo=None))

        start_iso = start_dt.isoformat()
        end_iso = end_dt.isoformat()

        events_result = api_resource.events().list(
            calendarId=calendar_id,
            timeMin=start_iso,
            timeMax=end_iso,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        conflicting_events = events_result.get('items', [])

        if not conflicting_events:
            event = {
                'summary': summary,
                'start': {'dateTime': start_iso, 'timeZone': time_zone},
                'end': {'dateTime': end_iso, 'timeZone': time_zone},
            }
            created_event = api_resource.events().insert(calendarId=calendar_id, body=event).execute()
            return {"status": "success", "message": "Meeting scheduled.", "event": created_event}
        else:
            suggested_start_dt = end_dt
            for conflict in conflicting_events:
                conflict_end_dt = tz.localize(datetime.fromisoformat(conflict['end']['dateTime']).replace(tzinfo=None))
                if conflict_end_dt > suggested_start_dt:
                    suggested_start_dt = conflict_end_dt

            suggested_start_dt += timedelta(minutes=5)
            minutes = suggested_start_dt.minute
            remainder = minutes % 30
            if remainder != 0:
                suggested_start_dt += timedelta(minutes=(30 - remainder))
            suggested_start_dt = suggested_start_dt.replace(second=0, microsecond=0)

            duration = end_dt - start_dt
            suggested_end_dt = suggested_start_dt + duration

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

# --- Pydantic Models for Tool Input Schemas ---
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
