import React, { useEffect, useState } from 'react';

interface Business {
    id: string;
    name: string;
    location: string;
}

interface AdminPageProps {
    onBack: () => void;
}

const AdminPage: React.FC<AdminPageProps> = ({ onBack }) => {
    const [businesses, setBusinesses] = useState<Business[]>([]);
    const [loading, setLoading] = useState(true);
    const [deleteIntent, setDeleteIntent] = useState<Business | null>(null);

    const loadBusinesses = () => {
        setLoading(true);
        fetch('http://localhost:5001/businesses')
            .then(res => res.json())
            .then(data => {
                setBusinesses(data);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    };

    useEffect(() => {
        loadBusinesses();
    }, []);

    const handleDeleteClick = (business: Business) => {
        setDeleteIntent(business);
    };

    const confirmDelete = async () => {
        if (!deleteIntent) return;

        try {
            const res = await fetch(`http://localhost:5001/delete-business/${deleteIntent.id}`, {
                method: 'DELETE'
            });
            if (res.ok) {
                // alert(`Business "${deleteIntent.name}" deleted.`); // Removed alert for smoother UX, or keep it? Let's remove and just refresh. 
                // Actually, let's keep a small notification or just refresh. Refresh is fine.
                loadBusinesses();
            } else {
                alert('Failed to delete business.');
            }
        } catch (e) {
            console.error(e);
            alert('Error deleting business.');
        } finally {
            setDeleteIntent(null);
        }
    };

    return (
        <div className="container" style={{ marginTop: '40px', maxWidth: '800px', margin: '40px auto' }}>
            <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                    <h1 style={{ margin: 0 }}>🛡️ Admin Panel</h1>
                    <button onClick={onBack} className="btn-primary" style={{ background: 'transparent', border: '1px solid var(--border-color)' }}>
                        ← Back to Directory
                    </button>
                </div>

                <p style={{ color: 'var(--text-secondary)' }}>Manage registered businesses.</p>

                {loading ? (
                    <p>Loading...</p>
                ) : (
                    <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '20px' }}>
                        <thead>
                            <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                                <th style={{ padding: '10px' }}>Name</th>
                                <th style={{ padding: '10px' }}>Location</th>
                                <th style={{ padding: '10px' }}>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {businesses.map(b => (
                                <tr key={b.id} style={{ borderBottom: '1px solid #333' }}>
                                    <td style={{ padding: '15px' }}>{b.name}</td>
                                    <td style={{ padding: '15px', color: 'var(--text-secondary)' }}>{b.location}</td>
                                    <td style={{ padding: '15px' }}>
                                        <button
                                            onClick={() => handleDeleteClick(b)}
                                            style={{
                                                backgroundColor: 'var(--error-color)',
                                                color: 'white',
                                                border: 'none',
                                                padding: '8px 12px',
                                                borderRadius: '4px',
                                                cursor: 'pointer'
                                            }}
                                        >
                                            Delete
                                        </button>
                                    </td>
                                </tr>
                            ))}
                            {businesses.length === 0 && (
                                <tr>
                                    <td colSpan={3} style={{ textAlign: 'center', padding: '20px', color: 'var(--text-secondary)' }}>
                                        No businesses found.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Confirmation Modal */}
            {deleteIntent && (
                <div style={{
                    position: 'fixed',
                    top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    zIndex: 1000,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                }}>
                    <div className="card" style={{ maxWidth: '400px', width: '90%', textAlign: 'center' }}>
                        <h2 style={{ marginTop: 0 }}>Confirm Deletion</h2>
                        <p style={{ marginBottom: '30px' }}>
                            Are you sure you want to delete <strong>{deleteIntent.name}</strong>?
                            <br /><span style={{ fontSize: '0.9em', color: 'var(--error-color)' }}>This action cannot be undone.</span>
                        </p>
                        <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
                            <button
                                onClick={() => setDeleteIntent(null)}
                                className="btn-primary"
                                style={{ background: 'transparent', border: '1px solid var(--border-color)' }}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={confirmDelete}
                                className="btn-primary"
                                style={{ backgroundColor: 'var(--error-color)', border: 'none' }}
                            >
                                Delete
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AdminPage;
