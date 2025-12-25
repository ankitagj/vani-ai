# Transcript Query Agent

A Gemini-powered query system that uses transcribed call recordings as a knowledge base to answer questions in English, Hindi, or Kannada.

## Overview

The `query_transcripts.py` script allows you to query all your transcribed call recordings using Google Gemini as the AI brain. It automatically:
- Loads all transcript files from the `transcripts/` directory
- Understands queries in English, Hindi, or Kannada
- Answers based on information from the call recordings
- Responds in the same language as the query (or English if preferred)

## Setup

1. **Set your Gemini API key:**
```bash
export GEMINI_API_KEY='your-api-key-here'
```

2. **Make sure you have transcripts:**
   - Run `transcribe_audio.py` on your call recordings first
   - Transcripts should be in `transcripts/` directory with `*_gemini_*.json` format

## Usage

### Interactive Mode (Recommended)

Start an interactive session where you can ask multiple questions:

```bash
python query_transcripts.py
```

**Example session:**
```
💬 Your question: What is the address of Rainbow Paradise?
💡 Answer (English): The Rainbow Paradise Building is opposite the Royal Store...

💬 Your question: ರೈನ್ಬೋ ಪ್ಯಾರಡೈಸ್ ಎಲ್ಲಿ ಇದೆ?
💡 Answer (Kannada): RD1 ಮತ್ತು RD2 ಪ್ರಕಾರ, ರೈನ್ಬೋ ಪ್ಯಾರಡೈಸ್...

💬 Your question: quit
👋 Goodbye!
```

**Interactive Commands:**
- `list` - Show all loaded transcripts
- `summary` - Get summary statistics
- `quit` or `exit` - Exit the agent

### Single Query Mode

Ask a single question from command line:

```bash
# English query
python query_transcripts.py "What are the office hours?"

# Kannada query
python query_transcripts.py "ರೈನ್ಬೋ ಪ್ಯಾರಡೈಸ್ ಎಲ್ಲಿ ಇದೆ?"

# Hindi query
python query_transcripts.py "रैनबो पैराडाइस कहाँ है?"
```

## Features

### Multilingual Support
- **English**: Full support for English queries
- **Kannada**: Kannada script (ಕನ್ನಡ) queries and responses
- **Hindi**: Devanagari script (हिंदी) queries and responses
- Automatic language detection
- Responses in the same language as the query

### Knowledge Base
- Automatically loads all Gemini transcripts
- Combines information from multiple recordings
- Cites which recording provided the information
- Handles missing information gracefully

### Smart Querying
- Understands context from conversations
- Extracts business information (hours, location, pricing, services)
- Identifies speakers when relevant
- Provides specific answers with citations

## Example Queries

### Business Information
```bash
# Location
"What is the address of Rainbow Paradise?"
"Where is the office located?"

# Hours
"What are the office hours?"
"When are you open?"

# Services
"What services do you offer?"
"What is the fee for scooter classes?"

# Contact
"How can I contact you?"
```

### Multilingual Examples
```bash
# Kannada
"ರೈನ್ಬೋ ಪ್ಯಾರಡೈಸ್ ಎಲ್ಲಿ ಇದೆ?"
"ಆಫೀಸ್ ಸಮಯ ಏನು?"

# Hindi
"रैनबो पैराडाइस कहाँ है?"
"कार्यालय का समय क्या है?"
```

## How It Works

1. **Load Transcripts**: Reads all `*_gemini_*.json` files from `transcripts/` directory
2. **Create Context**: Formats all transcripts as context for Gemini
3. **Process Query**: 
   - Detects query language (English/Hindi/Kannada)
   - Sends query + transcript context to Gemini
   - Gets AI-generated answer based on transcripts
4. **Return Answer**: Provides answer in the same language as query

## Technical Details

- **Model**: Uses Gemini 2.0 Flash (or falls back to other available models)
- **Context Window**: All transcripts are included in the context
- **Language Detection**: Automatic based on script detection
- **Error Handling**: Graceful handling of API errors, missing transcripts, etc.

## Troubleshooting

### "No transcripts available"
- Make sure you've run `transcribe_audio.py` first
- Check that transcripts are in `transcripts/` directory
- Verify files are named `*_gemini_*.json`

### "API quota exceeded"
- Wait for quota reset (usually 1 minute)
- Check your Gemini API usage limits
- Consider upgrading your API plan

### "GEMINI_API_KEY not found"
- Set the environment variable: `export GEMINI_API_KEY='your-key'`
- Or pass it programmatically in the script

## Integration

You can also use this as a Python module:

```python
from query_transcripts import TranscriptQueryAgent

# Initialize agent
agent = TranscriptQueryAgent(transcripts_dir="transcripts")

# Ask a question
result = agent.answer_query("What is the address?")
print(result['answer'])

# Interactive mode
agent.interactive_mode()
```

## Next Steps

- Add more transcripts by running `transcribe_audio.py` on new recordings
- The agent automatically includes new transcripts in its knowledge base
- Query in any language - the agent adapts automatically

