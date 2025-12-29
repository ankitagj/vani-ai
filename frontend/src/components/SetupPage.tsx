import React, { useState } from 'react';

interface SetupPageProps {
    onComplete: () => void;
}

const SetupPage: React.FC<SetupPageProps> = ({ onComplete }) => {
    const [formData, setFormData] = useState({
        business_name: '',
        agent_name: '',
        owner_name: '',
        phone: '',
        location: '',
        deployment_phone: '',
        request_new_number: true,
        agent_behavior: '',
        voice_gender: 'no_preference',
        voice_id: '5Q0t7uMcjvnagumLfvZi', // Default to Sarah
        custom_voice_id_val: '',
    });
    const [files, setFiles] = useState<File[]>([]);
    const [loading, setLoading] = useState(false);
    const [status, setStatus] = useState('');

    // Constants for upload limits
    const MAX_FILES = 15;
    const MAX_FILE_SIZE_MB = 10;
    const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            const newFiles = Array.from(e.target.files);

            // 1. Check Total File Count
            if (files.length + newFiles.length > MAX_FILES) {
                alert(`You can only upload a maximum of ${MAX_FILES} files. You already have ${files.length}.`);
                e.target.value = ''; // Clear input
                return;
            }

            // 2. Check File Sizes
            for (const file of newFiles) {
                if (file.size > MAX_FILE_SIZE_BYTES) {
                    alert(`File "${file.name}" exceeds the ${MAX_FILE_SIZE_MB}MB limit.`);
                    e.target.value = ''; // Clear input
                    return;
                }
            }

            // 3. Append to existing files
            setFiles(prev => [...prev, ...newFiles]);

            // 4. Reset input to allow selecting the same file again if needed
            e.target.value = '';
        }
    };

    const removeFile = (index: number) => {
        setFiles(prev => prev.filter((_, i) => i !== index));
    };

    const [setupResult, setSetupResult] = useState<{ phone: string, name: string } | null>(null);

    // ... existing handlers ...

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setStatus('Registering Business...');

        try {
            // 1. Prepare Payload (Handle Custom Voice)
            const payload = { ...formData };
            if (payload.voice_id === 'custom' && payload.custom_voice_id_val) {
                payload.voice_id = payload.custom_voice_id_val;
            }

            // 2. Save Config & Get Business ID
            const setupResponse = await fetch('http://localhost:5002/setup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!setupResponse.ok) throw new Error('Setup failed');
            const setupData = await setupResponse.json();
            const businessId = setupData.business_id;

            // 2. Upload Transcripts (if any)
            if (files.length > 0) {
                setStatus('Uploading transcripts...');
                const uploadData = new FormData();
                files.forEach(file => {
                    uploadData.append('file', file);
                });

                await fetch(`http://localhost:5002/upload-transcripts/${businessId}`, {
                    method: 'POST',
                    body: uploadData,
                });
            }

            setStatus('Finalizing Agents...');
            await fetch('http://localhost:5002/setup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ...formData, id: businessId, request_new_number: false }),
            });

            setStatus('Setup complete!');

            // Show Success Screen instead of immediate redirect
            setSetupResult({
                phone: setupData.deployment_phone || formData.deployment_phone || 'N/A',
                name: formData.business_name
            });

        } catch (error) {
            console.error(error);
            setStatus('Error during setup. Please check console.');
        } finally {
            setLoading(false);
        }
    };

    if (setupResult) {
        return (
            <div className="container" style={{ marginTop: '40px', maxWidth: '600px', margin: '40px auto' }}>
                <div className="card" style={{ textAlign: 'center', padding: '40px' }}>
                    <div style={{ fontSize: '4rem', marginBottom: '20px' }}>🎉</div>
                    <h1 style={{ marginTop: 0, color: 'var(--success-color)' }}>Setup Complete!</h1>
                    <p style={{ fontSize: '1.2rem', color: 'var(--text-primary)' }}>
                        <strong>{setupResult.name}</strong> is now live.
                    </p>

                    <div style={{ margin: '30px 0', padding: '20px', background: 'rgba(255,255,255,0.05)', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
                        <p style={{ margin: 0, textTransform: 'uppercase', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                            Your AI Agent's Phone Number
                        </p>
                        <p style={{ margin: '10px 0 0 0', fontSize: '2rem', fontWeight: 'bold', color: '#fff', letterSpacing: '1px' }}>
                            {setupResult.phone}
                        </p>
                    </div>

                    <p style={{ color: 'var(--text-secondary)', marginBottom: '30px' }}>
                        You can share this number with your customers immediately.
                    </p>

                    <button
                        onClick={onComplete}
                        className="btn-primary"
                        style={{ width: '100%', padding: '15px', fontSize: '1.1rem' }}
                    >
                        Go to Directory →
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="container" style={{ marginTop: '40px', maxWidth: '600px', margin: '40px auto' }}>
            <div className="card">
                <h1 style={{ marginTop: 0, textAlign: 'center' }}>🤖 AI Agent Setup</h1>
                <p style={{ color: 'var(--text-secondary)', textAlign: 'center' }}>Configure your detailed business profile.</p>

                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '15px', marginTop: '20px' }}>
                    <div>
                        <label>Business Name</label>
                        <input
                            name="business_name"
                            placeholder="e.g. Joe's Pizza"
                            value={formData.business_name}
                            onChange={handleChange}
                            required
                            className="input-field"
                        />
                    </div>

                    <div>
                        <label>Agent Name</label>
                        <input
                            name="agent_name"
                            placeholder="e.g. Mario"
                            value={formData.agent_name}
                            onChange={handleChange}
                            required
                            className="input-field"
                        />
                    </div>

                    <div>
                        <label>Owner Name</label>
                        <input
                            name="owner_name"
                            placeholder="e.g. Joe Smith"
                            value={formData.owner_name}
                            onChange={handleChange}
                            required
                            className="input-field"
                        />
                    </div>

                    <div>
                        <label>Agent Voice</label>
                        <select
                            name="voice_id"
                            value={formData.voice_id || '5Q0t7uMcjvnagumLfvZi'}
                            onChange={(e) => setFormData({ ...formData, voice_id: e.target.value })}
                            className="input-field"
                            style={{ backgroundColor: 'rgba(255,255,255,0.05)', color: 'white' }}
                        >
                            <optgroup label="🇮🇳 Best for Hindi/Indian Context">
                                <option value="5Q0t7uMcjvnagumLfvZi">Sarah (Female) - Recommended</option>
                                <option value="pqHfZKP75CvOlQylNhV4">Bill (Male) - Deep/Trustworthy</option>
                            </optgroup>

                            <optgroup label="🇺🇸 American English">
                                <option value="21m00Tcm4TlvDq8ikWAM">Rachel (Female) - Calm/Pro</option>
                                <option value="29vD33N1CtxCmqQRPOHJ">Drew (Male) - News Anchor</option>
                                <option value="2EiwWnXFnvU5JabPnv8n">Clyde (Male) - Deep</option>
                            </optgroup>

                            <optgroup label="🌍 International Accents">
                                <option value="IKne3meq5aSn9XLyUdCD">Charlie (Male - Australian)</option>
                                <option value="zrHiDhphv9ZnVXBqCLjz">Mimi (Female - Australian)</option>
                                <option value="JBFqnCBsd6RMkjVDRZzb">George (Male - British)</option>
                                <option value="D38z5RcWu1voky8o86Ks">Fin (Male - Irish)</option>
                            </optgroup>
                        </select>
                    </div>

                    <div>
                        <label>Business Owner Phone (For Contact)</label>
                        <input
                            name="phone"
                            placeholder="e.g. +1 555-0123"
                            value={formData.phone}
                            onChange={handleChange}
                            required
                            className="input-field"
                        />
                    </div>

                    <div style={{ marginTop: '10px', padding: '15px', backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                        <h3 style={{ marginTop: 0, fontSize: '1rem', color: 'var(--text-primary)' }}>📞 Agent Deployment Number</h3>
                        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '15px' }}>
                            Where should customers call to reach your AI Agent?
                        </p>

                        <div style={{ marginBottom: '15px' }}>
                            <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                                <input
                                    type="checkbox"
                                    name="request_new_number"
                                    checked={formData.request_new_number}
                                    onChange={(e) => {
                                        setFormData(prev => ({
                                            ...prev,
                                            request_new_number: e.target.checked,
                                            deployment_phone: e.target.checked ? '' : prev.deployment_phone
                                        }));
                                    }}
                                    style={{ marginRight: '10px', width: 'auto' }}
                                />
                                Request a new dedicated number (Auto-provision)
                            </label>
                        </div>

                        {!formData.request_new_number && (
                            <div>
                                <label>Existing Deployment Phone (Twilio/Vapi)</label>
                                <input
                                    name="deployment_phone"
                                    placeholder="e.g. +1 999-888-7777"
                                    value={formData.deployment_phone || ''} // Handle undefined
                                    onChange={(e) => setFormData({ ...formData, deployment_phone: e.target.value })}
                                    className="input-field"
                                    style={{ marginTop: '5px' }}
                                />
                            </div>
                        )}


                    </div>

                    <div>
                        <label>Location</label>
                        <input
                            name="location"
                            placeholder="e.g. New York, NY"
                            value={formData.location}
                            onChange={handleChange}
                            required
                            className="input-field"
                        />
                    </div>

                    <div>
                        <label>Agent Behavior Instructions (Optional)</label>
                        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '5px' }}>
                            Tell the agent how to behave. E.g., "Be very polite," "Always ask for email," "Respond in short sentences."
                        </p>
                        <textarea
                            name="agent_behavior"
                            placeholder="e.g. Please treat every customer like a VIP. Always mention we are closed on Sundays."
                            value={formData.agent_behavior || ''}
                            onChange={(e) => setFormData({ ...formData, agent_behavior: e.target.value })}
                            className="input-field"
                            style={{ minHeight: '80px', fontFamily: 'inherit' }}
                        />
                    </div>

                    <div>
                        <label>Upload Documents (Audio, PDF, JSON)</label>
                        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '5px' }}>
                            Max {MAX_FILES} files, {MAX_FILE_SIZE_MB}MB each.
                        </p>
                        <input
                            type="file"
                            multiple
                            accept=".json, .pdf, .txt, .mp3, .wav, .m4a, .ogg"
                            onChange={handleFileChange}
                            className="input-field"
                            style={{ paddingTop: '8px' }}
                        />

                        {/* Selected Files List */}
                        {files.length > 0 && (
                            <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '5px' }}>
                                {files.map((file, index) => (
                                    <div key={index} style={{
                                        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                        background: 'rgba(255,255,255,0.1)', padding: '5px 10px', borderRadius: '4px', fontSize: '0.9rem'
                                    }}>
                                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>📄 {file.name}</span>
                                        <button
                                            type="button"
                                            onClick={() => removeFile(index)}
                                            style={{ background: 'transparent', border: 'none', color: '#ff6b6b', cursor: 'pointer', marginLeft: '10px' }}
                                        >
                                            ✕
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="btn-primary"
                        style={{ marginTop: '10px', width: '100%', opacity: loading ? 0.7 : 1 }}
                    >
                        {loading ? 'Processing...' : 'Create Agent'}
                    </button>
                </form>

                {status && <p style={{ marginTop: '20px', fontWeight: 'bold', color: 'var(--success-color)', textAlign: 'center' }}>{status}</p>}
            </div>
        </div>
    );
};

export default SetupPage;
