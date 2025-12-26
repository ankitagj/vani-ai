# Install additional packages:
# pip install transformers datasets torch accelerate sentence-transformers

import json
import pandas as pd
from transformers import (
    AutoTokenizer, AutoModelForSequenceClassification,
    AutoModelForCausalLM, TrainingArguments, Trainer,
    pipeline, DataCollatorForLanguageModeling
)
from datasets import Dataset
import torch
from sklearn.model_selection import train_test_split
import numpy as np
import logging
from sentence_transformers import SentenceTransformer
import os

class MultilingualConversationModelTrainer:
    def __init__(self, training_data_path="training_data.json"):
        """Initialize trainer with processed multilingual conversation data"""
        with open(training_data_path, 'r') as f:
            self.training_data = json.load(f)

        self.qa_pairs = self.training_data["qa_pairs"]
        print(f"Loaded {len(self.qa_pairs)} training examples")

        # Analyze language distribution
        self.language_stats = self._analyze_languages()
        print(f"Languages detected: {list(self.language_stats.keys())}")

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Models we'll train
        self.intent_classifier = None
        self.response_generator = None
        self.similarity_model = None

    def _analyze_languages(self):
        """Analyze language distribution in training data"""
        language_counts = {}
        for pair in self.qa_pairs:
            primary_lang = pair.get("primary_language", "english")
            language_counts[primary_lang] = language_counts.get(primary_lang, 0) + 1
        return language_counts
        
    def prepare_intent_classification_data(self):
        """Prepare data for training intent classifier"""
        # Extract questions and intents
        texts = [pair["question"] for pair in self.qa_pairs]
        labels = [pair["intent"] for pair in self.qa_pairs]
        
        # Create label mapping
        unique_labels = list(set(labels))
        self.label_to_id = {label: i for i, label in enumerate(unique_labels)}
        self.id_to_label = {i: label for label, i in self.label_to_id.items()}
        
        # Convert labels to IDs
        label_ids = [self.label_to_id[label] for label in labels]
        
        # Split data
        # Adjust test_size for small datasets to ensure all classes can be represented
        test_size = 0.2
        if len(texts) < 50 and len(texts) * test_size < len(unique_labels):
            test_size = len(unique_labels) / len(texts) + 0.05 # Ensure slightly more than minimum
            if test_size > 0.5: test_size = 0.5
            
        try:
            train_texts, val_texts, train_labels, val_labels = train_test_split(
                texts, label_ids, test_size=test_size, random_state=42, stratify=label_ids
            )
        except ValueError:
            # Fallback for very small datasets or if stratification fails
            print("Warning: Stratified split failed, falling back to random split")
            train_texts, val_texts, train_labels, val_labels = train_test_split(
                texts, label_ids, test_size=test_size, random_state=42, stratify=None
            )
        
        return {
            "train_texts": train_texts,
            "val_texts": val_texts,
            "train_labels": train_labels,
            "val_labels": val_labels,
            "num_labels": len(unique_labels)
        }
    
    def train_intent_classifier(self, model_name="distilbert-base-multilingual-cased"):
        """Train a multilingual model to classify customer intents"""
        print("Training multilingual intent classifier...")
        self.logger.info(f"Using model: {model_name}")

        # Prepare data
        data = self.prepare_intent_classification_data()

        # Load multilingual tokenizer and model
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(
            model_name, num_labels=data["num_labels"]
        )
        
        # Tokenize data
        def tokenize_function(examples):
            return tokenizer(examples["text"], truncation=True, padding=True)
        
        train_dataset = Dataset.from_dict({
            "text": data["train_texts"],
            "labels": data["train_labels"]
        }).map(tokenize_function, batched=True)
        
        val_dataset = Dataset.from_dict({
            "text": data["val_texts"], 
            "labels": data["val_labels"]
        }).map(tokenize_function, batched=True)
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir="./intent_classifier",
            num_train_epochs=3,
            per_device_train_batch_size=8,
            per_device_eval_batch_size=8,
            warmup_steps=100,
            weight_decay=0.01,
            logging_dir="./logs",
            logging_steps=10,
            eval_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
        )
        
        # Create trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            tokenizer=tokenizer,
        )
        
        # Train model
        trainer.train()
        
        # Save model
        trainer.save_model("./intent_classifier_final")
        tokenizer.save_pretrained("./intent_classifier_final")
        
        # Save label mappings
        with open("./intent_classifier_final/label_mapping.json", "w") as f:
            json.dump({
                "label_to_id": self.label_to_id,
                "id_to_label": self.id_to_label
            }, f)
        
        print("Intent classifier training complete!")
        return trainer
    
    def prepare_response_generation_data(self):
        """Prepare multilingual data for training response generator"""
        # Create conversation format for training
        conversations = []

        for pair in self.qa_pairs:
            # Format: "Customer: [question] Business: [answer]"
            # Include language context for better training
            primary_lang = pair.get('primary_language', 'english')
            conversation = f"Customer: {pair['question']} Business: {pair['answer']}"

            # Add language marker for multilingual training
            if primary_lang != 'english':
                conversation = f"[{primary_lang.upper()}] {conversation}"

            conversations.append(conversation)

        # Split data while maintaining language distribution
        langs = [pair.get('primary_language', 'english') for pair in self.qa_pairs]
        
        # Check if we can stratify (need at least 2 examples per class)
        from collections import Counter
        counts = Counter(langs)
        can_stratify = all(c >= 2 for c in counts.values())
        
        try:
            train_convs, val_convs = train_test_split(
                conversations, test_size=0.2, random_state=42,
                stratify=langs if can_stratify else None
            )
        except ValueError:
             # Fallback
             train_convs, val_convs = train_test_split(
                conversations, test_size=0.2, random_state=42,
                stratify=None
            )

        return train_convs, val_convs
    
    def train_response_generator(self, model_name="microsoft/DialoGPT-medium"):
        """Train a multilingual model to generate responses"""
        print("Training multilingual response generator...")
        self.logger.info(f"Using model: {model_name}")

        # Prepare data
        train_convs, val_convs = self.prepare_response_generation_data()

        # Load tokenizer and model
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(model_name)
        
        # Tokenize conversations
        def tokenize_function(examples):
            return tokenizer(
                examples["text"], 
                truncation=True, 
                padding=True, 
                max_length=512
            )
        
        train_dataset = Dataset.from_dict({"text": train_convs})
        train_dataset = train_dataset.map(tokenize_function, batched=True)
        
        val_dataset = Dataset.from_dict({"text": val_convs})
        val_dataset = val_dataset.map(tokenize_function, batched=True)
        
        # Data collator
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=tokenizer, mlm=False
        )
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir="./response_generator",
            num_train_epochs=3,
            per_device_train_batch_size=4,
            per_device_eval_batch_size=4,
            warmup_steps=100,
            weight_decay=0.01,
            logging_dir="./logs",
            logging_steps=10,
            eval_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
        )
        
        # Create trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            data_collator=data_collator,
            tokenizer=tokenizer,
        )
        
        # Train model
        trainer.train()
        
        # Save model
        trainer.save_model("./response_generator_final")
        tokenizer.save_pretrained("./response_generator_final")
        
        print("Response generator training complete!")
        return trainer
    
    def create_inference_pipeline(self):
        """Create inference pipeline using trained models"""
        # Load intent classifier
        intent_pipeline = pipeline(
            "text-classification",
            model="./intent_classifier_final",
            tokenizer="./intent_classifier_final"
        )
        
        # Load response generator
        response_pipeline = pipeline(
            "text-generation",
            model="./response_generator_final",
            tokenizer="./response_generator_final"
        )
        
        # Load label mapping
        with open("./intent_classifier_final/label_mapping.json", "r") as f:
            label_mapping = json.load(f)
        
        return intent_pipeline, response_pipeline, label_mapping
    
    def test_models(self, test_questions=None):
        """Test the trained models with sample questions"""
        if test_questions is None:
            test_questions = [
                "Are you open right now?",
                "What time do you close?",
                "How long is the wait for a table?",
                "Do you have vegan options?",
                "Can I make a reservation?"
            ]
        
        try:
            intent_pipeline, response_pipeline, label_mapping = self.create_inference_pipeline()
            
            print("\n=== MODEL TESTING ===")
            for question in test_questions:
                # Classify intent
                intent_result = intent_pipeline(question)
                predicted_intent = intent_result[0]["label"]
                confidence = intent_result[0]["score"]
                
                # Generate response
                prompt = f"Customer: {question} Restaurant:"
                response_result = response_pipeline(
                    prompt, 
                    max_length=len(prompt.split()) + 30,
                    num_return_sequences=1,
                    temperature=0.7,
                    do_sample=True
                )
                
                generated_text = response_result[0]["generated_text"]
                # Extract just the restaurant response
                restaurant_response = generated_text.split("Restaurant:")[-1].strip()
                
                print(f"\nQ: {question}")
                print(f"Intent: {predicted_intent} (confidence: {confidence:.2f})")
                print(f"A: {restaurant_response}")
        
        except Exception as e:
            print(f"Error during testing: {str(e)}")
            print("Make sure both models are trained first!")
    
    def generate_model_stats(self):
        """Generate statistics about the trained models"""
        # Intent distribution
        intent_counts = {}
        for pair in self.qa_pairs:
            intent = pair["intent"]
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
        
        # Response length analysis
        response_lengths = [len(pair["answer"]) for pair in self.qa_pairs]
        
        stats = {
            "total_training_examples": len(self.qa_pairs),
            "intent_distribution": intent_counts,
            "avg_response_length": np.mean(response_lengths),
            "unique_intents": len(intent_counts)
        }
        
        print("\n=== MODEL STATISTICS ===")
        print(f"Training examples: {stats['total_training_examples']}")
        print(f"Unique intents: {stats['unique_intents']}")
        print(f"Average response length: {stats['avg_response_length']:.1f} characters")
        print("\nIntent distribution:")
        for intent, count in sorted(intent_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {intent}: {count} examples")
        
        return stats

# Usage example
def main():
    # Make sure you've run the MultilingualVoiceDataProcessor first to generate training_data.json
    trainer = MultilingualConversationModelTrainer("training_data.json")

    # Train both models
    print("Starting multilingual model training...")
    trainer.train_intent_classifier()
    trainer.train_response_generator()

    # Test the models
    trainer.test_models()

    # Generate statistics
    trainer.generate_model_stats()

    print("\nTraining complete! Models saved to ./intent_classifier_final and ./response_generator_final")

if __name__ == "__main__":
    main()