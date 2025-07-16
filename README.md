# Google Meeting Scheduler Chatbot

This is a voice-enabled AI assistant built with Python, Streamlit, LangChain, and Google's Gemini model. It allows users to schedule meetings on their Google Calendar using natural language voice commands, automatically checking for conflicts and suggesting alternative time slots.

## Features

  * **Interactive Web UI:** A user-friendly web interface powered by Streamlit.

  * **Voice Interaction:** Speak your meeting requests and hear the bot's responses using Speech-to-Text (STT) and Text-to-Speech (TTS).

  * **Voice Button:** A single button toggles to "🎙️ Listen" (to start recording for 10 seconds) and "" (to indicate recording is active).

  * **Natural Language Understanding:** Understands various date and time expressions (e.g., "tomorrow at 10 AM", "next Tuesday", "in 3 days") using `python-dateutil`.

  * **Google Calendar Integration:** (Requires setup) Schedules meetings directly on your Google Calendar.

  * **Conflict Detection & Suggestion:** Automatically checks for conflicting events and proposes the next available 30-minute slot.

  * **Conversational Memory:** Maintains chat history for each session, allowing for multi-turn interactions and follow-up questions.

  * **Session Management:** Start new chat sessions or load existing ones using unique session IDs.

  * **Asynchronous Operations:** Uses `asyncio` and `asyncio.to_thread` to ensure a responsive UI while performing blocking I/O operations (like voice recording/playback and API calls).

  * **Loading Indicators:** Provides visual feedback when the bot is processing.

## Prerequisites

