# Legacy Code - Archived

This directory contains code from the original ML-based approach that is no longer used in the current system.

## What's Here

- **`conversation_model_trainer.py`** - Original intent classification model trainer
- **`multilingual_customer_service_agent.py`** - Original ML-based agent
- **`complete_pipeline.py`** - Training pipeline for ML model
- **`create_sample_data.py`** - Sample data generator for training
- **`debug_tokenizer.py`** - Tokenizer debugging utility
- **`voice_data_processor.py`** - Voice data preprocessing
- **`training_data.json`** - Sample training data

## Why Archived?

The project pivoted from a traditional ML classification approach to using **Google Gemini AI** directly. This provides:

1. ✅ Better natural language understanding
2. ✅ Native multilingual support (Hindi/English)
3. ✅ No training required
4. ✅ More conversational responses
5. ✅ Easier to update with new information

## Current Architecture

The system now uses:
- **`query_transcripts.py`** - Gemini-based conversational agent
- **Transcript files** - Real call recordings as knowledge base
- **No ML training** - Direct API calls to Gemini

## If You Need This Code

This code is preserved for reference but is not part of the active system. If you want to revert to the ML approach, you would need to:

1. Move files back to root directory
2. Train the model with `complete_pipeline.py`
3. Update `app.py` to use the trained model
4. Modify frontend to work with classification-based responses

**Note**: The current Gemini-based approach is recommended for better performance and flexibility.
