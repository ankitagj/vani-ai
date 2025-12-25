# Gemini API Setup for Transcription

## Step 1: Get Your Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy your API key

## Step 2: Set Up the API Key

**Option 1: Environment Variable (Recommended)**
```bash
export GEMINI_API_KEY='AIzaSyAQV1Aoh1xPA1oOGssMVmgg11txkcXdQs8'
```

**Option 2: Command Line**
```bash
python transcribe_audio.py call_recordings/RD1.mp3 gemini --api-key AIzaSyAQV1Aoh1xPA1oOGssMVmgg11txkcXdQs8
```

## Step 3: Run Transcription

```bash
# Try Gemini first (will fallback to Deepgram if quota exceeded)
python transcribe_audio.py call_recordings/RD1.mp3

# Or specify Gemini directly
python transcribe_audio.py call_recordings/RD1.mp3 gemini

# Or use Deepgram directly
python transcribe_audio.py call_recordings/RD1.mp3 deepgram --api-key YOUR_DEEPGRAM_KEY
```

## Why Gemini?

- **Excellent multilingual support** - Handles Kannada, Hindi, English, and mixed conversations
- **Context-aware** - Understands business context and speaker identification
- **High accuracy** - Google's advanced AI model
- **Free tier available** - Generous free usage limits

## Features

- Automatically transcribes in original language(s)
- Translates to English automatically
- Handles mixed-language conversations
- Identifies speakers when possible
- Preserves business terms and names
