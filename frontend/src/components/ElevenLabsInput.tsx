import React, { useState, useEffect, useRef } from 'react';
import { useScribe } from '@elevenlabs/react';

interface VoiceInputProps {
    onTranscriptComplete: (transcript: string, messages?: Message[]) => Promise<any>;
}

interface Message {
    role: 'user' | 'assistant';
    text: string;
}

export const ElevenLabsInput: React.FC<VoiceInputProps> = ({ onTranscriptComplete }) => {
    const [partialTranscript, setPartialTranscript] = useState<string>('');
    const [messages, setMessages] = useState<Message[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [debugLog, setDebugLog] = useState<string[]>([]);

    // Refs for conversational flow
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const silenceTimerRef = useRef<any>(null);
    const isPlayingRef = useRef<boolean>(false);
    const lastPartialTextRef = useRef<string>('');
    const sessionIdRef = useRef<string>('');
    const conversationLanguageRef = useRef<string>('English');
    const SILENCE_TIMEOUT_MS = 1500; // 1.5 seconds of no new text = turn ended

    // Generate session ID on mount
    useEffect(() => {
        sessionIdRef.current = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        addDebug(`Session ID: ${sessionIdRef.current}`);
    }, []);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, partialTranscript]);

    const addDebug = (msg: string) => {
        setDebugLog(prev => [...prev, `${new Date().toISOString().split('T')[1].slice(0, -1)}: ${msg}`]);
        console.log(msg);
    };

    const resetSilenceTimer = () => {
        if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
        silenceTimerRef.current = setTimeout(() => {
            addDebug('Silence detected. Processing...');
            stopListening();
        }, SILENCE_TIMEOUT_MS);
    };

    const { connect, disconnect, status } = useScribe({
        onPartialTranscript: (data) => {
            if (isPlayingRef.current) return; // Ignore input while AI is speaking

            const currentText = data.text || '';

            // Only reset timer if the text has actually changed
            if (currentText && currentText !== lastPartialTextRef.current) {
                setPartialTranscript(currentText);
                lastPartialTextRef.current = currentText;
                resetSilenceTimer();
            }
        },
        onCommittedTranscript: (data) => {
            // We rely more on silence detection for "turn taking", but this helps update the view
            const final = data.text;
            if (final && final.trim()) {
                // If Scribe commits, we can either wait for silence or treat it as a chunk.
                // For this use case, let's just let silence timer handle the "User finished" event.
                // But we update partial to show progress.
                // setPartialTranscript(final); 
                // Actually Scribe clears partial on commit, so we rely on silence logic mostly.
            }
        },
        onError: (e: any) => {
            addDebug(`Scribe Error: ${e.message}`);
            setError(`An error occurred: ${e.message || 'Unknown error'}`);
        },
    });

    const stopListening = () => {
        disconnect();
        if (silenceTimerRef.current) {
            clearTimeout(silenceTimerRef.current);
            silenceTimerRef.current = null;
        }

        // Manual commit logic will handle the actual submission in handleToggleRecording/disconnect flow
        // But since we call disconnect(), we need to trigger the submission logic manually or via a side effect.
        // The previous implementation used handleToggleRecording logic for this.
        // Let's call the submission logic explicitly here to be safe.

        // We need the current partial transcript. Since state updates are async, 
        // we might need a ref for partialTranscript if we want to access it inside this closure perfectly,
        // but state usually works fine if we trigger an encoded action.
        // However, we can use the "Manual commit" logic in the Effect or just trigger it here.

        // Actually, the easiest way is to trigger a specific "commit" function.
    };

    // We need to capture the transition from connected -> disconnected to finalize text
    // But since we want "silence -> stop -> submit", we can do it in the stopListening function
    // accessing the state directly might be stale.
    // Let's use a Ref for partial text to ensure freshness.
    const partialTextRef = useRef('');
    useEffect(() => {
        partialTextRef.current = partialTranscript;
    }, [partialTranscript]);

    // Save conversation periodically (every 3 messages)
    useEffect(() => {
        if (messages.length > 0 && messages.length % 3 === 0) {
            saveConversation(false);
        }
    }, [messages]);

    const saveConversation = async (ended: boolean = false) => {
        try {
            await fetch('/save-conversation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionIdRef.current,
                    messages: messages,
                    language: conversationLanguageRef.current,
                    ended: ended
                }),
            });
            if (ended) {
                addDebug('Conversation saved (ended)');
            }
        } catch (err: any) {
            console.error('Error saving conversation:', err);
        }
    };

    // Filler audio management
    const fillerAudioRef = useRef<HTMLAudioElement | null>(null);
    const FILLERS: { [key: string]: string[] } = {
        'English': [
            '/fillers/filler_1.mp3',
            '/fillers/filler_2.mp3',
            '/fillers/filler_3.mp3',
            '/fillers/filler_4.mp3'
        ],
        'Hindi': [
            '/fillers/filler_hi_1.mp3',
            '/fillers/filler_hi_2.mp3',
            '/fillers/filler_hi_3.mp3'
        ]
    };

    const playFiller = async () => {
        try {
            // Determine language (default to English if unknown)
            const lang = conversationLanguageRef.current || 'English';
            const fillersList = FILLERS[lang] || FILLERS['English'];

            // Pick random filler
            const randomFiller = fillersList[Math.floor(Math.random() * fillersList.length)];
            addDebug(`Playing filler (${lang}): ${randomFiller}`);

            const audio = new Audio(randomFiller);
            audio.volume = 0.6; // Slightly lower volume
            fillerAudioRef.current = audio;

            await audio.play();
        } catch (e: any) {
            console.warn("Filler play failed", e);
        }
    };

    const stopFiller = () => {
        if (fillerAudioRef.current) {
            fillerAudioRef.current.pause();
            fillerAudioRef.current = null;
        }
    };

    const submitUserQuery = async (text: string) => {
        if (!text || !text.trim()) return;

        setPartialTranscript('');
        // Add user message
        setMessages(prev => [...prev, { role: 'user', text }]);

        // Play filler immediately to mask latency
        playFiller();

        addDebug(`Submitting user query: ${text}...`);

        try {
            const response = await onTranscriptComplete(text, messages); // Pass history so backend knows context

            // Stop filler once we have the response (or ideally when TTS starts, but this is close enough)
            // actually playAudioResponse will be called next. 
            // We should ideally let playAudioResponse stop it to avoid dead air if TTS fetch takes time.
            // But response generation is the long part. TTS generation is fast.
            // So we can stop here or inside playAudioResponse.

            const textToSpeak = response.answer || response.response;
            const detectedLanguage = response.query_language || 'English';

            // Track conversation language
            conversationLanguageRef.current = detectedLanguage;

            if (textToSpeak) {
                // Add placeholder for assistant message
                setMessages(prev => [...prev, { role: 'assistant', text: '' }]);

                // Pass language to TTS
                await playAudioResponse(textToSpeak, detectedLanguage);
            } else {
                stopFiller(); // Stop if no response
                addDebug('No answer text found');
            }
        } catch (e: any) {
            stopFiller(); // Stop on error
            addDebug(`Error submitting: ${e.message}`);

            // Add error message as assistant response for user visibility
            setMessages(prev => [...prev, {
                role: 'assistant',
                text: 'I apologize, I\'m experiencing technical difficulties. Please try again in a moment or call us directly for assistance.'
            }]);

            setError(e.message);
        }
    };

    const typeWriterEffect = (text: string) => {
        let index = 0;
        const interval = setInterval(() => {
            setMessages(prev => {
                const newMessages = [...prev];
                const lastMsg = newMessages[newMessages.length - 1];
                if (lastMsg && lastMsg.role === 'assistant') {
                    // Update the text directly
                    lastMsg.text = text.slice(0, index + 1);
                }
                return newMessages;
            });
            index++;
            if (index >= text.length) clearInterval(interval);
        }, 50);
        return interval;
    };

    const playAudioResponse = async (text: string, language: string = 'English') => {
        try {
            isPlayingRef.current = true;
            addDebug(`Fetching audio (${language})...`);

            // Note: We leave filler playing while fetching TTS to cover that gap too

            const response = await fetch('/tts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, language }),
            });

            if (!response.ok) throw new Error('TTS failed');

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const audio = new Audio(url);

            // STOP FILLER NOW - ready to play real audio
            stopFiller();

            // Sync: Start typewriter when audio starts
            let typeWriterInterval: any;

            audio.onplay = () => {
                addDebug('Audio started. Typing text...');
                // IMPORTANT: Start the typewriter AFTER audio begins
                typeWriterInterval = typeWriterEffect(text);
            };

            audio.onended = () => {
                addDebug('Audio ended. Restarting listener...');
                isPlayingRef.current = false;
                if (typeWriterInterval) clearInterval(typeWriterInterval);

                // Auto-restart listening
                startListening();
            };

            await audio.play();
        } catch (err: any) {
            stopFiller(); // Stop if TTS fails
            isPlayingRef.current = false;
            addDebug(`Playback error: ${err.message}`);
            // Start listening anyway if audio fails, to keep flow
            startListening();
        }
    };

    const startListening = async () => {
        setError(null);
        setPartialTranscript('');
        addDebug('Initializing connection...');

        try {
            const tokenRes = await fetch('/get-scribe-token');
            const tokenData = await tokenRes.json();

            await connect({
                token: tokenData.token,
                modelId: 'scribe_v2_realtime',
                microphone: {
                    echoCancellation: true,
                    noiseSuppression: true,
                }
            });
            addDebug('Listening... Speak now!');
        } catch (err: any) {
            addDebug(`Connect failed: ${err.message}`);
            setError(err.message);
        }
    };

    const handleManualStop = () => {
        stopListening();
        // Allow the "disconnect" effect to handle submission? 
        // Or just call it directly.
        // We'll use a unified trigger.
    };

    // Watch for disconnection to trigger submission (if we have text)
    // This covers both manual stop and silence timeout stop.
    // We need to avoid double-submission if verify.
    // Let's use a "status" effect.
    useEffect(() => {
        if (status === 'disconnected' && partialTextRef.current) {
            const textToSubmit = partialTextRef.current;
            partialTextRef.current = ''; // Clear ref to prevent double submit
            submitUserQuery(textToSubmit);
        }
    }, [status]); // When status changes to disconnected, submit.

    return (
        <div style={styles.container}>
            <div style={styles.headerContainer}>
                <h2 style={styles.header}>SavitaDevi</h2>
                <div style={styles.statusIndicator}>
                    Status: <span style={{ color: status === 'connected' || status === 'transcribing' ? '#2ecc71' : '#95a5a6' }}>
                        {status === 'connected' || status === 'transcribing' ? 'Listening...' : status}
                    </span>
                    {isPlayingRef.current && <span style={{ color: '#007bff', marginLeft: '10px' }}>Speaking...</span>}
                </div>
            </div>

            <div style={styles.chatContainer}>
                {messages.map((msg, index) => (
                    <div key={index} style={{
                        ...styles.messageRow,
                        justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start'
                    }}>
                        <div style={{
                            ...styles.messageBubble,
                            backgroundColor: msg.role === 'user' ? '#007bff' : '#e9ecef',
                            color: msg.role === 'user' ? 'white' : 'black',
                            borderBottomRightRadius: msg.role === 'user' ? '0' : '12px',
                            borderBottomLeftRadius: msg.role === 'assistant' ? '0' : '12px',
                        }}>
                            {msg.text}
                        </div>
                    </div>
                ))}

                {/* Partial transcript */}
                {partialTranscript && (
                    <div style={{ ...styles.messageRow, justifyContent: 'flex-end' }}>
                        <div style={{ ...styles.messageBubble, backgroundColor: '#007bff', opacity: 0.7, color: 'white' }}>
                            {partialTranscript}...
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {error && <div style={styles.errorBanner}>{error}</div>}

            <div style={styles.controlsContainer}>
                <button
                    onClick={status === 'connected' || status === 'transcribing' ? handleManualStop : startListening}
                    disabled={status === 'connecting' || isPlayingRef.current}
                    style={{
                        ...styles.mainButton,
                        backgroundColor: status === 'connected' || status === 'transcribing' ? '#dc3545' : '#28a745',
                        opacity: isPlayingRef.current ? 0.5 : 1
                    }}
                >
                    {isPlayingRef.current ? 'Agent Speaking...' :
                        (status === 'connected' || status === 'transcribing' ? 'Stop Recording' : 'Start Conversation')}
                </button>
            </div>

            <details style={styles.debugDetails}>
                <summary style={{ cursor: 'pointer', color: '#666' }}>Show Debug Logs</summary>
                <div style={styles.debugLog}>
                    {debugLog.map((log, i) => <div key={i}>{log}</div>)}
                </div>
            </details>
        </div>
    );
};

const styles: { [key: string]: React.CSSProperties } = {
    container: {
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
        maxWidth: '500px',
        margin: '20px auto',
        backgroundColor: '#fff',
        borderRadius: '20px',
        boxShadow: '0 10px 25px rgba(0,0,0,0.1)',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        height: '80vh',
    },
    headerContainer: {
        padding: '20px',
        borderBottom: '1px solid #eee',
        backgroundColor: '#f8f9fa',
        textAlign: 'center',
    },
    header: { margin: 0, fontSize: '1.2rem', color: '#333' },
    statusIndicator: { fontSize: '0.8rem', marginTop: '5px', color: '#888' },
    chatContainer: {
        flex: 1,
        padding: '20px',
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        backgroundColor: '#ffffff',
    },
    messageRow: {
        display: 'flex',
        width: '100%',
    },
    messageBubble: {
        maxWidth: '80%',
        padding: '12px 16px',
        borderRadius: '12px',
        fontSize: '0.95rem',
        lineHeight: '1.4',
        boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
    },
    controlsContainer: {
        padding: '20px',
        borderTop: '1px solid #eee',
        backgroundColor: '#f8f9fa',
        textAlign: 'center',
    },
    mainButton: {
        width: '100%',
        padding: '15px',
        fontSize: '1.1rem',
        fontWeight: '600',
        color: 'white',
        border: 'none',
        borderRadius: '12px',
        cursor: 'pointer',
        transition: 'background-color 0.2s',
    },
    errorBanner: {
        backgroundColor: '#ffebee',
        color: '#c62828',
        padding: '10px',
        fontSize: '0.9rem',
        textAlign: 'center',
    },
    debugDetails: {
        padding: '10px 20px',
        backgroundColor: '#f1f1f1',
        fontSize: '0.8rem',
    },
    debugLog: {
        marginTop: '10px',
        maxHeight: '100px',
        overflowY: 'auto',
        fontFamily: 'monospace',
        whiteSpace: 'pre-wrap',
        color: '#333',
    }
};