Before you begin, ensure you have the following installed:

  * **Python 3.8+**: Download from [python.org](https://www.python.org/downloads/).

  * **Google Gemini API Key**: Obtain one from [Google AI Studio](https://aistudio.google.com/app/apikey).

  * **Google Cloud Project & OAuth 2.0 Client ID**: For Google Calendar API integration.

  * **FFmpeg**: Essential for `pydub` to handle MP3 audio playback.

      * **Windows:** Download a pre-built FFmpeg executable from [gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/) (e.g., `ffmpeg-release-full.7z`). Extract it and **add the `bin` folder** (e.g., `C:\ffmpeg\bin`) to your system's `PATH` environment variable.

      * **macOS:** `brew install ffmpeg`

      * **Linux (Debian/Ubuntu):** `sudo apt-get install ffmpeg`

  * **Microphone**: For voice input.

  * **Speakers/Headphones**: For voice output.

## Project Structure

It's recommended to organize your project into the following structure:

```
your_project_root/
├── streamlit_app.py        # Main Streamlit application
├── tools.py                # Contains all tool functions and their Pydantic schemas
├── google_calendar_api.py  # Handles Google Calendar API initialization and mock
├── voice_io.py             # Handles Speech-to-Text (STT) and Text-to-Speech (TTS)
├── .env                    # Stores your Google Gemini API Key (create this file)
├── credentials.json        # Your Google OAuth 2.0 client secrets (downloaded from Google Cloud)
└── token.json              # Google Calendar API token (generated on first run)
```

## Installation

1.  **Clone the repository (or set up files manually):**
    Create the project directory and place `streamlit_app.py`, `tools.py`, `google_calendar_api.py`, and `voice_io.py` inside it.

2.  **Create a Python Virtual Environment (recommended):**
    Navigate to your project root in the terminal and run:

    ```bash
    python -m venv .venv
    ```

3.  **Activate the Virtual Environment:**

      * **Windows:**

        ```bash
        .venv\Scripts\activate
        ```

      * **macOS/Linux:**

        ```bash
        source .venv/bin/activate
        ```

4.  **Install Python Libraries:**

    ```bash
    pip install streamlit langchain google-generativeai python-dotenv langchain-google-genai langchain_community pytz python-dateutil pydantic SpeechRecognition gTTS pydub nest_asyncio google-api-python-client google-auth-oauthlib google-auth-httplib2
    ```

## Google API Key Setup (`.env` file)

1.  **Create a `.env` file:** In your project's root directory (the same folder as `streamlit_app.py`), create a new file named `.env`.

2.  **Add your Gemini API Key:** Open the `.env` file and add the following line, replacing `your_gemini_api_key_here` with your actual Google Gemini API Key:

    ```
    GOOGLE_API_KEY=your_gemini_api_key_here
    ```

      * **Security Note:** Never commit your `.env` file to version control (e.g., Git repositories) as it contains sensitive information.

## Google Calendar API Setup

To enable actual meeting scheduling on your Google Calendar:

1.  **Create a Google Cloud Project:** Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project.

2.  **Enable Google Calendar API:** In your Google Cloud project, navigate to "APIs & Services" \> "Enabled APIs & services" and enable the "Google Calendar API."

3.  **Create OAuth 2.0 Client ID:**

      * Go to "APIs & Services" \> "Credentials."

      * Click "Create Credentials" \> "OAuth client ID."

      * Select "Desktop app" as the application type.

      * Give it a name (e.g., "Calendar Chatbot").

      * Click "Create."

      * Download the JSON file. Rename it to `credentials.json` and place it in the same directory as your `streamlit_app.py` script.

4.  **Generate `token.json`:**
    The first time you run the Streamlit app, it will attempt to authenticate with Google. This will open a web browser, ask you to log in to your Google account, and grant permission to access your calendar. After successful authorization, a `token.json` file will be automatically created in your script's directory. This file stores your credentials for future use.

    *If `token.json` is not generated or authentication fails, the script will fall back to a mock Google Calendar API for demonstration purposes.*

## How to Run

1.  **Activate your virtual environment** (if you haven't already).

2.  **Run the Streamlit application:**

    ```bash
    streamlit run streamlit_app.py
    ```

    This command will open the application in your default web browser.

## Usage

When you run the Streamlit app, you'll see a chat interface.

  * **Start/Load Session:**

      * The bot will initially welcome you and provide a new session ID, or you can use the "Load Session ID" input and "Load Session" button to continue a previous conversation.

  * **Text Input:** Type your message in the chat input box at the bottom and press Enter.

  * **Voice Input:**

    1.  Click the "🎙️ Listen" button.

    2.  The app will indicate it's "Listening...".

    3.  Speak your meeting request into your microphone.

    4.  The app will then process your speech and convert it to text.

    5.  The bot will respond both in text and verbally.

    6.  The "Stop" button will automatically revert to "Listen" after the listening period (10 seconds or when speech ends).

  * **Scheduling Meetings:**

      * Provide clear instructions for scheduling, e.g., "Schedule a meeting for tomorrow at 10 AM about project updates for 30 minutes."

      * The bot will ask clarifying questions if any information (summary, time, duration) is missing.

      * It will check for conflicts and suggest alternative slots if the preferred time is busy.

**Example Interactions:**

  * "Schedule a meeting for tomorrow at 10 AM about team sync."

  * "What is the current time?"

  * "Parse 'next Monday at 5 PM'."

  * "Schedule a quick chat today at 2 PM." (The bot might ask for duration or summary if missing).

## Troubleshooting

  * **`RuntimeError: asyncio.run() cannot be called from a running event loop`**: This is handled by `nest_asyncio.apply()`. Ensure `nest_asyncio` is installed.

  * **`Error during text-to-speech or playback: ...`**:

      * **FFmpeg not found:** Ensure FFmpeg is correctly installed and its `bin` directory is added to your system's `PATH` environment variable. Restart your terminal/command prompt after modifying PATH.

      * **Audio device issues:** Check your microphone and speaker settings.

  * **`Could not understand audio` / `No speech detected`**:

      * Ensure your microphone is properly connected and selected as the default input device.

      * Speak clearly and at a normal volume.

      * Check for background noise.

  * **`Error initializing Google Calendar API service: ...`**:

      * Verify `credentials.json` is in the correct directory and is valid.

      * Ensure you have completed the OAuth consent screen setup in Google Cloud Console.

      * The `token.json` file might be expired or corrupted; try deleting it and rerunning the script to re-authenticate.

  * **Agent not scheduling or parsing correctly:**

      * Review the `verbose=True` output in your terminal (where you ran `streamlit run`) to see the agent's thought process and tool calls. This can help identify if the LLM is misunderstanding the prompt or the tool descriptions.

      * Refine your prompts to be clearer and more explicit.

## Future Improvements

  * **Persistent Chat Memory:** Implement saving/loading chat sessions to a file (e.g., JSON) or a database (e.g., SQLite, Firestore) to retain history across app restarts.

  * **More Robust Natural Language Parsing:** While `dateutil` is good, for highly complex or ambiguous phrases, integrating with a dedicated NLU service or a more advanced parsing model could be beneficial.

  * **Meeting Participants:** Extend the `ScheduleMeeting` tool to allow adding participants to the meeting.

  * **User Preferences:** Allow users to set default meeting durations, preferred time zones, or calendar IDs.

  * **Enhanced Error Handling & User Feedback:** Provide more specific and user-friendly error messages, especially for API-related failures, directly within the UI.

  * **Streaming Responses:** Implement streaming for both STT and TTS for a more real-time conversational flow.