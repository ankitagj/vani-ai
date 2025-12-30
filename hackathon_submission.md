# 🏆 Vani.ai - Hackathon Submission

**Tagline**: Transform any business into a 24/7 Multilingual AI Call Center in seconds.

> **Note**: *Vani* (वाणी) means "Voice" or "Speech" in Sanskrit/Hindi. We chose this name because we are giving a powerful voice to small businesses that truly represents them.

## ❤️ The Inspiration (Our "Why")
**Our mother runs a small business in India:** [Rainbow Driving School Kalaburagi](https://share.google/hqycAgk6XpPHZrDrq), a 2-wheeler driving school dedicated to helping women become independent.

Her business has grown purely through word-of-mouth, bringing in **20-30 calls daily**.
We watched her struggle to keep up—juggling household work, running the business, and answering inquiries.
*   **The Struggle**: "She can't miss a lead, but the constant interruption is exhausting."
*   **The Cost**: It was costing her sleep, peace of mind, and quality time.
*   **The Insight**: 80% of the questions were repetitive ("What are the fees?", "Do you teach on weekends?").

**Vani.ai was born to give her back her time.**
We built an agent to handle the repetitive 80%, so she can focus on the 20% that matters—serving her customers and getting some well-deserved rest. We then realized this problem is universal for millions of SMBs, lead to the generalization of **Vani.ai**.

## 🚀 The Problem
Small businesses lose 60% of leads because they can't answer the phone 24/7. Hiring support staff is expensive, and language barriers (English vs. Hindi/Kannada) further alienate customers.

## 💡 The Solution: Vani.ai
Vani.ai is a **white-label AI Voice Agent platform** that:
1.  **Ingests Logic Instantly**: Upload call recordings or PDFs, and the AI "learns" the business in seconds.
2.  **Speaks Fluently**: Handles calls in English, Hindi, and Kannada with native-like accent and emotion.
3.  **Remembers You**: Defines "Smart Memory" to recognize repeat callers and greet them by name.
4.  **Captures Leads**: Automatically extracts Name, Phone, and Intent, pushing them to a live dashboard.

## 🛠️ System Architecture
[See System Design Diagram](system_design.md)

**Tech Stack**:
*   **Frontend**: React, Vite, Tailwind CSS (Custom Dashboard & Admin Panel)
*   **Backend**: Python, Flask, SQLite
*   **AI Orchestration**: Gemini 2.0 Flash (Reasoning & Extraction)
*   **Voice Pipeline**: ElevenLabs Scribe (STT) + ElevenLabs Turbo (TTS) + Vapi.ai (Telephony)
*   **Engagement**: Twilio (Automated SMS Follow-ups)

## ✨ Key Features (Demo Highlights)

### 1. Smart Lead Extraction
The system listens to the conversation and updates the dashboard in real-time.
*   **Caller ID Priority**: Trusted physical numbers over AI hallucinations.
*   **Strict English Output**: Even if the customer speaks Hindi ("Mera naam Ankita hai"), the dashboard shows "Ankita" in English.

### 2. Intelligent Turn-Taking
*   **No "Robot Pauses"**: Uses filler words ("Um, let me check...") to mask API latency.
*   **Interruption Handling**: Stops speaking immediately if the user interrupts.

### 3. Persistent Memory
*   **First Call**: "May I have your name?"
*   **Second Call**: "Welcome back, Ankita!" (No need to repeat details).

## 📹 Demo Video Script (Recording Instructions)
*Since the auto-recording encountered network issues, please screen-record the following flow for your submission video:*

1.  **Opening**: Show the **Vani.ai Directory** (Landing Page).
2.  **Selection**: Click on **Rainbow Driving School**.
3.  **Chat**: Type "Hello, do you have weekend slots?".
4.  **Dashboard**: Click the **Dashboard** button.
    *   Highlight the **Hot Leads** card.
    *   Show the **Recent Conversations** table with "Ankita" listed.
5.  **Multi-Tenancy**: Go back, select a different business (e.g., "Anvi Chatbot"), and show how the header/agent name changes instantly.

## 🔮 Future Roadmap
*   **WhatsApp Integration**: Full 2-way chat on WhatsApp.
*   **Smart Calendar Booking**: Automatically book appointments on the business calendar when a customer confirms a slot.
*   **Instant Knowledge Updates**: A simple text interface for business owners to instantly update their agent's knowledge (e.g., "We are closed this Friday").
*   **Intelligent Handoff**: Automatically reroute the call to the business owner if the AI agent detects it is struggling to answer effectively.

## 👥 Contributors
*   **Ankita Jhawar**
*   **Venkatesh Bhattad**
