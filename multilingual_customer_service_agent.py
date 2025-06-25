# Install required packages:
# pip install transformers torch sentence-transformers langdetect googletrans flask

import json
import torch
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification, AutoModelForCausalLM
from langdetect import detect, DetectorFactory
from googletrans import Translator
import logging
import numpy as np
from sentence_transformers import SentenceTransformer
import re
from datetime import datetime
import os

# Set seed for consistent language detection
DetectorFactory.seed = 0

class MultilingualCustomerServiceAgent:
    def __init__(self, 
                 intent_model_path="./intent_classifier_final",
                 response_model_path="./response_generator_final",
                 training_data_path="training_data.json"):
        """Initialize the multilingual customer service agent"""
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize translator
        self.translator = Translator()
        
        # Load training data for context
        self.training_data = self._load_training_data(training_data_path)
        
        # Load models
        self.intent_pipeline = None
        self.response_pipeline = None
        self.similarity_model = None
        self.label_mapping = None
        
        # Load models if they exist
        self._load_models(intent_model_path, response_model_path)
        
        # Language detection patterns
        self.language_patterns = self._initialize_language_patterns()
        
    def _load_training_data(self, training_data_path):
        """Load training data for context and fallback responses"""
        try:
            with open(training_data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning(f"Training data not found at {training_data_path}")
            return {"qa_pairs": []}
    
    def _load_models(self, intent_model_path, response_model_path):
        """Load trained models"""
        try:
            # Load intent classifier
            if os.path.exists(intent_model_path):
                self.intent_pipeline = pipeline(
                    "text-classification",
                    model=intent_model_path,
                    tokenizer=intent_model_path
                )
                
                # Load label mapping
                label_mapping_path = os.path.join(intent_model_path, "label_mapping.json")
                if os.path.exists(label_mapping_path):
                    with open(label_mapping_path, 'r') as f:
                        self.label_mapping = json.load(f)
                
                self.logger.info("Intent classifier loaded successfully")
            
            # Load response generator
            if os.path.exists(response_model_path):
                self.response_pipeline = pipeline(
                    "text-generation",
                    model=response_model_path,
                    tokenizer=response_model_path
                )
                self.logger.info("Response generator loaded successfully")
            
            # Load similarity model for fallback
            self.similarity_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            self.logger.info("Similarity model loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error loading models: {str(e)}")
    
    def _initialize_language_patterns(self):
        """Initialize language-specific patterns"""
        return {
            'english': {
                'greetings': ['hello', 'hi', 'good morning', 'good afternoon', 'good evening'],
                'thanks': ['thank you', 'thanks', 'appreciate'],
                'goodbye': ['bye', 'goodbye', 'see you', 'have a good day']
            },
            'hindi': {
                'greetings': ['namaste', 'namaskar', 'hello', 'hi'],
                'thanks': ['dhanyawad', 'shukriya', 'thank you'],
                'goodbye': ['alvida', 'bye', 'phir milenge']
            },
            'kannada': {
                'greetings': ['namaskara', 'vanakkam', 'hello'],
                'thanks': ['dhanyavada', 'thank you'],
                'goodbye': ['bye', 'nodona', 'phir sigona']
            }
        }
    
    def detect_language(self, text):
        """Detect the language of input text"""
        try:
            detected_lang = detect(text)
            lang_mapping = {
                'en': 'english',
                'hi': 'hindi',
                'kn': 'kannada'
            }
            return lang_mapping.get(detected_lang, 'english')
        except:
            # Fallback to script-based detection
            if any(ord(char) >= 0x0900 and ord(char) <= 0x097F for char in text):
                return 'hindi'
            elif any(ord(char) >= 0x0C80 and ord(char) <= 0x0CFF for char in text):
                return 'kannada'
            else:
                return 'english'
    
    def classify_intent(self, text):
        """Classify the intent of customer query"""
        if not self.intent_pipeline:
            return {"intent": "general", "confidence": 0.5}
        
        try:
            result = self.intent_pipeline(text)
            return {
                "intent": result[0]["label"],
                "confidence": result[0]["score"]
            }
        except Exception as e:
            self.logger.error(f"Error in intent classification: {str(e)}")
            return {"intent": "general", "confidence": 0.5}
    
    def find_similar_response(self, query, language):
        """Find similar response from training data using semantic similarity"""
        if not self.training_data.get("qa_pairs") or not self.similarity_model:
            return None
        
        try:
            # Get embeddings for the query
            query_embedding = self.similarity_model.encode([query])
            
            # Get embeddings for all training questions
            training_questions = []
            training_answers = []
            
            for pair in self.training_data["qa_pairs"]:
                # Prefer same language pairs
                pair_lang = pair.get("primary_language", "english")
                if pair_lang == language or language == "english":
                    training_questions.append(pair["question"])
                    training_answers.append(pair["answer"])
            
            if not training_questions:
                return None
            
            # Calculate similarities
            question_embeddings = self.similarity_model.encode(training_questions)
            similarities = np.dot(query_embedding, question_embeddings.T)[0]
            
            # Find best match
            best_idx = np.argmax(similarities)
            best_similarity = similarities[best_idx]
            
            if best_similarity > 0.7:  # Threshold for similarity
                return {
                    "answer": training_answers[best_idx],
                    "similarity": float(best_similarity),
                    "matched_question": training_questions[best_idx]
                }
            
        except Exception as e:
            self.logger.error(f"Error in similarity search: {str(e)}")
        
        return None
    
    def generate_response(self, query, intent_info, language):
        """Generate response using trained model or fallback methods"""
        
        # Try model-based generation first
        if self.response_pipeline:
            try:
                # Format prompt based on language
                if language != 'english':
                    prompt = f"[{language.upper()}] Customer: {query} Business:"
                else:
                    prompt = f"Customer: {query} Business:"
                
                result = self.response_pipeline(
                    prompt,
                    max_length=len(prompt.split()) + 50,
                    num_return_sequences=1,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.response_pipeline.tokenizer.eos_token_id
                )
                
                generated_text = result[0]["generated_text"]
                # Extract just the business response
                if "Business:" in generated_text:
                    response = generated_text.split("Business:")[-1].strip()
                    if response and len(response) > 10:  # Valid response
                        return {
                            "response": response,
                            "method": "model_generation",
                            "confidence": 0.8
                        }
                
            except Exception as e:
                self.logger.error(f"Error in model generation: {str(e)}")
        
        # Fallback to similarity-based response
        similar_response = self.find_similar_response(query, language)
        if similar_response:
            return {
                "response": similar_response["answer"],
                "method": "similarity_match",
                "confidence": similar_response["similarity"],
                "matched_question": similar_response["matched_question"]
            }
        
        # Final fallback - generic responses
        return self._get_fallback_response(intent_info["intent"], language)
    
    def _get_fallback_response(self, intent, language):
        """Get fallback response based on intent and language"""
        fallback_responses = {
            'english': {
                'hours': "I'd be happy to help with our hours. Could you please call us directly for the most current information?",
                'availability': "For table availability and reservations, please call us directly and we'll be glad to assist you.",
                'menu': "I'd love to tell you about our menu. Please call us and we can discuss our current offerings.",
                'location': "For directions and location information, please call us and we'll help you find us.",
                'pricing': "For pricing information, please call us directly and we'll provide you with current rates.",
                'general': "Thank you for contacting us. Please call us directly and we'll be happy to assist you with your inquiry."
            },
            'hindi': {
                'hours': "Main aapko hamare samay ke baare mein batane mein khush hoon. Kripaya hamen seedhe call kariye.",
                'availability': "Table ki uplabdhata ke liye, kripaya hamen call kariye.",
                'menu': "Menu ke baare mein jaanne ke liye, kripaya hamen call kariye.",
                'location': "Sthaan ki jaankaari ke liye, kripaya hamen call kariye.",
                'pricing': "Kimat ki jaankaari ke liye, kripaya hamen call kariye.",
                'general': "Sampark karne ke liye dhanyawad. Kripaya hamen call kariye."
            },
            'kannada': {
                'hours': "Naavu samaya bagge tilisalu khushi. Dayavittu namage call maadi.",
                'availability': "Table siguvudakke, dayavittu namage call maadi.",
                'menu': "Menu bagge tiliyalu, dayavittu namage call maadi.",
                'location': "Stala jaankaari ge, dayavittu namage call maadi.",
                'pricing': "Bele jaankaari ge, dayavittu namage call maadi.",
                'general': "Sampark madidakke dhanyavaada. Dayavittu namage call maadi."
            }
        }
        
        responses = fallback_responses.get(language, fallback_responses['english'])
        response = responses.get(intent, responses['general'])
        
        return {
            "response": response,
            "method": "fallback",
            "confidence": 0.6
        }
    
    def process_customer_query(self, query):
        """Main method to process customer query and generate response"""
        
        # Log the query
        self.logger.info(f"Processing query: {query}")
        
        # Detect language
        language = self.detect_language(query)
        self.logger.info(f"Detected language: {language}")
        
        # Classify intent
        intent_info = self.classify_intent(query)
        self.logger.info(f"Classified intent: {intent_info}")
        
        # Generate response
        response_info = self.generate_response(query, intent_info, language)
        
        # Prepare final response
        result = {
            "query": query,
            "detected_language": language,
            "intent": intent_info,
            "response": response_info["response"],
            "generation_method": response_info["method"],
            "confidence": response_info.get("confidence", 0.5),
            "timestamp": datetime.now().isoformat()
        }
        
        # Add matched question if available
        if "matched_question" in response_info:
            result["matched_question"] = response_info["matched_question"]
        
        self.logger.info(f"Generated response using {response_info['method']}")
        
        return result

# Example usage and testing
def main():
    # Initialize the agent
    agent = MultilingualCustomerServiceAgent()
    
    # Test queries in different languages
    test_queries = [
        "What time do you open?",
        "Aap kab khulte hain?",  # Hindi
        "Yaavaga khali maadtira?",  # Kannada
        "Do you have tables available?",
        "Kya table available hai?",  # Hindi
        "Table sigutte?",  # Kannada
    ]
    
    print("=== MULTILINGUAL CUSTOMER SERVICE AGENT TEST ===\n")
    
    for query in test_queries:
        print(f"Customer: {query}")
        result = agent.process_customer_query(query)
        print(f"Agent ({result['detected_language']}): {result['response']}")
        print(f"Intent: {result['intent']['intent']} (confidence: {result['intent']['confidence']:.2f})")
        print(f"Method: {result['generation_method']}")
        print("-" * 50)

if __name__ == "__main__":
    main()
