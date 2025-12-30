# Vani.ai System Architecture

```mermaid
graph TD
    User(["User / Caller"])
    
    subgraph "Frontend Layer (React + Vite)"
        UI[Web Interface]
        Dashboard[Analytics Dashboard]
        Setup[Onboarding Wizard]
    end
    
    subgraph "Communication Layer"
        Vapi[Vapi.ai Telephony]
        Twilio[Twilio SMS]
    end
    
    subgraph "Backend Core (Flask / Python)"
        API[REST API]
        Socket[WebSocket Handler]
        Orchestrator[Agent Orchestrator]
    end
    
    subgraph "Intelligence Engine"
        Gemini["Gemini 2.0 Flash (Reasoning)"]
        Scribe["ElevenLabs Scribe (STT)"]
        ElevenLabs["ElevenLabs Turbo (TTS)"]
    end
    
    subgraph "Data Layer"
        DB[("SQLite Leads DB")]
        KB[("Knowledge Base JSON")]
        Files["Audio Transcripts"]
    end

    %% Flows
    User -- "Voice Call" --> Vapi
    User -- "Web Chat" --> UI
    
    Vapi -- "Webhook (End of Call)" --> API
    Vapi -- "Audio Stream" --> Scribe
    
    UI --> API
    
    API --> Orchestrator
    Orchestrator --> Gemini
    Orchestrator --> DB
    
    Gemini -- "Answer / Extraction" --> Orchestrator
    
    Orchestrator -- "Response Text" --> ElevenLabs
    ElevenLabs -- "Audio" --> Vapi
    
    Orchestrator -- "Send SMS" --> Twilio
    Twilio -- "SMS" --> User
    
    Setup -- "Upload Files" --> API
    API -- "Process" --> KB
```

## Component Description

1.  **Frontend**: Built with **React** and **Vite**, focusing on a premium, responsive UI. It handles business registration, live chat testing, and provides a real-time analytics dashboard.
2.  **Backend**: Powered by **Flask** (Python). It serves as the central controller, managing webhooks from telephony providers and coordinating AI services.
3.  **Telephony**:
    *   **Vapi.ai**: Manages the phone line, voice activity detection, and latency optimization.
    *   **Twilio**: Handles programmatic SMS dispatch for post-call engagement.
4.  **Intelligence**:
    *   **Gemini 2.0 Flash**: The brain. Handles conversational logic, intent understanding, and data extraction (Lead Name, Phone, Summary).
    *   **ElevenLabs Scribe/Turbo**: Full-stack voice AI (Speech-to-Text and Text-to-Speech) for seamless, low-latency interaction.
5.  **Data**: A lightweight **SQLite** database tracks conversation history and extracted leads, enabling persistent memory (recognizing repeat callers).
