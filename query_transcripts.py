#!/usr/bin/env python3
"""
Gemini-powered query system for transcribed call recordings.
Uses transcripts as knowledge base to answer queries in English, Hindi, or Kannada.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️  Google Gemini SDK not installed. Install with: pip install google-genai")


class TranscriptQueryAgent:
    """Agent that uses Gemini to answer queries based on transcribed call recordings"""
    
    def __init__(self, business_id=None, api_key=None):
        """Initialize the query agent for a specific business"""
        if not GEMINI_AVAILABLE:
            raise ImportError("Google Gemini SDK is required. Install with: pip install google-genai")
        
        # Get API key
        if not api_key:
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found. Set it as environment variable or pass as argument.")
        
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        
        self.business_id = business_id
        if business_id:
            self.base_path = Path(f"businesses/{business_id}")
            self.transcripts_dir = self.base_path / "transcripts"
        else:
            # Fallback or "Default"
            self.base_path = Path(".")
            self.transcripts_dir = Path("transcripts")

        # Load Business Config
        self.config = {}
        config_path = self.base_path / "business_config.json"
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    self.config = json.load(f)
                print(f"🏢 Loaded config for: {self.config.get('business_name')} ({business_id})")
            except Exception as e:
                print(f"⚠️ Failed to load business config: {e}")

        # Load Knowledge Base (if exists)
        self.knowledge_base = None
        kb_path = self.base_path / "knowledge_base.json"
        if kb_path.exists():
            try:
                with open(kb_path, 'r') as f:
                    self.knowledge_base = json.load(f)
                print("🧠 Knowledge Base loaded successfully!")
            except Exception as e:
                print(f"⚠️ Failed to load Knowledge Base: {e}")
        
        # Load all transcripts (if needed for fallback)
        self.transcripts = self._load_transcripts()
        print(f"📚 Loaded {len(self.transcripts)} transcript files for {business_id}")
        
        # Try different models in order
        # Try different models in order - prioritize the one that works (gemini-2.0-flash-exp)
        self.models_to_try = ["gemini-2.0-flash-exp", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.5-flash-8b", "gemini-1.0-pro"]
        self.model_name = None
        
        # Cache for context to avoid rebuilding every time
        self.cached_context = None

    def reload(self):
        """Reload configuration, KB, and transcripts (clears cache)"""
        print(f"🔄 Reloading agent for {self.business_id}...")
        
        # Reload Config
        self.config = {}
        config_path = self.base_path / "business_config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"⚠️ Failed to reload config: {e}")

        # Reload KB
        self.knowledge_base = None
        kb_path = self.base_path / "knowledge_base.json"
        if kb_path.exists():
            try:
                with open(kb_path, 'r') as f:
                    self.knowledge_base = json.load(f)
            except Exception as e:
                print(f"⚠️ Failed to reload KB: {e}")
        
        # Reload Transcripts
        self.transcripts = self._load_transcripts()
        
        # Clear Cache
        self.cached_context = None
        print("✅ Agent reloaded successfully.")
    
    def _load_transcripts(self) -> List[Dict]:
        """Load all JSON transcript files"""
        transcripts = []
        
        if not self.transcripts_dir.exists():
            return transcripts
        
        # Find all JSON transcript files
        json_files = list(self.transcripts_dir.glob("*_gemini_*.json"))
        
        if not json_files:
            return transcripts
        
        for json_file in sorted(json_files):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Add filename for reference
                    data['_filename'] = json_file.name
                    transcripts.append(data)
            except Exception as e:
                print(f"⚠️  Error loading {json_file}: {e}")
        
        return transcripts
    
    def _get_transcript_context(self) -> str:
        """Format context for Gemini from Knowledge Base or Transcripts"""
        # Return cached context if available
        if self.cached_context:
            return self.cached_context

        # PRIORITY 1: USE STRUCTURED KNOWLEDGE BASE
        if self.knowledge_base:
            kb = self.knowledge_base
            context_parts = []
            context_parts.append("=== KNOWLEDGE BASE (Deduced from Call Recordings) ===")
            
            # Business Info
            biz = kb.get('business_info', {})
            context_parts.append(f"BUSINESS: {biz.get('name', 'Rainbow Driving School')}")
            if biz.get('location'): context_parts.append(f"LOCATION: {biz.get('location')}")
            if biz.get('owner'): context_parts.append(f"OWNER: {biz.get('owner')}")
            
            # Q&A Pairs
            context_parts.append("\n=== FREQUENT QUESTIONS & ANSWERS ===")
            for item in kb.get('qa_pairs', []):
                q = item.get('question')
                a = item.get('answer')
                context_parts.append(f"Q: {q}\nA: {a}\n")
            
            self.cached_context = "\n".join(context_parts)
            return self.cached_context
            
        # PRIORITY 2: FALLBACK TO RAW TRANSCRIPTS
        if not self.transcripts:
            return "No transcripts available."
        
        context_parts = []
        context_parts.append("=== TRANSCRIBED CALL RECORDINGS ===\n")
        context_parts.append("The following are transcriptions of business call recordings.\n")
        context_parts.append("Use this information to answer user queries.\n\n")
        
        for i, transcript in enumerate(self.transcripts, 1):
            filename = transcript.get('_filename', f'transcript_{i}')
            service = transcript.get('service', 'unknown')
            detected_lang = transcript.get('detected_language', 'unknown')
            
            context_parts.append(f"\n--- Recording {i} ({filename}) ---")
            context_parts.append(f"Service: {service}, Language: {detected_lang}\n")
            
            # Use English transcript if available, otherwise original
            transcript_text = transcript.get('transcript', '')
            if not transcript_text:
                transcript_text = transcript.get('transcript_original', '')
            
            if transcript_text:
                context_parts.append(transcript_text)
                context_parts.append("")  # Empty line between transcripts
        
        self.cached_context = "\n".join(context_parts)
        return self.cached_context
    
    def _detect_query_language(self, query: str) -> str:
        """Detect the language of the query - only Hindi or English"""
        # Check for Devanagari script (Hindi)
        has_devanagari = any('\u0900' <= c <= '\u097F' for c in query)
        
        if has_devanagari:
            return "Hindi"
        else:
            # Default to English for everything else (including Kannada, Urdu, etc.)
            return "English"
    
    def _initialize_model(self):
        """Initialize and test which Gemini model works"""
        if self.model_name:
            return self.model_name
        
        # Try gemini-1.5-flash first (better quota: 15 RPM vs 10 RPM)
        for model_name in self.models_to_try:
            try:
                # Test with a simple query
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=[types.Content(parts=[types.Part(text="Hello")])]
                )
                self.model_name = model_name
                print(f"✅ Using Gemini model: {model_name}")
                return model_name
            except Exception as e:
                if "404" in str(e) or "NOT_FOUND" in str(e):
                    continue
                else:
                    # For other errors, try next model
                    continue
        
        raise Exception("No working Gemini model found. Please check your API key and quota.")
    
    def answer_query(self, query: str, language: Optional[str] = None, conversation_history: List[Dict] = None) -> Dict:
        """Answer a query using the transcript knowledge base
        
        Args:
            query: The user's question
            language: Optional language override (Hindi/English)
            conversation_history: List of previous messages [{"role": "user/assistant", "text": "..."}]
        """
        if not self.transcripts and not self.knowledge_base:
            return {
                "query": query,
                "answer": "No information available. Please upload recordings or documents to build the knowledge base.",
                "error": "No transcripts or KB loaded"
            }
        
        # Move initialization inside try block to catch setup errors
        try:
            # Detect initial language (heuristic)
            heuristic_lang = self._detect_query_language(query)
            
            # Initialize model (if not already cached)
            model_name = self._initialize_model()
            
            # Get transcript context
            context = self._get_transcript_context()
            
            # Analyze conversation history for lead capture logic
            conversation_history = conversation_history or []
            
            # Count user turns (excluding current query which isn't in history yet)
            user_turns = sum(1 for msg in conversation_history if msg.get('role') == 'user')
            current_turn = user_turns + 1
            
            # Check if we already asked for contact info in ANY previous turn
            asked_for_contact = any(
                ("name" in msg.get('text', '').lower() and "phone" in msg.get('text', '').lower()) or
                ("naam" in msg.get('text', '').lower() and "number" in msg.get('text', '').lower())
                for msg in conversation_history 
                if msg.get('role') == 'assistant'
            )
            
            # Check if user provided contact info (regex heuristic)
            import re
            provided_contact = any(
                re.search(r'\d{10}', msg.get('text', '')) or re.search(r'\d{3}[-\s]\d{3}[-\s]\d{4}', msg.get('text', ''))
                for msg in conversation_history
                if msg.get('role') == 'user'
            )
            
            # Determine lead capture instruction
            lead_capture_instruction = ""
            if not asked_for_contact and not provided_contact:
                # Ask in the first 2 turns ONLY
                if current_turn <= 2:
                    lead_capture_instruction = "IMPORTANT: You MUST ask for their name and phone number in this response. Say something like 'May I have your name and number so I can better assist you?'"
                else:
                    # If we missed it early, don't nag them late in conversation
                    lead_capture_instruction = "DO NOT ask for name or phone number now. Focus on the query."
            else:
                # If we asked OR they provided, never ask again
                lead_capture_instruction = "**DO NOT** ask for name or phone number. We already have it or asked for it."

            # Determine greeting instruction
            # Only greet if this is the absolute first message (no history)
            greeting_instruction = "Greet the customer warmly."
            if len(conversation_history) > 0:
                greeting_instruction = "**DO NOT** greet the customer (no 'Hello', 'Hi', 'Namaste', etc.). Go straight to the answer."
            
            # Get business details for fallback
            owner_name = self.config.get('owner_name', 'us')
            owner_phone = self.config.get('phone', 'directly')
            agent_name = self.config.get('agent_name', 'Virtual Assistant')
            business_name = self.config.get('business_name', 'our business')
            
            prompt = f"""You are {agent_name}, the AI assistant for {business_name}, responding to customer inquiries. Answer naturally and conversationally.

