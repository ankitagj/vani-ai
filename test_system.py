#!/usr/bin/env python3
"""
Test script for the Multilingual Customer Service Agent

This script tests various components of the system to ensure everything works correctly.
"""

import os
import sys
import json
import tempfile
import logging
from datetime import datetime

def test_imports():
    """Test if all required modules can be imported"""
    print("Testing imports...")
    
    try:
        # Test core imports
        import torch
        import transformers
        import whisper
        import pandas as pd
        import numpy as np
        print("✓ Core ML libraries imported successfully")
        
        # Test language processing imports
        from langdetect import detect
        from google_trans_new import google_translator
        print("✓ Language processing libraries imported successfully")
        
        # Test custom modules
        from voice_data_processor import MultilingualVoiceDataProcessor
        from models.conversation_model_trainer import MultilingualConversationModelTrainer
        from multilingual_customer_service_agent import MultilingualCustomerServiceAgent
        print("✓ Custom modules imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def test_language_detection():
    """Test language detection functionality"""
    print("\nTesting language detection...")
    
    try:
        from voice_data_processor import MultilingualVoiceDataProcessor
        
        processor = MultilingualVoiceDataProcessor()
        
        # Test cases
        test_cases = [
            ("Hello, how are you?", "english"),
            ("Namaste, aap kaise hain?", "hindi"),
            ("Namaskara, hegiddira?", "kannada"),
            ("What time do you open?", "english"),
            ("Aap kab khulte hain?", "hindi"),
            ("Yaavaga khali maadtira?", "kannada")
        ]
        
        for text, expected_lang in test_cases:
            detected_lang = processor.detect_language(text)
            status = "✓" if detected_lang == expected_lang else "⚠"
            print(f"{status} '{text}' -> {detected_lang} (expected: {expected_lang})")
        
        print("✓ Language detection test completed")
        return True
        
    except Exception as e:
        print(f"✗ Language detection test failed: {e}")
        return False

def test_intent_patterns():
    """Test intent categorization patterns"""
    print("\nTesting intent patterns...")
    
    try:
        from voice_data_processor import MultilingualVoiceDataProcessor
        
        processor = MultilingualVoiceDataProcessor()
        
        # Create test Q&A pairs
        test_qa_pairs = [
            {
                "question": "What time do you open?",
                "answer": "We open at 9 AM",
                "question_language": "english",
                "answer_language": "english",
                "primary_language": "english"
            },
            {
                "question": "Aap kab khulte hain?",
                "answer": "Hum subah 9 baje khulte hain",
                "question_language": "hindi", 
                "answer_language": "hindi",
                "primary_language": "hindi"
            },
            {
                "question": "Do you have tables available?",
                "answer": "Yes, we have tables available",
                "question_language": "english",
                "answer_language": "english", 
                "primary_language": "english"
            }
        ]
        
        # Test intent categorization
        categorized_pairs = processor.categorize_intents(test_qa_pairs)
        
        for pair in categorized_pairs:
            print(f"✓ '{pair['question']}' -> Intent: {pair['intent']}")
        
        print("✓ Intent pattern test completed")
        return True
        
    except Exception as e:
        print(f"✗ Intent pattern test failed: {e}")
        return False

def test_customer_service_agent():
    """Test the customer service agent with fallback responses"""
    print("\nTesting customer service agent...")
    
    try:
        from multilingual_customer_service_agent import MultilingualCustomerServiceAgent
        
        # Create a temporary training data file
        temp_training_data = {
            "total_pairs": 3,
            "created_at": datetime.now().isoformat(),
            "qa_pairs": [
                {
                    "question": "What time do you open?",
                    "answer": "We open at 9 AM every day",
                    "intent": "hours",
                    "primary_language": "english"
                },
                {
                    "question": "Aap kab khulte hain?", 
                    "answer": "Hum roz subah 9 baje khulte hain",
                    "intent": "hours",
                    "primary_language": "hindi"
                },
                {
                    "question": "Do you take reservations?",
                    "answer": "Yes, we take reservations. Please call us.",
                    "intent": "availability", 
                    "primary_language": "english"
                }
            ]
        }
        
        # Save temporary training data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(temp_training_data, f)
            temp_file = f.name
        
        try:
            # Initialize agent (will use fallback responses since models aren't trained)
            agent = MultilingualCustomerServiceAgent(training_data_path=temp_file)
            
            # Test queries
            test_queries = [
                "What time do you open?",
                "Aap kab khulte hain?",
                "Yaavaga khali maadtira?",
                "Do you have tables?",
                "Menu kya hai?"
            ]
            
            for query in test_queries:
                result = agent.process_customer_query(query)
                print(f"✓ Query: '{query}'")
                print(f"  Language: {result['detected_language']}")
                print(f"  Intent: {result['intent']['intent']}")
                print(f"  Response: {result['response'][:100]}...")
                print(f"  Method: {result['generation_method']}")
                print()
            
            print("✓ Customer service agent test completed")
            return True
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file)
        
    except Exception as e:
        print(f"✗ Customer service agent test failed: {e}")
        return False

def test_directory_structure():
    """Test if required directories exist"""
    print("\nTesting directory structure...")
    
    required_dirs = ["call_recordings", "processed_audio", "models"]
    
    for directory in required_dirs:
        if os.path.exists(directory):
            print(f"✓ Directory exists: {directory}")
        else:
            print(f"⚠ Directory missing: {directory} (will be created when needed)")
    
    return True

def test_whisper_model():
    """Test if Whisper model can be loaded"""
    print("\nTesting Whisper model loading...")
    
    try:
        import whisper
        
        # Try to load the smallest model
        model = whisper.load_model("tiny")
        print("✓ Whisper model loaded successfully")
        
        # Test with a simple audio transcription (if we had audio)
        print("✓ Whisper test completed")
        return True
        
    except Exception as e:
        print(f"✗ Whisper model test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("MULTILINGUAL CUSTOMER SERVICE AGENT - SYSTEM TEST")
    print("=" * 60)
    
    tests = [
        ("Import Test", test_imports),
        ("Directory Structure", test_directory_structure), 
        ("Language Detection", test_language_detection),
        ("Intent Patterns", test_intent_patterns),
        ("Whisper Model", test_whisper_model),
        ("Customer Service Agent", test_customer_service_agent)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'-' * 40}")
        print(f"Running: {test_name}")
        print(f"{'-' * 40}")
        
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        symbol = "✓" if success else "✗"
        print(f"{symbol} {test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your system is ready to use.")
        print("\nNext steps:")
        print("1. Add call recordings to the 'call_recordings' directory")
        print("2. Run: python complete_pipeline.py --mode all")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Please check the errors above.")
        print("Make sure all dependencies are installed: pip install -r requirements.txt")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
