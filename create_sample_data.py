#!/usr/bin/env python3
"""
Create sample training data for testing the Multilingual Customer Service Agent

This script creates sample Q&A pairs in multiple languages to test the system
when you don't have actual call recordings yet.
"""

import json
from datetime import datetime
import os

def create_sample_training_data():
    """Create sample multilingual Q&A pairs"""
    
    sample_qa_pairs = [
        # English - Restaurant/Business Hours
        {
            "question": "What time do you open?",
            "answer": "We open at 9 AM every day from Monday to Sunday.",
            "intent": "hours",
            "question_language": "english",
            "answer_language": "english", 
            "primary_language": "english",
            "intent_confidence": 1,
            "context": {
                "conversation_id": "sample_001",
                "timestamp": datetime.now().isoformat()
            }
        },
        {
            "question": "What time do you close?",
            "answer": "We close at 10 PM on weekdays and 11 PM on weekends.",
            "intent": "hours",
            "question_language": "english",
            "answer_language": "english",
            "primary_language": "english", 
            "intent_confidence": 1,
            "context": {
                "conversation_id": "sample_002",
                "timestamp": datetime.now().isoformat()
            }
        },
        
        # Hindi - Restaurant/Business Hours
        {
            "question": "Aap kab khulte hain?",
            "answer": "Hum roz subah 9 baje khulte hain, somwar se raviwar tak.",
            "intent": "hours",
            "question_language": "hindi",
            "answer_language": "hindi",
            "primary_language": "hindi",
            "intent_confidence": 1,
            "context": {
                "conversation_id": "sample_003", 
                "timestamp": datetime.now().isoformat()
            }
        },
        {
            "question": "Kitne baje band karte hain?",
            "answer": "Hum weekdays mein raat 10 baje aur weekends mein 11 baje band karte hain.",
            "intent": "hours",
            "question_language": "hindi",
            "answer_language": "hindi",
            "primary_language": "hindi",
            "intent_confidence": 1,
            "context": {
                "conversation_id": "sample_004",
                "timestamp": datetime.now().isoformat()
            }
        },
        
        # Kannada - Restaurant/Business Hours  
        {
            "question": "Yaavaga khali maadtira?",
            "answer": "Naavu ella dina belige 9 gantege khali maadteve, somavaara ninda ravivaara varegu.",
            "intent": "hours",
            "question_language": "kannada",
            "answer_language": "kannada",
            "primary_language": "kannada",
            "intent_confidence": 1,
            "context": {
                "conversation_id": "sample_005",
                "timestamp": datetime.now().isoformat()
            }
        },
        
        # English - Table Availability
        {
            "question": "Do you have tables available right now?",
            "answer": "Yes, we have tables available. Would you like to make a reservation?",
            "intent": "availability",
            "question_language": "english",
            "answer_language": "english",
            "primary_language": "english",
            "intent_confidence": 1,
            "context": {
                "conversation_id": "sample_006",
                "timestamp": datetime.now().isoformat()
            }
        },
        {
            "question": "How long is the wait for a table?",
            "answer": "The current wait time is about 15-20 minutes for a table of 4.",
            "intent": "availability", 
            "question_language": "english",
            "answer_language": "english",
            "primary_language": "english",
            "intent_confidence": 1,
            "context": {
                "conversation_id": "sample_007",
                "timestamp": datetime.now().isoformat()
            }
        },
        
        # Hindi - Table Availability
        {
            "question": "Kya table available hai?",
            "answer": "Haan, hamare paas table available hai. Kya aap reservation karna chahte hain?",
            "intent": "availability",
            "question_language": "hindi",
            "answer_language": "hindi", 
            "primary_language": "hindi",
            "intent_confidence": 1,
            "context": {
                "conversation_id": "sample_008",
                "timestamp": datetime.now().isoformat()
            }
        },
        
        # English - Menu
        {
            "question": "What's on your menu today?",
            "answer": "We have a variety of dishes including North Indian, South Indian, and Chinese cuisine. Would you like me to tell you about our specials?",
            "intent": "menu",
            "question_language": "english",
            "answer_language": "english",
            "primary_language": "english", 
            "intent_confidence": 1,
            "context": {
                "conversation_id": "sample_009",
                "timestamp": datetime.now().isoformat()
            }
        },
        {
            "question": "Do you have vegetarian options?",
            "answer": "Yes, we have many vegetarian options including dal, paneer dishes, and vegetable curries.",
            "intent": "menu",
            "question_language": "english",
            "answer_language": "english",
            "primary_language": "english",
            "intent_confidence": 1,
            "context": {
                "conversation_id": "sample_010",
                "timestamp": datetime.now().isoformat()
            }
        },
        
        # Hindi - Menu
        {
            "question": "Aaj menu mein kya hai?",
            "answer": "Hamare paas North Indian, South Indian aur Chinese khana hai. Kya aap hamare special dishes ke baare mein sunna chahenge?",
            "intent": "menu",
            "question_language": "hindi",
            "answer_language": "hindi",
            "primary_language": "hindi",
            "intent_confidence": 1,
            "context": {
                "conversation_id": "sample_011",
                "timestamp": datetime.now().isoformat()
            }
        },
        
        # English - Location
        {
            "question": "Where are you located?",
            "answer": "We are located on MG Road, near the metro station. You can find us easily using Google Maps.",
            "intent": "location",
            "question_language": "english",
            "answer_language": "english",
            "primary_language": "english",
            "intent_confidence": 1,
            "context": {
                "conversation_id": "sample_012",
                "timestamp": datetime.now().isoformat()
            }
        },
        
        # English - Pricing
        {
            "question": "What are your prices like?",
            "answer": "Our prices are very reasonable. Main dishes start from 150 rupees and go up to 400 rupees.",
            "intent": "pricing",
            "question_language": "english",
            "answer_language": "english",
            "primary_language": "english",
            "intent_confidence": 1,
            "context": {
                "conversation_id": "sample_013",
                "timestamp": datetime.now().isoformat()
            }
        },
        
        # English - Services
        {
            "question": "Do you provide home delivery?",
            "answer": "Yes, we provide home delivery within 5 km radius. Delivery charges are 30 rupees.",
            "intent": "services",
            "question_language": "english",
            "answer_language": "english",
            "primary_language": "english",
            "intent_confidence": 1,
            "context": {
                "conversation_id": "sample_014",
                "timestamp": datetime.now().isoformat()
            }
        },
        
        # Mixed language examples
        {
            "question": "Phone number kya hai?",
            "answer": "Hamara phone number hai 080-12345678. Aap call kar sakte hain.",
            "intent": "contact",
            "question_language": "hindi",
            "answer_language": "hindi",
            "primary_language": "hindi",
            "intent_confidence": 1,
            "context": {
                "conversation_id": "sample_015",
                "timestamp": datetime.now().isoformat()
            }
        }
    ]
    
    # Create the training data structure
    training_data = {
        "total_pairs": len(sample_qa_pairs),
        "created_at": datetime.now().isoformat(),
        "qa_pairs": sample_qa_pairs,
        "metadata": {
            "source": "sample_data_generator",
            "languages": ["english", "hindi", "kannada"],
            "intents": ["hours", "availability", "menu", "location", "pricing", "services", "contact"],
            "description": "Sample multilingual Q&A pairs for testing the customer service agent"
        }
    }
    
    return training_data