CONTEXT FROM PREVIOUS CALL RECORDINGS:
{context}

CUSTOMER QUERY: {query}

CRITICAL INSTRUCTIONS:
1. **LANGUAGE DETECTION & RESTRICTION**: 
   - Detect the language of the CUSTOMER QUERY.
   - **ALLOWED SCRIPTS ONLY**: Latin (English), Devanagari (Hindi), Kannada.
   - **STRICTLY FORBIDDEN**: Urdu Script (Right-to-Left). NEVER result in Urdu script.
   - **Handling**:
     - If user speaks **Hindi** or **Hinglish** (Hindi in Latin) or **Urdu**: Respond in **Hindi (using Devanagari script)**.
     - If user speaks **Kannada**: Respond in **Kannada**.
     - If user speaks **English**: Respond in **English**.
     - If user speaks any other language: Respond in English.
2. **TONE & STYLE (CASUAL & NATURAL)**:
   - **General**: Be friendly, warm, and helpful. Talk like a real person, not a robot.
   - **English**: Use contractions (e.g., "I'm", "can't", "we're"). Use simple, spoken English. Avoid formal phrases like "I apologize" (say "Sorry about that") or "Please accept" (say "Here you go").
   - **Hindi**: Use natural **Hindustani** (Spoken Hindi). Casual but polite.
     - **Avoid** formal/textbook/Sanskritized words (e.g., avoid "kripya", "sahayata", "avashyak", "uppasthit"). 
     - **Use** common conversational words.
     - **Examples**:
       - ❌ Formal: "Kripya pratiksha karein" -> ✅ Casual: "Ek minute rukiye" or "Bas ek second"
       - ❌ Formal: "Kya mein aapki sahayata kar sakta hoon?" -> ✅ Casual: "Bataiye, kaise madad karu?" or "Haan ji, boliye?"
       - ❌ Formal: "Humari kakshaen" -> ✅ Casual: "Humari classes"
     - Use "ji" for politeness ("Haan ji", "Theek hai ji") but keep sentences simple.
