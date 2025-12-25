# Deepgram API Key Setup Guide

## Step 1: Get Your Deepgram API Key

1. Go to [Deepgram Console](https://console.deepgram.com/)
2. Sign up or log in to your account
3. Navigate to **API Keys** section
4. Create a new API key or copy an existing one
5. **Important**: Save the key securely - you won't be able to see it again!

## Step 2: Set Up the API Key

You have **3 options** to provide the API key:

### Option 1: Environment Variable (Recommended for Permanent Use)

**For macOS/Linux (zsh/bash):**

```bash
# Temporary (current terminal session only)
export DEEPGRAM_API_KEY='your-api-key-here'

# Permanent (add to ~/.zshrc or ~/.bashrc)
echo 'export DEEPGRAM_API_KEY="your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

**For Windows (PowerShell):**

```powershell
# Temporary (current session only)
$env:DEEPGRAM_API_KEY = "your-api-key-here"

# Permanent (add to profile)
[System.Environment]::SetEnvironmentVariable('DEEPGRAM_API_KEY', 'your-api-key-here', 'User')
```

### Option 2: Command Line Argument (Quick & Easy)

```bash
python transcribe_audio.py call_recordings/RD1.mp3 deepgram --api-key your-api-key-here
```

### Option 3: Create a .env File (For Development)

1. Create a file named `.env` in the project root:
```bash
echo "DEEPGRAM_API_KEY=your-api-key-here" > .env
```

2. The script will automatically read it (if you install python-dotenv)

## Step 3: Run Transcription

Once the API key is set, run:

```bash
# Using environment variable
python transcribe_audio.py call_recordings/RD1.mp3 deepgram

# Or with command line argument
python transcribe_audio.py call_recordings/RD1.mp3 deepgram --api-key your-key
```

## Verify Setup

To check if your API key is set correctly:

```bash
# macOS/Linux
echo $DEEPGRAM_API_KEY

# Windows PowerShell
echo $env:DEEPGRAM_API_KEY
```

## Troubleshooting

- **"DEEPGRAM_API_KEY not found"**: Make sure you've exported the variable in the same terminal session, or use `--api-key` flag
- **"Authentication failed"**: Check that your API key is correct and hasn't expired
- **"Rate limit exceeded"**: You may have hit your plan's limits. Check your Deepgram dashboard

## Free Tier Limits

Deepgram offers a free tier with:
- $200 in free credits
- Good for testing and small projects
- Check [Deepgram Pricing](https://deepgram.com/pricing) for details

