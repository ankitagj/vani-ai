# Multilingual Customer Service Agent

An AI-powered customer service agent that learns from call recordings in English, Hindi, and Kannada to provide automated responses that mimic how business owners would respond to customer queries.

## Features

- **Multilingual Support**: Handles English, Hindi, and Kannada languages
- **Audio Processing**: Extracts Q&A pairs from call recordings
- **Speaker Identification**: Distinguishes between customers and business owners
- **Intent Classification**: Categorizes customer queries by intent
- **Response Generation**: Generates contextual responses based on learned patterns
- **Fallback System**: Provides appropriate responses even for unseen queries
- **Real-time Processing**: Can handle live customer queries

## System Architecture

```
Call Recordings → Audio Processing → Q&A Extraction → Model Training → Deployed Agent
     ↓                    ↓               ↓              ↓              ↓
  .wav/.mp3         Transcription    Intent+Response   ML Models    Live Service
   files            + Language        Pairs           Training      Responses
                    Detection
```

## Quick Start

### 1. Setup Environment

```bash
# Clone or download the project
cd CustomerServiceAssistant

# Run setup script
python3 setup.py

# Activate virtual environment
source ai_env/bin/activate  # Linux/Mac
# or
ai_env\Scripts\activate     # Windows
```

### 2. Add Your Call Recordings

Place your call recordings in the `call_recordings` directory:
- Supported formats: `.wav`, `.mp3`, `.m4a`, `.flac`, `.ogg`
- Recordings should contain conversations between business owners and customers
- Multiple languages (English, Hindi, Kannada) are supported

### 3. Run the Complete Pipeline

```bash
# Process audio, train models, and deploy agent
python complete_pipeline.py --mode all

# Or run individual steps:
python complete_pipeline.py --mode process  # Extract Q&A pairs
python complete_pipeline.py --mode train    # Train ML models  
python complete_pipeline.py --mode serve    # Deploy agent
```

## Detailed Usage

### Audio Processing

The system processes call recordings to:
- Transcribe audio using OpenAI Whisper
- Detect languages (English, Hindi, Kannada)
- Identify speakers (customer vs business owner)
- Extract question-answer pairs
- Categorize intents

```python
from voice_data_processor import MultilingualVoiceDataProcessor

processor = MultilingualVoiceDataProcessor()
conversations, qa_pairs = processor.process_all_recordings("call_recordings")
processor.save_training_data(qa_pairs)
```

### Model Training

Trains two main models:
- **Intent Classifier**: Categorizes customer queries
- **Response Generator**: Generates appropriate responses

```python
from models.conversation_model_trainer import MultilingualConversationModelTrainer

trainer = MultilingualConversationModelTrainer("training_data.json")
trainer.train_intent_classifier()
trainer.train_response_generator()
```

### Customer Service Agent

The deployed agent can handle real-time queries:

```python
from multilingual_customer_service_agent import MultilingualCustomerServiceAgent

agent = MultilingualCustomerServiceAgent()
result = agent.process_customer_query("What time do you open?")
print(result['response'])
```

## Language Support

### English
- Full support for intent classification and response generation
- Handles common business queries (hours, menu, reservations, etc.)

### Hindi
- Devanagari script support
- Common phrases: "kya", "kaise", "kab", "kitna", "kahan"
- Business responses in Hindi

### Kannada
- Kannada script support  
- Common phrases: "yaava", "hege", "yaavaga", "eshtu"
- Business responses in Kannada

## Intent Categories

The system recognizes these intent categories:
- **Hours**: Opening/closing times
- **Availability**: Table reservations, wait times
- **Menu**: Food items, dietary options
- **Location**: Address, directions
- **Contact**: Phone numbers, contact info
- **Pricing**: Costs, rates
- **Services**: Delivery, takeout, catering

## File Structure

```
CustomerServiceAssistant/
├── call_recordings/              # Place your audio files here
├── processed_audio/              # Processed audio chunks
├── models/                       # Trained model files
├── ai_env/                       # Virtual environment
├── voice_data_processor.py       # Audio processing
├── models/
│   └── conversation_model_trainer.py  # Model training
├── multilingual_customer_service_agent.py  # Deployed agent
├── complete_pipeline.py          # Main pipeline script
├── setup.py                      # Setup script
├── requirements.txt              # Dependencies
└── README.md                     # This file
```

## Configuration

### Model Selection

You can customize the models used:

```python
# For better multilingual support (larger models)
trainer = MultilingualConversationModelTrainer()
trainer.train_intent_classifier(model_name="microsoft/mdeberta-v3-base")
trainer.train_response_generator(model_name="microsoft/DialoGPT-medium")

# For faster processing (smaller models)  
trainer.train_intent_classifier(model_name="distilbert-base-multilingual-cased")
trainer.train_response_generator(model_name="microsoft/DialoGPT-small")
```

### Audio Processing

Adjust audio processing parameters:

```python
processor = MultilingualVoiceDataProcessor(whisper_model_size="base")
# Options: "tiny", "base", "small", "medium", "large"
```

## Troubleshooting

### Common Issues

1. **No audio files found**
   - Ensure audio files are in `call_recordings` directory
   - Check file formats are supported

2. **Language detection errors**
   - Install language detection dependencies: `pip install langdetect`
   - Ensure audio quality is good for transcription

3. **Model training fails**
   - Check available GPU memory
   - Reduce batch size in training arguments
   - Use smaller models for limited resources

4. **Poor response quality**
   - Add more training data
   - Improve audio quality of recordings
   - Fine-tune model parameters

### Performance Tips

- Use GPU for faster training: `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118`
- Increase Whisper model size for better transcription: `whisper_model_size="medium"`
- Add more diverse training data for better responses

## API Deployment (Optional)

Create a simple Flask API:

```python
from flask import Flask, request, jsonify
from multilingual_customer_service_agent import MultilingualCustomerServiceAgent

app = Flask(__name__)
agent = MultilingualCustomerServiceAgent()

@app.route('/query', methods=['POST'])
def handle_query():
    data = request.json
    result = agent.process_customer_query(data['query'])
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add your improvements
4. Test with different languages and scenarios
5. Submit a pull request

## License

This project is open source. Feel free to use and modify for your business needs.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs in `pipeline.log`
3. Test with sample audio files first
4. Ensure all dependencies are installed correctly
