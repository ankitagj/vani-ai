#!/usr/bin/env python3
"""
High-quality audio transcription for Indian languages (Hindi, Kannada, English)
Supports multiple transcription services optimized for Indian languages.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Translation support
try:
    from deep_translator import GoogleTranslator
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False
    print("⚠️  deep-translator not installed. Install with: pip install deep-translator")




def transcribe_with_google(audio_path, api_key=None):
    """Transcribe using Google Cloud Speech-to-Text (excellent for Kannada and Hindi)"""
    try:
        from google.cloud import speech
        import io
        
        if not api_key:
            # Google Cloud uses service account JSON file
            creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if not creds_path or not os.path.exists(creds_path):
                print("⚠️  GOOGLE_APPLICATION_CREDENTIALS not set or file not found.")
                print("   Set it to your service account JSON file path.")
                return None
        
        # Initialize client
        client = speech.SpeechClient()
        
        # Read audio file
        with io.open(audio_path, "rb") as audio_file:
            content = audio_file.read()
        
        # Configure for Indian languages - try Kannada first, then Hindi, then auto-detect
        # Google supports both kn-IN (Kannada) and hi-IN (Hindi) explicitly
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
            sample_rate_hertz=16000,  # Will auto-detect if different
            language_code="kn-IN",  # Kannada (India)
            alternative_language_codes=["hi-IN", "en-IN"],  # Hindi and English as alternatives
            enable_automatic_punctuation=True,
            enable_word_time_offsets=True,
            enable_speaker_diarization=True,
            model="latest_long",  # Best for long-form audio
        )
        
        audio = speech.RecognitionAudio(content=content)
        
        print("🎤 Transcribing with Google Cloud Speech-to-Text (optimized for Kannada/Hindi)...")
        
        # Perform transcription
        response = client.recognize(config=config, audio=audio)
        
        # Also try long-running operation for better results
        operation = client.long_running_recognize(config=config, audio=audio)
        response = operation.result(timeout=300)  # 5 minute timeout
        
        # Extract transcript
        transcript_parts = []
        for result in response.results:
            transcript_parts.append(result.alternatives[0].transcript)
        
        full_transcript = " ".join(transcript_parts)
        
        result = {
            "transcript": full_transcript,
            "detected_language": "kn-IN/hi-IN/en-IN (mixed)",
            "service": "google_cloud"
        }
        
        print("✅ Transcription complete!")
        return result
        
    except ImportError:
        print("⚠️  Google Cloud Speech-to-Text not installed. Install with: pip install google-cloud-speech")
        return None
    except Exception as e:
        print(f"❌ Google Cloud transcription failed: {str(e)}")
        return None


def transcribe_with_assemblyai(audio_path, api_key=None):
    """Transcribe using AssemblyAI (good multilingual support)"""
    try:
        import assemblyai as aai
        
        if not api_key:
            api_key = os.getenv('ASSEMBLYAI_API_KEY')
            if not api_key:
                print("⚠️  ASSEMBLYAI_API_KEY not found. Please set it as environment variable.")
                return None
        
        aai.settings.api_key = api_key
        
        print("🎤 Transcribing with AssemblyAI...")
        
        # Configure transcriber
        config = aai.TranscriptionConfig(
            language_code="hi",  # Hindi (will auto-detect if mixed)
            speaker_labels=True,
            auto_punctuate=True,
            format_text=True,
        )
        
        transcriber = aai.Transcriber(config=config)
        
        # Transcribe
        transcript = transcriber.transcribe(audio_path)
        
        if transcript.status == aai.TranscriptStatus.error:
            print(f"❌ AssemblyAI error: {transcript.error}")
            return None
        
        result = {
            "transcript": transcript.text,
            "detected_language": transcript.language_code if hasattr(transcript, 'language_code') else "unknown",
            "service": "assemblyai"
        }
        
        print("✅ Transcription complete!")
        return result
        
    except ImportError:
        print("⚠️  AssemblyAI SDK not installed. Install with: pip install assemblyai")
        return None
    except Exception as e:
        print(f"❌ AssemblyAI transcription failed: {str(e)}")
        return None


def transcribe_with_gemini(audio_path, api_key=None):
    """Transcribe using Google Gemini API (excellent for multilingual content)"""
    try:
        from google import genai
        
        if not api_key:
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                print("⚠️  GEMINI_API_KEY not found. Please set it as environment variable.")
                print("   Get your API key from: https://aistudio.google.com/app/apikey")
                return None
        
        print("🎤 Transcribing with Google Gemini (optimized for multilingual content)...")
        
        # Initialize Gemini client
        client = genai.Client(api_key=api_key)
        
        # Read audio file
        print("⏳ Reading audio file...")
        with open(audio_path, "rb") as audio_file:
            audio_data = audio_file.read()
        
        # Determine MIME type
        mimetype = "audio/mpeg"
        if audio_path.endswith('.wav'):
            mimetype = "audio/wav"
        elif audio_path.endswith('.m4a'):
            mimetype = "audio/mp4"
        
        # Create prompt for transcription
        prompt = """
