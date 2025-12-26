// import { VoiceInput } from './components/VoiceInput';
import { ElevenLabsInput } from './components/ElevenLabsInput';
// import { useState } from 'react';

function App() {
  // const [useElevenLabs, setUseElevenLabs] = useState(false);

  // This function will be called when a final transcript is ready
  const handleTranscriptComplete = async (transcript: string) => {
    console.log('Final Transcript:', transcript);

    // Perform the fetch() POST request to the backend
    try {
      const response = await fetch('/ask-mom', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ transcript }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Gemini/Backend Response:', data);
      return data; // Return data to be displayed by the component
    } catch (error) {
      console.error('Error sending transcript to backend:', error);
      throw error; // Re-throw to be caught by the component
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Rainbow Driving School</h1>
        {/* <div style={{ margin: '20px 0' }}>
          <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
            <input
              type="checkbox"
              checked={useElevenLabs}
              onChange={(e) => setUseElevenLabs(e.target.checked)}
            />
            Test with ElevenLabs API
          </label>
        </div> */}
      </header>
      <main>
        {/* {useElevenLabs ? ( */}
        <ElevenLabsInput onTranscriptComplete={handleTranscriptComplete} />
        {/* ) : (
          <VoiceInput onTranscriptComplete={handleTranscriptComplete} />
        )} */}
      </main>
    </div>
  );
}

export default App;
