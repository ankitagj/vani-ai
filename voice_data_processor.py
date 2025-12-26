# Install required packages:


import whisper
import os
import json
import pandas as pd
from pydub import AudioSegment
from pydub.silence import split_on_silence
import re
from datetime import datetime
import numpy as np
from langdetect import detect, DetectorFactory

import logging

# Set seed for consistent language detection
DetectorFactory.seed = 0

class MultilingualVoiceDataProcessor:
    def __init__(self, whisper_model_size="base"):
        # Load Whisper model for transcription (supports multilingual)
        print(f"Loading Whisper model ({whisper_model_size})...")
        self.whisper_model = whisper.load_model(whisper_model_size)

        

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Conversation patterns
        self.conversation_data = []
        self.training_pairs = []

        # Language-specific patterns for speaker identification
        self.language_patterns = self._initialize_language_patterns()

    def _initialize_language_patterns(self):
        """Initialize language-specific patterns for speaker identification"""
        return {
            'english': {
                'customer_patterns': [
                    r'\b(are you|do you|can i|what time|how long|is there)\b',
                    r'\b(open|closed|reservation|table|wait|menu)\b',
                    r'\?(.*)$',  # Questions
                    r'\b(hi|hello|thanks|thank you)\b.*\?',
                    r'\b(i want|i need|i would like)\b'
                ],
                'business_patterns': [
                    r'\b(we are|we\'re|yes we|no we|we close|we open)\b',
                    r'\b(thank you for calling|how can i help|what can i do)\b',
                    r'\b(our hours|we take|we don\'t|we have)\b',
                    r'\b(about.*minutes|reservation for|table for)\b'
                ]
            },
            'hindi': {
                'customer_patterns': [
                    r'\b(kya|kaise|kab|kitna|kahan)\b',  # what, how, when, how much, where
                    r'\b(khula|band|samay|time)\b',  # open, closed, time
                    r'\b(chahiye|chaahte|mangta)\b',  # want, need
                    r'\b(namaste|dhanyawad|shukriya)\b'  # greetings, thanks
                ],
                'business_patterns': [
                    r'\b(hum|hamare|hamara)\b',  # we, our
                    r'\b(ji haan|ji nahin|bilkul)\b',  # yes, no, absolutely
                    r'\b(samay|ghante|minute)\b',  # time, hours, minutes
                    r'\b(aapka swagat|kaise madad)\b'  # welcome, how to help
                ]
            },
            'kannada': {
                'customer_patterns': [
                    r'\b(yaava|hege|yaavaga|eshtu)\b',  # which, how, when, how much
                    r'\b(khali|muchkondu|samaya)\b',  # open, closed, time
                    r'\b(beku|bekagide|kodtira)\b',  # want, need, will you give
                    r'\b(namaskara|dhanyavada)\b'  # greetings, thanks
                ],
                'business_patterns': [
                    r'\b(naavu|namdu|namma)\b',  # we, our
                    r'\b(houdu|illa|sariyaagi)\b',  # yes, no, correctly
                    r'\b(samaya|gante|nimisha)\b',  # time, hours, minutes
                    r'\b(swagata|hege sahaya)\b'  # welcome, how to help
                ]
            }
        }

    def detect_language(self, text):
        """Detect the language of the given text"""
        try:
            detected_lang = detect(text)
            # Map detected language codes to our supported languages
            lang_mapping = {
                'en': 'english',
                'hi': 'hindi',
                'kn': 'kannada'
            }
            return lang_mapping.get(detected_lang, 'english')  # Default to English
        except:
            # If detection fails, try to identify based on script/patterns
            if any(ord(char) >= 0x0900 and ord(char) <= 0x097F for char in text):  # Devanagari
                return 'hindi'
            elif any(ord(char) >= 0x0C80 and ord(char) <= 0x0CFF for char in text):  # Kannada
                return 'kannada'
            else:
                return 'english'

    def preprocess_audio(self, audio_path, output_dir="processed_audio"):
        """Clean and prepare audio files for better transcription"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Load audio
        audio = AudioSegment.from_file(audio_path)
        
        # Normalize audio
        audio = audio.normalize()
        
        # Remove silence and split into segments
        chunks = split_on_silence(
            audio,
            min_silence_len=1000,  # 1 second
            silence_thresh=audio.dBFS-14,
            keep_silence=500
        )
        
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            if len(chunk) > 2000:  # Only keep chunks longer than 2 seconds
                chunk_path = f"{output_dir}/chunk_{i}.wav"
                chunk.export(chunk_path, format="wav")
                processed_chunks.append(chunk_path)
        
        return processed_chunks
    
    def transcribe_conversation(self, audio_path):
        """Transcribe full conversation with multilingual support"""
        self.logger.info(f"Transcribing conversation: {audio_path}")

        # First transcribe the entire conversation
        result = self.whisper_model.transcribe(audio_path)

        # Detect primary language of the conversation
        primary_language = self.detect_language(result["text"])
        self.logger.info(f"Detected primary language: {primary_language}")

        # Split into chunks and try to identify speakers
        chunks = self.preprocess_audio(audio_path)

        conversation = {
            "full_transcript": result["text"],
            "primary_language": primary_language,
            "segments": [],
            "audio_path": audio_path,
            "timestamp": datetime.now().isoformat()
        }

        for chunk_path in chunks:
            chunk_result = self.whisper_model.transcribe(chunk_path)
            chunk_language = self.detect_language(chunk_result["text"])

            conversation["segments"].append({
                "text": chunk_result["text"],
                "language": chunk_language,
                "audio_file": chunk_path,
                "duration": len(AudioSegment.from_file(chunk_path)) / 1000
            })

        return conversation
    
    def identify_speakers(self, conversation):
        """Multilingual speaker identification based on patterns"""
        segments = conversation["segments"]
        labeled_segments = []
        primary_language = conversation.get("primary_language", "english")

        for segment in segments:
            text = segment["text"].lower().strip()
            segment_language = segment.get("language", primary_language)

            # Get language-specific patterns
            patterns = self.language_patterns.get(segment_language, self.language_patterns['english'])
            customer_patterns = patterns['customer_patterns']
            business_patterns = patterns['business_patterns']

            # Score each segment
            customer_score = sum(1 for pattern in customer_patterns if re.search(pattern, text))
            business_score = sum(1 for pattern in business_patterns if re.search(pattern, text))

            # Additional scoring based on common patterns across languages
            # Questions typically indicate customers
            if '?' in text or text.endswith('?'):
                customer_score += 1

            # Formal greetings often indicate business
            if any(greeting in text for greeting in ['welcome', 'calling', 'help', 'swagat', 'sahaya']):
                business_score += 1

            # Assign speaker
            if business_score > customer_score:
                speaker = "business_owner"
            elif customer_score > 0:
                speaker = "customer"
            else:
                speaker = "unknown"

            labeled_segments.append({
                **segment,
                "speaker": speaker,
                "customer_score": customer_score,
                "business_score": business_score,
                "segment_language": segment_language
            })

        conversation["labeled_segments"] = labeled_segments
        return conversation
    
    def extract_qa_pairs(self, conversation):
        """Extract question-answer pairs from multilingual conversation"""
        segments = conversation["labeled_segments"]
        qa_pairs = []
        primary_language = conversation.get("primary_language", "english")

        for i, segment in enumerate(segments):
            if segment["speaker"] == "customer":
                question = segment["text"]
                question_language = segment.get("segment_language", primary_language)

                # Look for the next business owner response
                for j in range(i + 1, len(segments)):
                    if segments[j]["speaker"] == "business_owner":
                        answer = segments[j]["text"]
                        answer_language = segments[j].get("segment_language", primary_language)

                        qa_pairs.append({
                            "question": question.strip(),
                            "answer": answer.strip(),
                            "question_language": question_language,
                            "answer_language": answer_language,
                            "primary_language": primary_language,
                            "context": {
                                "conversation_id": conversation.get("audio_path", ""),
                                "timestamp": conversation.get("timestamp", ""),
                                "question_audio": segment.get("audio_file", ""),
                                "answer_audio": segments[j].get("audio_file", "")
                            }
                        })
                        break

        return qa_pairs
    
    def categorize_intents(self, qa_pairs):
        """Categorize questions by intent across multiple languages"""
        # Multilingual intent patterns
        intent_patterns = {
            "hours": {
                "english": [r"\b(hours|open|close|what time|timing)\b"],
                "hindi": [r"\b(samay|khula|band|kab|ghante)\b"],
                "kannada": [r"\b(samaya|khali|muchkondu|yaavaga|gante)\b"]
            },
            "availability": {
                "english": [r"\b(table|available|wait|busy|reservation|book)\b"],
                "hindi": [r"\b(table|jagah|intezaar|vyast|booking)\b"],
                "kannada": [r"\b(table|stala|kaayuva|busy|booking)\b"]
            },
            "menu": {
                "english": [r"\b(menu|food|eat|dish|special|cuisine)\b"],
                "hindi": [r"\b(menu|khana|bhojan|dish|vishesh)\b"],
                "kannada": [r"\b(menu|anna|oota|dish|visheshha)\b"]
            },
            "location": {
                "english": [r"\b(where|address|location|directions|find)\b"],
                "hindi": [r"\b(kahan|pata|jagah|raasta|dhundna)\b"],
                "kannada": [r"\b(elli|patta|stala|daari|kandu)\b"]
            },
            "contact": {
                "english": [r"\b(phone|number|call|contact|reach)\b"],
                "hindi": [r"\b(phone|number|call|sampark|pahunchna)\b"],
                "kannada": [r"\b(phone|number|call|sampark|seralu)\b"]
            },
            "pricing": {
                "english": [r"\b(price|cost|expensive|cheap|much|rate)\b"],
                "hindi": [r"\b(daam|kimat|mehnga|sasta|kitna)\b"],
                "kannada": [r"\b(bele|kimat|jasti|kammi|eshtu)\b"]
            },
            "services": {
                "english": [r"\b(delivery|takeout|catering|party|service)\b"],
                "hindi": [r"\b(delivery|ghar|catering|party|seva)\b"],
                "kannada": [r"\b(delivery|mane|catering|party|seva)\b"]
            }
        }

        categorized_pairs = []

        for pair in qa_pairs:
            question = pair["question"].lower()
            question_language = pair.get("question_language", "english")

            # Find the best matching intent using language-specific patterns
            intent_scores = {}
            for intent, lang_patterns in intent_patterns.items():
                patterns = lang_patterns.get(question_language, lang_patterns.get("english", []))
                score = sum(1 for pattern in patterns if re.search(pattern, question))
                if score > 0:
                    intent_scores[intent] = score

            # Assign the highest scoring intent
            if intent_scores:
                best_intent = max(intent_scores, key=intent_scores.get)
            else:
                best_intent = "general"

            categorized_pairs.append({
                **pair,
                "intent": best_intent,
                "intent_confidence": intent_scores.get(best_intent, 0)
            })

        return categorized_pairs
    
    def process_all_recordings(self, audio_directory):
        """Process all audio files in a directory"""
        all_conversations = []
        all_qa_pairs = []
        
        # Support common audio formats
        audio_extensions = ['.wav', '.mp3', '.m4a', '.flac', '.ogg']
        
        audio_files = []
        for ext in audio_extensions:
            audio_files.extend([f for f in os.listdir(audio_directory) if f.endswith(ext)])
        
        print(f"Found {len(audio_files)} audio files to process...")
        
        for i, filename in enumerate(audio_files):
            print(f"Processing {i+1}/{len(audio_files)}: {filename}")
            
            try:
                audio_path = os.path.join(audio_directory, filename)
                
                # Transcribe conversation
                conversation = self.transcribe_conversation(audio_path)
                
                # Identify speakers
                conversation = self.identify_speakers(conversation)
                
                # Extract Q&A pairs
                qa_pairs = self.extract_qa_pairs(conversation)
                
                # Categorize intents
                qa_pairs = self.categorize_intents(qa_pairs)
                
                all_conversations.append(conversation)
                all_qa_pairs.extend(qa_pairs)
                
                print(f"  - Extracted {len(qa_pairs)} Q&A pairs")
                
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
                continue
        
        return all_conversations, all_qa_pairs
    
    def save_training_data(self, qa_pairs, output_file="training_data.json"):
        """Save processed Q&A pairs for training"""
        training_data = {
            "total_pairs": len(qa_pairs),
            "created_at": datetime.now().isoformat(),
            "qa_pairs": qa_pairs
        }
        
        with open(output_file, 'w') as f:
            json.dump(training_data, f, indent=2)
        
        # Also create a simple CSV for easy viewing
        df = pd.DataFrame([{
            "question": pair["question"],
            "answer": pair["answer"],
            "intent": pair["intent"],
            "confidence": pair["intent_confidence"]
        } for pair in qa_pairs])
        
        df.to_csv(output_file.replace('.json', '.csv'), index=False)
        
        print(f"Saved {len(qa_pairs)} training pairs to {output_file}")
        return training_data
    
    def analyze_data_quality(self, qa_pairs):
        """Analyze the quality and distribution of extracted data"""
        # Intent distribution
        intent_counts = {}
        for pair in qa_pairs:
            intent = pair["intent"]
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
        
        # Quality metrics
        avg_question_length = np.mean([len(pair["question"]) for pair in qa_pairs])
        avg_answer_length = np.mean([len(pair["answer"]) for pair in qa_pairs])
        
        report = {
            "total_qa_pairs": len(qa_pairs),
            "intent_distribution": intent_counts,
            "avg_question_length": avg_question_length,
            "avg_answer_length": avg_answer_length,
            "unique_questions": len(set(pair["question"] for pair in qa_pairs))
        }
        
        print("\n=== DATA QUALITY REPORT ===")
        print(f"Total Q&A pairs: {report['total_qa_pairs']}")
        print(f"Unique questions: {report['unique_questions']}")
        print(f"Avg question length: {report['avg_question_length']:.1f} chars")
        print(f"Avg answer length: {report['avg_answer_length']:.1f} chars")
        print("\nIntent distribution:")
        for intent, count in sorted(intent_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {intent}: {count} ({count/len(qa_pairs)*100:.1f}%)")
        
        return report

# Usage example
def main():
    processor = MultilingualVoiceDataProcessor()

    # Process all recordings in a directory
    audio_dir = "call_recordings"  # Put your audio files here
    conversations, qa_pairs = processor.process_all_recordings(audio_dir)

    # Analyze data quality
    processor.analyze_data_quality(qa_pairs)

    # Save training data
    processor.save_training_data(qa_pairs)

    print(f"\nProcessing complete! Generated {len(qa_pairs)} training examples.")
    print(f"Languages detected: {set(pair.get('primary_language', 'english') for pair in qa_pairs)}")

if __name__ == "__main__":
    main()