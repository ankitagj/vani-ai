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
    });
    const [files, setFiles] = useState<FileList | null>(null);
    const [loading, setLoading] = useState(false);
    const [status, setStatus] = useState('');

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) setFiles(e.target.files);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setStatus('Registering Business...');

        try {
            // 1. Save Config & Get Business ID
            const setupResponse = await fetch('http://localhost:5001/setup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData),
            });

            if (!setupResponse.ok) throw new Error('Setup failed');
            const setupData = await setupResponse.json();
            const businessId = setupData.business_id;

            // 2. Upload Transcripts (if any)
            if (files && files.length > 0) {
                setStatus('Uploading transcripts...');
                const uploadData = new FormData();
                Array.from(files).forEach(file => {
                    uploadData.append('file', file);
                });

                await fetch(`http://localhost:5001/upload-transcripts/${businessId}`, {
                    method: 'POST',
                    body: uploadData,
                });
            }

            setStatus('Finalizing Agents...');
            await fetch('http://localhost:5001/setup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ...formData, id: businessId }),
            });

            setStatus('Setup complete!');
            setTimeout(onComplete, 1000);

        } catch (error) {
            console.error(error);
            setStatus('Error during setup. Please check console.');
        } finally {
            setLoading(false);
        }
    };

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
                        <label>Phone Number</label>
                        <input
                            name="phone"
                            placeholder="e.g. +1 555-0123"
                            value={formData.phone}
                            onChange={handleChange}
                            required
                            className="input-field"
                        />
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
                        <label>Upload Documents (Audio, PDF, JSON)</label>
                        <input
                            type="file"
                            multiple
                            accept=".json, .pdf, .txt, .mp3, .wav, .m4a, .ogg"
                            onChange={handleFileChange}
                            className="input-field"
                            style={{ paddingTop: '8px' }}
                        />
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
