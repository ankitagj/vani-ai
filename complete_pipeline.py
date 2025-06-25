#!/usr/bin/env python3
"""
Complete Multilingual Customer Service Agent Pipeline

This script orchestrates the entire process:
1. Process audio recordings to extract Q&A pairs
2. Train multilingual models on the extracted data
3. Deploy the trained agent for real-time customer service

Usage:
    python complete_pipeline.py --mode [process|train|serve|all]
"""

import argparse
import os
import sys
import logging
from datetime import datetime

# Import our custom modules
from voice_data_processor import MultilingualVoiceDataProcessor
from models.conversation_model_trainer import MultilingualConversationModelTrainer
from multilingual_customer_service_agent import MultilingualCustomerServiceAgent

class CustomerServicePipeline:
    def __init__(self, audio_dir="call_recordings", output_dir="models"):
        """Initialize the complete pipeline"""
        self.audio_dir = audio_dir
        self.output_dir = output_dir
        self.training_data_file = "training_data.json"
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('pipeline.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Create necessary directories
        os.makedirs(self.audio_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs("processed_audio", exist_ok=True)
        
    def process_audio_recordings(self):
        """Step 1: Process audio recordings to extract training data"""
        self.logger.info("=" * 60)
        self.logger.info("STEP 1: PROCESSING AUDIO RECORDINGS")
        self.logger.info("=" * 60)
        
        # Check if audio files exist
        audio_files = []
        audio_extensions = ['.wav', '.mp3', '.m4a', '.flac', '.ogg']
        
        for ext in audio_extensions:
            audio_files.extend([f for f in os.listdir(self.audio_dir) if f.endswith(ext)])
        
        if not audio_files:
            self.logger.warning(f"No audio files found in {self.audio_dir}")
            self.logger.info("Please add your call recordings to the call_recordings directory")
            self.logger.info("Supported formats: .wav, .mp3, .m4a, .flac, .ogg")
            return False
        
        self.logger.info(f"Found {len(audio_files)} audio files to process")
        
        # Initialize processor
        processor = MultilingualVoiceDataProcessor()
        
        try:
            # Process all recordings
            conversations, qa_pairs = processor.process_all_recordings(self.audio_dir)
            
            if not qa_pairs:
                self.logger.error("No Q&A pairs extracted from audio files")
                return False
            
            # Analyze data quality
            processor.analyze_data_quality(qa_pairs)
            
            # Save training data
            processor.save_training_data(qa_pairs, self.training_data_file)
            
            self.logger.info(f"Successfully processed {len(audio_files)} files")
            self.logger.info(f"Extracted {len(qa_pairs)} Q&A pairs")
            
            # Show language distribution
            languages = {}
            for pair in qa_pairs:
                lang = pair.get('primary_language', 'english')
                languages[lang] = languages.get(lang, 0) + 1
            
            self.logger.info("Language distribution:")
            for lang, count in languages.items():
                self.logger.info(f"  {lang}: {count} pairs ({count/len(qa_pairs)*100:.1f}%)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing audio recordings: {str(e)}")
            return False
    
    def train_models(self):
        """Step 2: Train multilingual models on extracted data"""
        self.logger.info("=" * 60)
        self.logger.info("STEP 2: TRAINING MULTILINGUAL MODELS")
        self.logger.info("=" * 60)
        
        # Check if training data exists
        if not os.path.exists(self.training_data_file):
            self.logger.error(f"Training data not found: {self.training_data_file}")
            self.logger.info("Please run audio processing first")
            return False
        
        try:
            # Initialize trainer
            trainer = MultilingualConversationModelTrainer(self.training_data_file)
            
            # Train intent classifier
            self.logger.info("Training intent classifier...")
            trainer.train_intent_classifier()
            
            # Train response generator
            self.logger.info("Training response generator...")
            trainer.train_response_generator()
            
            # Test the models
            self.logger.info("Testing trained models...")
            trainer.test_models()
            
            # Generate statistics
            trainer.generate_model_stats()
            
            self.logger.info("Model training completed successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"Error training models: {str(e)}")
            return False
    
    def serve_agent(self):
        """Step 3: Deploy the trained agent for customer service"""
        self.logger.info("=" * 60)
        self.logger.info("STEP 3: DEPLOYING CUSTOMER SERVICE AGENT")
        self.logger.info("=" * 60)
        
        # Check if models exist
        intent_model_path = "./intent_classifier_final"
        response_model_path = "./response_generator_final"
        
        if not os.path.exists(intent_model_path) or not os.path.exists(response_model_path):
            self.logger.warning("Trained models not found. Agent will use fallback responses.")
        
        try:
            # Initialize agent
            agent = MultilingualCustomerServiceAgent(
                intent_model_path=intent_model_path,
                response_model_path=response_model_path,
                training_data_path=self.training_data_file
            )
            
            self.logger.info("Customer Service Agent is ready!")
            self.logger.info("You can now use the agent to handle customer queries")
            
            # Interactive mode
            self._interactive_mode(agent)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error deploying agent: {str(e)}")
            return False
    
    def _interactive_mode(self, agent):
        """Interactive mode for testing the agent"""
        print("\n" + "=" * 60)
        print("INTERACTIVE CUSTOMER SERVICE AGENT")
        print("=" * 60)
        print("Type customer queries to test the agent")
        print("Supported languages: English, Hindi, Kannada")
        print("Type 'quit' to exit")
        print("-" * 60)
        
        while True:
            try:
                query = input("\nCustomer: ").strip()
                
                if query.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye!")
                    break
                
                if not query:
                    continue
                
                # Process the query
                result = agent.process_customer_query(query)
                
                # Display response
                print(f"Agent ({result['detected_language']}): {result['response']}")
                print(f"[Intent: {result['intent']['intent']} | "
                      f"Confidence: {result['intent']['confidence']:.2f} | "
                      f"Method: {result['generation_method']}]")
                
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {str(e)}")
    
    def run_complete_pipeline(self):
        """Run the complete pipeline from start to finish"""
        self.logger.info("STARTING COMPLETE MULTILINGUAL CUSTOMER SERVICE PIPELINE")
        self.logger.info(f"Timestamp: {datetime.now().isoformat()}")
        
        # Step 1: Process audio recordings
        if not self.process_audio_recordings():
            self.logger.error("Pipeline failed at audio processing step")
            return False
        
        # Step 2: Train models
        if not self.train_models():
            self.logger.error("Pipeline failed at model training step")
            return False
        
        # Step 3: Deploy agent
        if not self.serve_agent():
            self.logger.error("Pipeline failed at agent deployment step")
            return False
        
        self.logger.info("PIPELINE COMPLETED SUCCESSFULLY!")
        return True

def main():
    parser = argparse.ArgumentParser(description="Multilingual Customer Service Agent Pipeline")
    parser.add_argument(
        "--mode", 
        choices=["process", "train", "serve", "all"],
        default="all",
        help="Pipeline mode: process audio, train models, serve agent, or run all steps"
    )
    parser.add_argument(
        "--audio-dir",
        default="call_recordings",
        help="Directory containing audio recordings"
    )
    parser.add_argument(
        "--output-dir",
        default="models",
        help="Directory to save trained models"
    )
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = CustomerServicePipeline(
        audio_dir=args.audio_dir,
        output_dir=args.output_dir
    )
    
    # Run based on mode
    success = False
    
    if args.mode == "process":
        success = pipeline.process_audio_recordings()
    elif args.mode == "train":
        success = pipeline.train_models()
    elif args.mode == "serve":
        success = pipeline.serve_agent()
    elif args.mode == "all":
        success = pipeline.run_complete_pipeline()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
