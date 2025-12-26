import React, { useState, useEffect, useRef } from 'react';

// Type definitions for Web Speech API
interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: (event: any) => void;
  onerror: (event: any) => void;
  onend: (event: any) => void;
}

declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

interface VoiceInputProps {
  onTranscriptComplete: (transcript: string) => Promise<any>;
}

export const VoiceInput: React.FC<VoiceInputProps> = ({ onTranscriptComplete }) => {
  const [partialTranscript, setPartialTranscript] = useState<string>('');
  const [finalTranscript, setFinalTranscript] = useState<string>('');
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [backendResponse, setBackendResponse] = useState<string>('');

  const recognitionRef = useRef<SpeechRecognition | null>(null);

  useEffect(() => {
    // Initialize Speech Recognition
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US'; // Default to English, but models are multilingual

      recognition.onresult = (event: any) => {
        let interimTranscript = '';
        let finalTrans = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTrans += event.results[i][0].transcript;
          } else {
            interimTranscript += event.results[i][0].transcript;
          }
        }

        if (finalTrans) {
          setFinalTranscript(prev => {
            const newValue = prev ? `${prev} ${finalTrans}` : finalTrans;
            // When we get a final chunk, we can optionally send it immediately 
            // or wait for the user to stop. 
            // For this demo, let's just accumulate it.
            return newValue;
          });
        }
        setPartialTranscript(interimTranscript);
      };

      recognition.onerror = (event: any) => {
        console.error('Speech recognition error', event.error);
        setError(`Error: ${event.error}`);
        setIsRecording(false);
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current = recognition;
    } else {
      setError("Web Speech API is not supported in this browser.");
    }
  }, []);

  const handleTranscriptComplete = async (transcript: string) => {
    if (!transcript.trim()) return;

    try {
      setBackendResponse('Sending to backend...');
      const response = await onTranscriptComplete(transcript);
      setBackendResponse(JSON.stringify(response, null, 2));
    } catch (err: any) {
      console.error('Backend fetch error:', err);
      const errorMessage = `Failed to get response from backend: ${err.message}`;
      setError(errorMessage);
      setBackendResponse(errorMessage);
    }
  };

  const handleToggleRecording = () => {
    if (isRecording) {
      recognitionRef.current?.stop();
      setIsRecording(false);
      // When stopping, process the final transcript we have so far
      // We wait a tick to let any pending finals settle? 
      // Actually, let's just send what we have in finalTranscript + partialTranscript
      const fullText = (finalTranscript + ' ' + partialTranscript).trim();
      if (fullText) {
        handleTranscriptComplete(fullText);
      }
    } else {
      // Reset states for a new recording session
      setError(null);
      setFinalTranscript('');
      setPartialTranscript('');
      setBackendResponse('');

      try {
        recognitionRef.current?.start();
        setIsRecording(true);
      } catch (err) {
        console.error("Failed to start recording:", err);
      }
    }
  };

  const renderUI = () => {
    if (error && error.includes("not supported")) {
      return <p style={styles.errorText}>{error}</p>;
    }

    return (
      <>
        <button
          onClick={handleToggleRecording}
          style={isRecording ? styles.stopButton : styles.startButton}
        >
          {isRecording ? 'Stop Listening' : 'Start Listening'}
        </button>
        <div style={styles.transcriptContainer}>
          <p style={styles.transcriptText}>
            <span style={styles.finalTranscript}>{finalTranscript}</span>
            <span style={styles.partialTranscript} style={{ color: '#999' }} >{partialTranscript}</span>
          </p>
        </div>
        {backendResponse && (
          <div style={styles.responseContainer}>
            <strong>Backend Response:</strong>
            <pre style={styles.responsePre}>{backendResponse}</pre>
          </div>
        )}
      </>
    );
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.header}>Live Microphone to Text</h2>
      <p style={styles.subHeader}>Using Web Speech API</p>
      {error && !error.includes("not supported") && <p style={styles.errorText}>{error}</p>}
      {renderUI()}
    </div>
  );
};

// Basic styling to make the component look clean
const styles: { [key: string]: React.CSSProperties } = {
  container: {
    fontFamily: 'sans-serif',
    maxWidth: '600px',
    margin: '50px auto',
    padding: '20px',
    borderRadius: '8px',
    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
    textAlign: 'center',
  },
  header: {
    margin: 0,
  },
  subHeader: {
    color: '#666',
    marginTop: '4px',
  },
  startButton: {
    backgroundColor: '#28a745',
    color: 'white',
    padding: '10px 20px',
    border: 'none',
    borderRadius: '4px',
    fontSize: '16px',
    cursor: 'pointer',
    margin: '20px 0',
  },
  stopButton: {
    backgroundColor: '#dc3545',
    color: 'white',
    padding: '10px 20px',
    border: 'none',
    borderRadius: '4px',
    fontSize: '16px',
    cursor: 'pointer',
    margin: '20px 0',
  },
  transcriptContainer: {
    minHeight: '100px',
    border: '1px solid #ccc',
    borderRadius: '4px',
    padding: '10px',
    textAlign: 'left',
    background: '#f9f9f9',
  },
  transcriptText: {
    margin: 0,
  },
  finalTranscript: {
    color: '#333',
  },
  partialTranscript: {
    color: '#999',
  },
  errorText: {
    color: '#dc3545',
    margin: '10px 0',
  },
  responseContainer: {
    marginTop: '20px',
    textAlign: 'left',
    background: '#e9ecef',
    padding: '10px',
    borderRadius: '4px',
  },
  responsePre: {
    whiteSpace: 'pre-wrap',
    wordWrap: 'break-word',
    margin: 0,
  },
};