3. Answer as the business owner would - naturally, helpfully, and directly.
4. Use ONLY the information from the call recordings above. Do NOT mention "according to recordings".
5. If the information is not available, suggest they call **{owner_name} at {owner_phone}**.
6. **LEAD CAPTURE STRATEGY**: 
   - We must capture name and phone number early (First 2 turns).
   - {lead_capture_instruction}
   - If asking, request BOTH together.
7. **GREETING**: {greeting_instruction}

Respond as {agent_name} (in Hindi Devanagari if user used Hindi/Hinglish, otherwise English):"""
        
            # Generate response with retries
            max_retries = 3
            import time
            import random
            
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=[
                            types.Content(
                                parts=[
                                    types.Part(text=prompt)
                                ]
                            )
                        ]
                    )
                    
                    answer = response.text.strip()
                    
                    # Detect language from ANSWER (to guide TTS)
                    # If answer contains Devanagari, it is Hindi
                    final_language = "English"
                    if any('\u0900' <= c <= '\u097F' for c in answer):
                        final_language = "Hindi"
                    
                    return {
                        "query": query,
                        "query_language": final_language,
                        "answer": answer,
                        "model": model_name,
                        "timestamp": datetime.now().isoformat(),
                        "transcripts_used": len(self.transcripts)
                    }
                    
                except Exception as loop_e:
                    last_error = loop_e
                    error_str = str(loop_e)
                    # Only retry on transient errors or rate limits
                    if "429" in error_str or "503" in error_str or "500" in error_str or "quota" in error_str.lower():
                        sleep_time = (attempt + 1) * 2 + random.uniform(0, 1)
                        print(f"⚠️  Attempt {attempt+1} failed ({error_str}), retrying in {sleep_time:.1f}s...")
                        time.sleep(sleep_time)
                    else:
                        raise loop_e
            
            # If we exhausted retries, raise the last error
            if last_error:
                raise last_error
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in answer_query: {error_msg}")
            
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "quota" in error_msg.lower():
                return {
                    "query": query,
                    "query_language": language if 'language' in locals() else "English",
                    "answer": "I apologize, but I'm experiencing high demand right now. Please try again in a few moments or call us directly for immediate assistance." if language == "English" else "अरे, अभी थोड़ी व्यस्तता है। थोड़ी देर बाद फिर से कोशिश करें या हमें सीधे फोन कर लें।",
                    "error": "quota_exceeded"
                }
            else:
                return {
                    "query": query,
                    "query_language": language if 'language' in locals() else "English",
                    "answer": "I apologize, I'm having technical difficulties. Please try again or call us for assistance." if language == "English" else "सॉरी, थोड़ी तकनीकी दिक्कत आ रही है। फिर से कोशिश करें या हमें कॉल करें।",
                    "error": "processing_error"
                }
    
    def extract_lead_info(self, conversation_messages: List[Dict]) -> Dict:
        """Extract customer name, phone number, and summary from conversation using Gemini"""
        if not conversation_messages:
            return {
                "customer_name": None,
                "customer_phone": None,
                "summary": "No conversation data"
            }
        
        # Initialize model if needed
        model_name = self._initialize_model()
        
        # Format conversation for analysis
        conversation_text = "\n".join([
            f"{'Customer' if msg['role'] == 'user' else 'SavitaDevi'}: {msg['text']}"
            for msg in conversation_messages
        ])
        
        prompt = f"""Analyze this conversation between a customer and SavitaDevi (Rainbow Driving School owner) and extract the following information:

