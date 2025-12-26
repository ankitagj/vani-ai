# Rainbow Driving School - Conversational AI Agent

A multilingual customer service agent powered by Google Gemini AI for Rainbow Driving School.

## 🌟 Features

- **Multilingual Support**: Handles Hindi and English conversations naturally
- **Voice Interface**: ElevenLabs Scribe for speech-to-text and TTS for responses
- **Lead Capture**: Automatically extracts customer name, phone number, and conversation summary
- **Smart Classification**: Categorizes leads as HOT_LEAD, GENERAL_INQUIRY, SPAM, or UNRELATED
- **Knowledge Base**: Powered by real call recordings (RD1-RD10)
- **Owner Dashboard**: View and manage captured leads

## 🏗️ Architecture

### Backend (`app.py`)
- Flask API server
- Gemini-powered conversational agent
- ElevenLabs TTS integration
- SQLite database for lead storage

### Frontend (`frontend/`)
- React + TypeScript + Vite
- ElevenLabs Scribe for voice input
- Real-time conversation UI
- Automatic turn-taking with silence detection

### Core Components

1. **`query_transcripts.py`** - Gemini-based query agent
   - Loads transcript knowledge base
   - Handles multilingual conversations
   - Extracts lead information

2. **`leads_db.py`** - Database management
   - Stores conversation history
   - Manages lead data
   - Provides dashboard queries

3. **`transcribe_audio.py`** - Audio transcription
   - Uses Gemini AI for transcription
   - Supports Hindi, English, Kannada
   - Auto-translation to English

## 📁 Project Structure

```
CustomerServiceAssistant/
├── app.py                      # Main Flask backend
├── query_transcripts.py        # Gemini query agent
├── leads_db.py                 # Database management
├── transcribe_audio.py         # Audio transcription
├── call_recordings/            # Audio files (RD1-RD10)
├── transcripts/                # Transcribed conversations
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── App.tsx
│   │   └── components/
│   │       └── ElevenLabsInput.tsx
│   └── package.json
├── leads.db                    # SQLite database
└── legacy_code/                # Unused ML model code (archived)
```

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Node.js 16+
- GEMINI_API_KEY
- VITE_ELEVEN_LABS_API_KEY

### Installation

1. **Backend Setup**
```bash
python3 -m venv ai_env
source ai_env/bin/activate
pip install -r requirements.txt
```

2. **Frontend Setup**
```bash
cd frontend
npm install
```

3. **Environment Variables**
Create `.env` in root:
```
GEMINI_API_KEY=your_gemini_key
```

Create `frontend/.env`:
```
VITE_ELEVEN_LABS_API_KEY=your_elevenlabs_key
```

### Running the Application

1. **Start Backend** (Terminal 1)
```bash
source ai_env/bin/activate
python app.py
```
Backend runs on `http://localhost:5001`

2. **Start Frontend** (Terminal 2)
```bash
cd frontend
npm run dev
```
Frontend runs on `http://localhost:5173`

3. **Access Dashboard**
```
http://localhost:5173/dashboard
```

## 📊 Knowledge Base

The agent is trained on 10 real call recordings covering:
- Location inquiries (Karaneshwar Nagar)
- Service offerings (two-wheeler training only)
- Pricing questions
- Appointment scheduling
- General business information

## 🎯 Key Capabilities

- **SavitaDevi** (AI Agent) can:
  - Answer questions about Rainbow Driving School
  - Speak in Hindi or English naturally
  - Capture customer contact information
  - Classify lead quality automatically
  - Maintain conversation context

## 🔧 API Endpoints

- `POST /ask-mom` - Send query, get response
- `POST /tts` - Text-to-speech conversion
- `POST /save-conversation` - Save conversation with lead data
- `GET /dashboard` - View leads dashboard
- `GET /get-scribe-token` - Get ElevenLabs token

## 📝 License

Private project for Rainbow Driving School

## 🙏 Acknowledgments

- Google Gemini AI for conversational intelligence
- ElevenLabs for voice technology
- Built with ❤️ for Rainbow Driving School