Listen to this audio carefully. It is a business call recording.

Please transcribe the dialogue with the following requirements:
1. ALWAYS identify and label each speaker for EVERY line of dialogue.
2. Use the format "Speaker 1:", "Speaker 2:", etc. before each speaker's dialogue.
3. Transcribe the dialogue exactly as spoken, preserving the original language(s).
4. If the conversation is in multiple languages (Kannada, Hindi, English, or a mix), transcribe each part accurately in its original language.
5. Maintain proper punctuation and sentence structure.
6. Do not translate - provide the exact transcription in the original language(s).
7. Include all business terms, names, and important details exactly as spoken.

IMPORTANT: Every line of dialogue must be prefixed with a speaker label (Speaker 1:, Speaker 2:, etc.). 
If you can identify the role (Customer, Business Owner, etc.), you may use descriptive labels, but always use consistent labels throughout.

Provide only the transcription, no additional commentary.
"""
        
        # Generate transcription using direct content method
        print("⏳ Transcribing with Gemini...")
        from google.genai import types
        
        # Try different models in order
        models_to_try = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash-exp"]
        response = None
        last_error = None
        
        for model_name in models_to_try:
            try:
                # Use Content with Parts structure
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        types.Content(
                            parts=[
                                types.Part(text=prompt),
                                types.Part(
                                    inline_data=types.Blob(
                                        mime_type=mimetype,
                                        data=audio_data
                                    )
                                )
                            ]
                        )
                    ]
                )
                print(f"✅ Using model: {model_name}")
                break
            except Exception as e:
                last_error = e
                if "404" in str(e) or "NOT_FOUND" in str(e):
                    print(f"⚠️  Model {model_name} not found, trying next...")
                    continue
                else:
                    # For quota errors or other issues, raise immediately
                    raise
        
        if response is None:
            raise Exception(f"All models failed. Last error: {last_error}")
        
        # Extract transcript
        transcript = response.text.strip()
        
        # Try to get more structured response if available
        detected_language = "unknown"
        if hasattr(response, 'candidates') and response.candidates:
            # Try to detect language from response metadata if available
            pass
        
        result = {
            "transcript": transcript,
            "detected_language": detected_language,
            "paragraphs": [],
            "confidence": None,
            "service": "gemini"
        }
        
        print(f"✅ Transcription complete!")
        print(f"📝 Transcript length: {len(transcript)} characters")
        
        return result
        
    except ImportError:
        print("⚠️  Google Gemini SDK not installed. Install with: pip install google-genai")
        return None
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
            print(f"⚠️  Gemini quota exceeded. Falling back to other services...")
        else:
            print(f"❌ Gemini transcription failed: {error_str[:200]}")
        return None


def transcribe_with_whisper_local(audio_path, model_size="large-v3"):
    """Fallback: Use local Whisper with large model (better than base for Indian languages)"""
    try:
        import whisper
        
        print(f"🎤 Transcribing with local Whisper ({model_size})...")
        print("   (This may take a while and requires significant disk space)")
        
        # Load model
        model = whisper.load_model(model_size)
        
        # Transcribe with language detection
        result = model.transcribe(
            audio_path,
            language=None,  # Auto-detect
            task="transcribe",
            verbose=True
        )
        
        transcript_result = {
            "transcript": result["text"],
            "detected_language": result.get("language", "unknown"),
            "segments": [{"start": s["start"], "end": s["end"], "text": s["text"]} for s in result.get("segments", [])],
            "service": f"whisper-{model_size}"
        }
        
        print(f"✅ Transcription complete! Detected language: {result.get('language', 'unknown')}")
        return transcript_result
        
    except ImportError:
        print("⚠️  Whisper not installed. Install with: pip install openai-whisper")
        return None
    except Exception as e:
        print(f"❌ Whisper transcription failed: {str(e)}")
        return None


def translate_to_english(text, translator=None):
    """Translate text to English, handling mixed languages"""
    if not TRANSLATION_AVAILABLE:
        return text, None
    
    if not text or not text.strip():
        return text, None
    
    try:
        if translator is None:
            translator = GoogleTranslator(source='auto', target='en')
        
        # Check if text contains non-ASCII characters (likely non-English)
        has_non_ascii = any(ord(c) > 127 for c in text)
        
        if not has_non_ascii:
            # Text appears to be all ASCII (likely English)
            return text, 'en'
        
        # Text contains non-ASCII characters, needs translation
        # Try translating the whole text first
        try:
            translated_text = translator.translate(text)
            
            # If translation returned the same text, try translating word by word for mixed content
            if translated_text == text or (len(translated_text) - len(text)) < 2:
                # Split into words and translate non-ASCII words
                import re
                words = re.findall(r'\S+|\s+', text)  # Split preserving spaces
                translated_words = []
                
                for word in words:
                    if word.isspace():
                        translated_words.append(word)
                    elif any(ord(c) > 127 for c in word):
                        # Word contains non-ASCII, translate it
                        try:
                            translated_word = GoogleTranslator(source='auto', target='en').translate(word)
                            translated_words.append(translated_word)
                        except:
                            translated_words.append(word)
                    else:
                        # ASCII word, keep as is
                        translated_words.append(word)
                
                translated_text = ''.join(translated_words)
            
            return translated_text, 'auto'
        except Exception as e:
            # If bulk translation fails, try word-by-word
            import re
            words = re.findall(r'\S+|\s+', text)
            translated_words = []
            
            for word in words:
                if word.isspace():
                    translated_words.append(word)
                elif any(ord(c) > 127 for c in word):
                    try:
                        translated_word = GoogleTranslator(source='auto', target='en').translate(word)
                        translated_words.append(translated_word)
                    except:
                        translated_words.append(word)
                else:
                    translated_words.append(word)
            
            return ''.join(translated_words), 'auto'
            
    except Exception as e:
        print(f"⚠️  Translation warning: {str(e)}")
        return text, None


def translate_transcript_data(transcript_data):
    """Translate transcript and all its components to English"""
    if not TRANSLATION_AVAILABLE:
        print("⚠️  Translation not available. Install deep-translator for English output.")
        return transcript_data
    
    translator = GoogleTranslator(source='auto', target='en')
    
    # Translate main transcript
    original_transcript = transcript_data.get("transcript", "")
    if original_transcript:
        translated_transcript, source_lang = translate_to_english(original_transcript, translator)
        transcript_data["transcript_original"] = original_transcript
        transcript_data["transcript"] = translated_transcript
        transcript_data["source_language"] = source_lang
        print(f"🌐 Translated transcript from {source_lang} to English")
    
    # Translate paragraphs if they exist
    if "paragraphs" in transcript_data and transcript_data["paragraphs"]:
        for para in transcript_data["paragraphs"]:
            if isinstance(para, dict):
                # Translate sentences in paragraph
                if "sentences" in para:
                    for sent in para["sentences"]:
                        if isinstance(sent, dict) and "text" in sent:
                            original_text = sent["text"]
                            translated_text, _ = translate_to_english(original_text, translator)
                            sent["text_original"] = original_text
                            sent["text"] = translated_text
    
    # Translate segments if they exist (for Whisper)
    if "segments" in transcript_data and transcript_data["segments"]:
        for seg in transcript_data["segments"]:
            if isinstance(seg, dict) and "text" in seg:
                original_text = seg["text"]
                translated_text, _ = translate_to_english(original_text, translator)
                seg["text_original"] = original_text
                seg["text"] = translated_text
    
    return transcript_data


def save_transcript(transcript_data, audio_path, output_dir="transcripts", translate=True):
    """Save transcript to file, optionally translating to English"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Translate to English if requested
    if translate:
        print("\n🌐 Translating transcript to English...")
        transcript_data = translate_transcript_data(transcript_data)
    
    # Create output filename
    audio_name = Path(audio_path).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    service_name = transcript_data.get("service", "unknown")
    
    # Save as JSON (includes both original and translated)
    json_path = os.path.join(output_dir, f"{audio_name}_{service_name}_{timestamp}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(transcript_data, f, indent=2, ensure_ascii=False)
    
    # Save as text (English version)
    txt_path = os.path.join(output_dir, f"{audio_name}_{service_name}_{timestamp}.txt")
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(f"Transcription Service: {service_name}\n")
        f.write(f"Detected Language: {transcript_data.get('detected_language', 'unknown')}\n")
        if translate and transcript_data.get('source_language'):
            f.write(f"Source Language: {transcript_data.get('source_language')}\n")
            f.write(f"Translated to: English\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
        f.write("\n" + "="*50 + "\n\n")
        f.write("TRANSCRIPT (English):\n")
        f.write("-" * 50 + "\n")
        f.write(transcript_data["transcript"])
        
        # Also include original if it exists and is different
        if translate and transcript_data.get("transcript_original") and transcript_data["transcript_original"] != transcript_data["transcript"]:
            f.write("\n\n" + "="*50 + "\n")
            f.write("ORIGINAL TRANSCRIPT:\n")
            f.write("-" * 50 + "\n")
            f.write(transcript_data["transcript_original"])
    
    print(f"\n💾 Transcript saved:")
    print(f"   JSON: {json_path}")
    print(f"   TXT:  {txt_path} (English)")
    
    return json_path, txt_path


def main():
    """Main transcription function - tries multiple services in order"""
    if len(sys.argv) < 2:
        print("Usage: python transcribe_audio.py <audio_file> [service] [--api-key KEY]")
        print("\nServices:")
        print("  1. gemini   - Best for multilingual (Kannada/Hindi/English) (requires GEMINI_API_KEY)")
        print("\nIf no service specified, will try Gemini first.")
        print("\nYou can pass API key via:")
        print("  - Environment variable: export GEMINI_API_KEY='your-key'")
        print("  - Command line: --api-key your-key")
        sys.exit(1)
    
    audio_path = sys.argv[1]
    preferred_service = None
    api_key = None
    
    # Parse command line arguments
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--api-key" and i + 1 < len(sys.argv):
            api_key = sys.argv[i + 1]
            i += 2
        elif not arg.startswith("--"):
            preferred_service = arg
            i += 1
        else:
            i += 1
    
    if not os.path.exists(audio_path):
        print(f"❌ Error: Audio file not found: {audio_path}")
        sys.exit(1)
    
    print(f"📁 Audio file: {audio_path}")
    print(f"📊 File size: {os.path.getsize(audio_path) / (1024*1024):.2f} MB\n")
    
    # Try services in order of preference
    services_to_try = []
    
    if preferred_service:
        services_to_try = [preferred_service.lower()]
    else:
        services_to_try = ["gemini"]
    
    transcript_result = None
    
    for service in services_to_try:
        print(f"\n{'='*60}")
        print(f"Trying service: {service.upper()}")
        print(f"{'='*60}\n")
        
        if service == "gemini":
            transcript_result = transcribe_with_gemini(audio_path, api_key=api_key)
        
        else:
            print(f"⚠️  Unknown service: {service}")
            continue
        
        if transcript_result:
            # Save transcript (with translation to English)
            save_transcript(transcript_result, audio_path, translate=True)
            
            # Print preview (English version)
            print(f"\n{'='*60}")
            print("TRANSCRIPT PREVIEW (English):")
            print(f"{'='*60}")
            preview = transcript_result["transcript"][:500]
            print(preview)
            if len(transcript_result["transcript"]) > 500:
                print(f"\n... ({len(transcript_result['transcript']) - 500} more characters)")
            print(f"{'='*60}\n")
            
            break
        else:
            print(f"⚠️  {service} failed or not available, trying next service...\n")
    
    if not transcript_result:
        print("\n❌ All transcription services failed or are unavailable.")
        print("\nTo use API services, you need to:")
        print("  1. Gemini: Set GEMINI_API_KEY environment variable")
        print("     Get key from: https://aistudio.google.com/app/apikey")
        print("     Or pass via: --api-key YOUR_GEMINI_KEY")
        sys.exit(1)


if __name__ == "__main__":
    main()