def main():
    """Create and save sample training data"""
    print("Creating sample multilingual training data...")
    
    # Create sample data
    training_data = create_sample_training_data()
    
    # Save to JSON file
    output_file = "sample_training_data.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(training_data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Sample training data saved to {output_file}")
    print(f"✓ Created {training_data['total_pairs']} Q&A pairs")
    
    # Show language distribution
    languages = {}
    for pair in training_data['qa_pairs']:
        lang = pair['primary_language']
        languages[lang] = languages.get(lang, 0) + 1
    
    print("\nLanguage distribution:")
    for lang, count in languages.items():
        percentage = (count / training_data['total_pairs']) * 100
        print(f"  {lang}: {count} pairs ({percentage:.1f}%)")
    
    # Show intent distribution
    intents = {}
    for pair in training_data['qa_pairs']:
        intent = pair['intent']
        intents[intent] = intents.get(intent, 0) + 1
    
    print("\nIntent distribution:")
    for intent, count in intents.items():
        percentage = (count / training_data['total_pairs']) * 100
        print(f"  {intent}: {count} pairs ({percentage:.1f}%)")
    
    print(f"\nYou can now test the system using:")
    print(f"python complete_pipeline.py --mode train")
    print(f"# (Use sample_training_data.json instead of processing audio)")
    
    print(f"\nOr test the agent directly:")
    print(f"python -c \"")
    print(f"from multilingual_customer_service_agent import MultilingualCustomerServiceAgent")
    print(f"agent = MultilingualCustomerServiceAgent(training_data_path='sample_training_data.json')")
    print(f"result = agent.process_customer_query('What time do you open?')")
    print(f"print(result['response'])")
    print(f"\"")

if __name__ == "__main__":
    main()
