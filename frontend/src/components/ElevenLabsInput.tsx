import React, { useState, useEffect, useRef } from 'react';
import { useScribe } from '@elevenlabs/react';
import { API_URL } from '../config';

interface VoiceInputProps {
    onTranscriptComplete: (transcript: string, messages?: Message[]) => Promise<any>;
    agentName?: string;
    businessId: string;
}

interface Message {
    role: 'user' | 'assistant';
    text: string;
}

export const ElevenLabsInput: React.FC<VoiceInputProps> = ({ onTranscriptComplete, agentName = "Assistant", businessId }) => {
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
                // Scribe commit
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
    };

    // We need to capture the transition from connected -> disconnected to finalize text
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
            await fetch(`${API_URL}/save-conversation`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionIdRef.current,
                    messages: messages,
                    language: conversationLanguageRef.current,
                    business_id: businessId,
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
            '/fillers/filler_3.mp3'
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
        // Ignore empty or very short inputs (noise)
        if (!text || text.trim().length < 3) {
            addDebug(`Ignored short input: "${text}"`);
            return;
        }

        setPartialTranscript('');
        // Add user message
        setMessages(prev => [...prev, { role: 'user', text }]);

        // Play filler immediately to mask latency
        playFiller();

        addDebug(`Submitting user query: ${text}...`);

        try {
            const response = await onTranscriptComplete(text, messages); // Pass history so backend knows context

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
            addDebug(`Fetching audio stream (${language})...`);

            const mediaSource = new MediaSource();
            const audioUrl = URL.createObjectURL(mediaSource);
            const audio = new Audio(audioUrl);

            // Clean up on end
            audio.onended = () => {
                addDebug('Audio ended. Restarting listener...');
                isPlayingRef.current = false;
                URL.revokeObjectURL(audioUrl); // release memory
                startListening();
            };

            // Handle errors
            audio.onerror = (e) => {
                addDebug(`Audio error: ${e}`);
                isPlayingRef.current = false;
                startListening();
            };

            // Setup streaming when source opens
            mediaSource.addEventListener('sourceopen', async () => {
                try {
                    const sourceBuffer = mediaSource.addSourceBuffer('audio/mpeg');

                    const response = await fetch(`${API_URL}/tts`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ text, language }),
                    });

                    if (!response.ok) throw new Error('TTS response failed');
                    if (!response.body) throw new Error('No response body');

                    const reader = response.body.getReader();
                    const queue: Uint8Array[] = [];
                    let isUpdating = false;

                    const processQueue = () => {
                        if (queue.length > 0 && !isUpdating) {
                            try {
                                const chunk = queue.shift();
                                if (chunk) {
                                    isUpdating = true;
                                    sourceBuffer.appendBuffer(chunk as unknown as BufferSource);
                                }
                            } catch (e) {
                                console.error('Buffer append error', e);
                            }
                        }
                    };

                    sourceBuffer.addEventListener('updateend', () => {
                        isUpdating = false;
                        processQueue();
                    });

                    // Stop filler as soon as we establish stream
                    stopFiller();

                    // Start typewriter immediately
                    typeWriterEffect(text);

                    // Read loop
                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) {
                            if (!isUpdating && queue.length === 0) {
                                mediaSource.endOfStream();
                            } else {
                                // Wait for queue to drain
                                const checkEnd = setInterval(() => {
                                    if (!isUpdating && queue.length === 0) {
                                        clearInterval(checkEnd);
                                        try { mediaSource.endOfStream(); } catch (e) { }
                                    }
                                }, 100);
                            }
                            break;
                        }

                        if (value) {
                            queue.push(value);
                            processQueue();

                            // Try to start playing as soon as we have data
                            if (audio.paused) {
                                audio.play().catch(e => console.log("Auto-play prevented", e));
                            }
                        }
                    }
                } catch (err: any) {
                    addDebug(`Stream error: ${err.message}`);
                    mediaSource.endOfStream();
                }
            });

        } catch (err: any) {
            stopFiller();
            isPlayingRef.current = false;
            addDebug(`Playback launch error: ${err.message}`);
            startListening();
        }
    };

    const startListening = async () => {
        setError(null);
        setPartialTranscript('');
        addDebug('Initializing connection...');

        try {
            addDebug('Fetching token...');
            const tokenRes = await fetch(`${API_URL}/get-scribe-token`);
            addDebug(`Token Response Status: ${tokenRes.status}`);
            const tokenData = await tokenRes.json();
            addDebug(`Token Response Data: ${JSON.stringify(tokenData)}`);

            if (!tokenRes.ok || tokenData.error) {
                throw new Error(tokenData.error || `Failed to get token: ${tokenRes.statusText}`);
            }

            if (!tokenData.token) {
                throw new Error("Backend returned 200 OK but no 'token' field found in JSON.");
            }

            await connect({
                token: tokenData.token,
                modelId: 'scribe_v2_realtime',
                // @ts-ignore - 'language' is supported by Scribe v2 but missing in current react-SDK types
                language: 'en',
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
    };

    // Watch for disconnection to trigger submission (if we have text)
    useEffect(() => {
        if (status === 'disconnected' && partialTextRef.current) {
            const textToSubmit = partialTextRef.current;
            partialTextRef.current = ''; // Clear ref to prevent double submit
            submitUserQuery(textToSubmit);
        }
    }, [status]); // When status changes to disconnected, submit.

    return (
        <div className="chat-wrapper">
            <div className="chat-header">
                <h2>{agentName}</h2>
                <div className="chat-status">
                    Status: <span style={{ color: status === 'connected' || status === 'transcribing' ? 'var(--success-color)' : 'var(--text-secondary)' }}>
                        {status === 'connected' || status === 'transcribing' ? 'Listening...' : status}
                    </span>
                    {isPlayingRef.current && <span style={{ color: 'var(--accent-color)', marginLeft: '10px' }}>Speaking...</span>}
                </div>
            </div>

            <div className="chat-body">
                {messages.map((msg, index) => (
                    <div key={index} className="message-row" style={{
                        justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start'
                    }}>
                        <div className={`message-bubble ${msg.role === 'user' ? 'msg-user' : 'msg-assistant'}`}>
                            {msg.text}
                        </div>
                    </div>
                ))}

                {/* Partial transcript */}
                {partialTranscript && (
                    <div className="message-row" style={{ justifyContent: 'flex-end' }}>
                        <div className="message-bubble msg-user" style={{ opacity: 0.7 }}>
                            {partialTranscript}...
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {error && <div style={{ background: '#f44336', color: 'white', padding: '10px', textAlign: 'center' }}>{error}</div>}

            <div className="chat-controls">


                <button
                    onClick={status === 'connected' || status === 'transcribing' ? handleManualStop : startListening}
                    disabled={status === 'connecting' || isPlayingRef.current}
                    className="btn-primary"
                    style={{
                        width: '100%',
                        backgroundColor: status === 'connected' || status === 'transcribing' ? 'var(--error-color)' : 'var(--success-color)',
                        opacity: isPlayingRef.current ? 0.5 : 1
                    }}
                >
                    {isPlayingRef.current ? 'Agent Speaking...' :
                        (status === 'connected' || status === 'transcribing' ? 'Stop Recording' : 'Start Voice Conversation')}
                </button>
            </div>

            <details className="debug-details">
                <summary style={{ cursor: 'pointer' }}>Show Debug Logs</summary>
                <div style={{ marginTop: '10px', maxHeight: '100px', overflowY: 'auto' }}>
                    {debugLog.map((log, i) => <div key={i}>{log}</div>)}
                </div>
            </details>
        </div>
    );
};
