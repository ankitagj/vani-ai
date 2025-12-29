import React, { useEffect, useState } from 'react';

interface Business {
    id: string;
    name: string;
    location: string;
}

interface BusinessDirectoryProps {
    onSelect: (id: string) => void;
    onRegister: () => void;
    onAdmin: () => void;
}

const BusinessDirectory: React.FC<BusinessDirectoryProps> = ({ onSelect, onRegister, onAdmin }) => {
    const [businesses, setBusinesses] = useState<Business[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('http://localhost:5002/businesses')
            .then(res => res.json())
            .then(data => {
                setBusinesses(data);
                setLoading(false);
            })
            .catch(err => {
                console.error("Failed to load directory", err);
                setLoading(false);
            });
    }, []);

    if (loading) return <div className="container" style={{ marginTop: '2rem' }}>Loading Directory...</div>;

    return (
        <div className="container text-center" style={{ marginTop: '2rem' }}>
            <h1>🏢 Vani.ai Directory</h1>
            <p style={{ color: 'var(--text-secondary)' }}>Select a business to chat with its AI Agent.</p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px', marginTop: '30px', justifyContent: 'center', maxWidth: '1000px', margin: '30px auto' }}>
                {businesses.map(b => (
                    <div
                        key={b.id}
                        className="card"
                        onClick={() => onSelect(b.id)}
                        style={{ cursor: 'pointer' }}
                    >
                        <h3 style={{ margin: '0 0 10px 0' }}>{b.name}</h3>
                        <p style={{ margin: 0, color: 'var(--text-secondary)' }}>📍 {b.location}</p>
                    </div>
                ))}

                <div
                    onClick={onRegister}
                    className="card"
                    style={{
                        border: '2px dashed var(--border-color)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--text-secondary)',
                        background: 'transparent',
                        minHeight: '120px'
                    }}
                >
                    + Register New Business
                </div>
            </div>

            <div style={{ marginTop: '40px', borderTop: '1px solid var(--border-color)', paddingTop: '20px' }}>
                <button onClick={onAdmin} style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', textDecoration: 'underline', fontSize: '0.8rem' }}>
                    Admin Panel
                </button>
            </div>
        </div>
    );
};

export default BusinessDirectory;