CONVERSATION:
{conversation_text}

TASK:
Extract the following information:
1. Customer's name (first name and/or last name)
2. Customer's phone number (any format)
3. Brief summary of what the customer inquired about (2-3 sentences)
4. Lead classification based on conversation quality and intent

LEAD CLASSIFICATION CRITERIA:
- **HOT_LEAD**: Customer is actively interested, asked about pricing/enrollment/schedule, provided contact info, or wants to sign up
- **GENERAL_INQUIRY**: Customer asked legitimate questions about services, location, hours, but hasn't committed yet
- **SPAM**: Irrelevant conversation, testing the system, nonsensical queries, or promotional content
- **UNRELATED**: Conversation is not about driving school services at all

IMPORTANT:
- If information is NOT mentioned, return "Not provided"
- For phone numbers, extract exactly as mentioned (don't add country codes if not given)
- For names, handle both English and Hindi names
- Summary should be in English regardless of conversation language
- Choose ONE classification that best fits the conversation

Respond in this EXACT format:
NAME: [customer name or "Not provided"]
PHONE: [phone number or "Not provided"]
SUMMARY: [brief summary of inquiry]
CLASSIFICATION: [HOT_LEAD or GENERAL_INQUIRY or SPAM or UNRELATED]"""

        try:
            response = self.client.models.generate_content(
                model=model_name,
                contents=[
                    types.Content(
                        parts=[
                            types.Part(text=prompt)
                        ]
                    )
                ]
            )
            
            result_text = response.text.strip()
            
            # Parse the structured response
            lines = result_text.split('\n')
            extracted = {
                "customer_name": None,
                "customer_phone": None,
                "summary": None,
                "lead_classification": None
            }
            
            for line in lines:
                if line.startswith("NAME:"):
                    name = line.replace("NAME:", "").strip()
                    extracted["customer_name"] = name if name != "Not provided" else None
                elif line.startswith("PHONE:"):
                    phone = line.replace("PHONE:", "").strip()
                    extracted["customer_phone"] = phone if phone != "Not provided" else None
                elif line.startswith("SUMMARY:"):
                    summary = line.replace("SUMMARY:", "").strip()
                    extracted["summary"] = summary if summary != "Not provided" else None
                elif line.startswith("CLASSIFICATION:"):
                    classification = line.replace("CLASSIFICATION:", "").strip()
                    extracted["lead_classification"] = classification
            
            return extracted
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error extracting lead info: {error_msg}")
            
            # Return partial data on error instead of failing completely
            return {
                "customer_name": None,
                "customer_phone": None,
                "summary": "Error during analysis - conversation data preserved",
                "lead_classification": "UNRELATED"
            }
    
    def interactive_mode(self):
        """Run in interactive mode for querying"""
        print("\n" + "="*70)
        print("🎤 TRANSCRIPT QUERY AGENT")
        print("="*70)
        print("Ask questions about the call recordings in English, Hindi, or Kannada.")
        print("The agent will answer based on the transcribed conversations.")
        print("\nCommands:")
        print("  'quit' or 'exit' - Exit the agent")
        print("  'list' - List all loaded transcripts")
        print("  'summary' - Get a summary of all transcripts")
        print("="*70 + "\n")
        
        while True:
            try:
                query = input("\n💬 Your question: ").strip()
                
                if not query:
                    continue
                
                if query.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break
                
                if query.lower() == 'list':
                    print("\n📚 Loaded Transcripts:")
                    for i, transcript in enumerate(self.transcripts, 1):
                        filename = transcript.get('_filename', 'unknown')
                        service = transcript.get('service', 'unknown')
                        print(f"  {i}. {filename} ({service})")
                    continue
                
                if query.lower() == 'summary':
                    print("\n📊 Transcript Summary:")
                    print(f"  Total recordings: {len(self.transcripts)}")
                    total_chars = sum(len(t.get('transcript', '')) for t in self.transcripts)
                    print(f"  Total transcript length: {total_chars:,} characters")
                    continue
                
                # Process query
                print("\n🤔 Processing your question...")
                result = self.answer_query(query)
                
                if "error" in result:
                    print(f"❌ Error: {result['answer']}")
                else:
                    print(f"\n💡 Answer ({result.get('query_language', 'unknown')}):")
                    print("-" * 70)
                    print(result['answer'])
                    print("-" * 70)
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        # Interactive mode
        try:
            agent = TranscriptQueryAgent()
            agent.interactive_mode()
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            print("\nMake sure to set GEMINI_API_KEY environment variable:")
            print("  export GEMINI_API_KEY='your-api-key'")
            sys.exit(1)
    else:
        # Single query mode
        query = " ".join(sys.argv[1:])
        try:
            agent = TranscriptQueryAgent()
            result = agent.answer_query(query)
            
            if "error" in result:
                print(f"❌ Error: {result['answer']}")
                sys.exit(1)
            else:
                print(f"\n💡 Answer ({result.get('query_language', 'unknown')}):")
                print("-" * 70)
                print(result['answer'])
                print("-" * 70)
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            sys.exit(1)


if __name__ == "__main__":
    main()

