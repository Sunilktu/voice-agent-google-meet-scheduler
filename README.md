# Google Meeting Scheduler Chatbot

A **voice-enabled AI assistant** built with Python, Streamlit, LangChain, and Google's Gemini model. Schedule meetings on your Google Calendar using natural language voice commands—automatically checks for conflicts and suggests alternatives.

---

## 🚀 Features

- **Interactive Web UI:** User-friendly interface powered by Streamlit.
- **Voice Interaction:** Speak your meeting requests and hear responses (Speech-to-Text & Text-to-Speech).
- **Dynamic Voice Button:** Toggle button "🎙️ Listen" for 10 seconds.
- **Natural Language Understanding:** Parses phrases like `tomorrow at 10 AM`, `next Tuesday`, etc.
- **Google Calendar Integration:** (Requires setup) Schedules meetings directly.
- **Conflict Detection & Suggestions:** Finds the next available 30-minute slot if conflicts exist.
- **Conversational Memory:** Maintains chat history per session.
- **Session Management:** Start new or load existing sessions with unique IDs.
- **Asynchronous Operations:** Responsive UI during blocking I/O (voice, API).
- **Loading Indicators:** Visual feedback during processing.

---

## 🛠️ How It Works

**Modular Components:**

- **Streamlit UI (`main.py`):** Displays chat, handles input, manages session state.
- **Voice I/O (`voice_io.py`):** 
  - `get_voice_input_streamlit()`: SpeechRecognition + Google Web Speech API.
  - `speak_text_streamlit()`: gTTS + pydub for audio playback.
- **Google Calendar API (`google_calendar_api.py`):** 
  - OAuth 2.0 authentication.
  - Real or mock API fallback.
- **Intelligent Tools (`tools.py`):**
  - `get_current_datetime_with_timezone()`
  - `parse_natural_datetime()`
  - `smart_schedule_meeting()`
- **LangChain Agent (`main.py`):**
  - Gemini 1.5 Flash as LLM.
  - Tools exposed via `StructuredTool` and Pydantic schemas.
  - `AgentExecutor` orchestrates tool use and responses.
  - `nest_asyncio.apply()` for event loop compatibility.

---

## 📦 Project Structure

```text
your_project_root/
├── main.py                 # Streamlit app
├── tools.py                # Tool functions & schemas
├── google_calendar_api.py  # Calendar API logic
├── voice_io.py             # STT & TTS logic
├── .env                    # Gemini API Key
├── credentials.json        # Google OAuth 2.0 secrets
├── token.json              # Calendar API token (auto-generated)
├── pyproject.toml          # Project dependencies & metadata
└── Dockerfile              # Container build instructions
```

---

## ⚡ Prerequisites

- **Python 3.8+** ([python.org](https://python.org))
- **Google Gemini API Key** (from Google AI Studio)
- **Google Cloud Project & OAuth 2.0 Client ID**
- **FFmpeg** (for audio playback)
  - **Windows:** [gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)
  - **macOS:** `brew install ffmpeg`
  - **Linux:** `sudo apt-get install ffmpeg`
- **Microphone & Speakers/Headphones**

---

## 📝 Installation

**1. Clone or set up files manually:**
Place `main.py`, `tools.py`, `google_calendar_api.py`, and `voice_io.py` in your project directory.

**2. Install [uv](https://astral.sh/uv/) (recommended):**

- **macOS/Linux:**
  ```sh
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- **Windows:**
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

Or, with pip:
```sh
pip install uv
```

**3. Create & activate a virtual environment:**
```sh
uv venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

**4. Install dependencies:**
```sh
uv sync
# If needed, install manually:
uv pip install streamlit langchain google-generativeai python-dotenv langchain-google-genai langchain_community pytz python-dateutil pydantic SpeechRecognition gTTS pydub nest_asyncio google-api-python-client google-auth-oauthlib google-auth-httplib2
```

---

## 🔑 Google API Key Setup

1. **Create `.env` in your project root:**
   ```
   GOOGLE_API_KEY=your_gemini_api_key_here
   ```
   > **Never commit `.env` to version control!**

---

## 📅 Google Calendar API Setup

1. **Create a Google Cloud Project** ([console](https://console.cloud.google.com/))
2. **Enable Google Calendar API**
3. **Create OAuth 2.0 Client ID** (Desktop app)
4. **Download credentials:** Rename to `credentials.json` and place in your project root.
5. **First run:** App will prompt for Google login and create `token.json`.

---

## ▶️ How to Run

```sh
uv run streamlit run main.py
```
App opens in your browser.

---

## 💬 Usage

- **Start/Load Session:** Use session ID to continue previous chats.
- **Text Input:** Type and press Enter.
- **Voice Input:** Click "🎙️ Listen", speak with in 10 seconds.
- **Scheduling:** Example:  
  > "Schedule a meeting for tomorrow at 10 AM about project updates for 30 minutes."
- **Bot will clarify missing info, check conflicts, and suggest alternatives.**

---

## 🧑‍💻 Example Interactions

- `"Schedule a meeting for tomorrow at 10 AM about team sync."`
- `"What is the current time?"`
- `"Parse 'next Monday at 5 PM'."`
- `"Schedule a quick chat today at 2 PM."`

---

## 🛠️ Troubleshooting

- **Asyncio errors:** Ensure `nest_asyncio` is installed.
- **FFmpeg not found:** Check PATH and restart terminal.
- **Audio issues:** Verify microphone/speaker settings.
- **Google Calendar API errors:** Check `credentials.json` and OAuth setup.
- **Agent issues:** Use verbose logs, clarify prompts.

---

## 🌱 Future Improvements

- Persistent chat memory (file/db)
- More robust natural language parsing
- Add meeting participants
- Streaming STT/TTS responses
- Enhanced error handling and feedback

---

## 🐳 Optional: Run with Docker

You can run the app in a container using the provided `Dockerfile`.

**1. Build the Docker image:**
```sh
docker build -t google-meeting-scheduler .
```

**2. Run the container:**
```sh
docker run -p 8501:8501 --env-file .env -v $(pwd)/credentials.json:/app/credentials.json google-meeting-scheduler
```

- Make sure `.env` and `credentials.json` are present in your project root.
- The app will be available at [http://localhost:8501](http://localhost:8501).

---