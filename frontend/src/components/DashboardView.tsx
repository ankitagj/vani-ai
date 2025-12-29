
import React, { useEffect, useState } from 'react';

interface DashboardStats {
    stats: {
        total_conversations: number;
        hot_leads: number;
        general_inquiries: number;
        spam: number;
        unrelated: number;
    };
    recent_conversations: Array<{
        started_at: string;
        customer_name?: string;
        customer_phone?: string;
        lead_classification?: string;
        summary?: string;
        language?: string;
    }>;
}

interface DashboardViewProps {
    businessId: string;
    businessName: string;
    onBack: () => void;
}

const DashboardView: React.FC<DashboardViewProps> = ({ businessId, businessName, onBack }) => {
    const [data, setData] = useState<DashboardStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetch(`http://localhost:5002/api/dashboard-stats?business_id=${businessId}`)
            .then(res => {
                if (!res.ok) throw new Error("Failed to fetch stats");
                return res.json();
            })
            .then(data => {
                setData(data);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setError("Error loading dashboard data");
                setLoading(false);
            });
    }, [businessId]);

    if (loading) return <div style={{ padding: 40, color: '#fff', textAlign: 'center' }}>Loading Dashboard...</div>;
    if (error) return <div style={{ padding: 40, color: '#ff6b6b', textAlign: 'center' }}>{error} - Make sure backend is running.</div>;
    if (!data) return null;

    return (
        <div style={{ maxWidth: 1200, margin: '0 auto', padding: 20 }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 30 }}>
                <button
                    onClick={onBack}
                    style={{
                        background: 'transparent',
                        border: '1px solid #444',
                        color: '#ccc',
                        padding: '8px 16px',
                        borderRadius: 4,
                        cursor: 'pointer',
                        marginRight: 20
                    }}
                >
                    ← Back
                </button>
                <div>
                    <h1 style={{ margin: 0, fontSize: '1.8rem', color: '#fff' }}>{businessName} Analytics</h1>
                    <p style={{ margin: '5px 0 0 0', color: '#888' }}>Powered by Vani.ai • Real-time Call Performance</p>
                </div>
            </div>

            {/* Stats Cards */}
            <div style={{ display: 'flex', gap: 20, marginBottom: 40, flexWrap: 'wrap' }}>
                <StatCard title="Total Calls" value={data.stats.total_conversations} color="#667eea" />
                <StatCard title="Hot Leads" value={data.stats.hot_leads} color="#c53030" bg="#3c1616" />
                <StatCard title="Inquiries" value={data.stats.general_inquiries} color="#2b6cb0" bg="#1a2639" />
                <StatCard title="Spam/Other" value={data.stats.spam + data.stats.unrelated} color="#975a16" bg="#2c1e0b" />
            </div>

            {/* Recent Calls Table */}
            <div style={{ background: '#1e1e1e', borderRadius: 8, overflow: 'hidden', border: '1px solid #333' }}>
                <div style={{ padding: '15px 20px', borderBottom: '1px solid #333', background: '#252525' }}>
                    <h3 style={{ margin: 0, color: '#fff' }}>Recent Conversations</h3>
                </div>
                <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', color: '#ddd', fontSize: '0.9rem' }}>
                        <thead>
                            <tr style={{ background: '#111', textAlign: 'left' }}>
                                <th style={{ padding: 15 }}>Date</th>
                                <th style={{ padding: 15 }}>Name/Phone</th>
                                <th style={{ padding: 15 }}>Classification</th>
                                <th style={{ padding: 15 }}>Language</th>
                                <th style={{ padding: 15 }}>Summary</th>
                            </tr>
                        </thead>
                        <tbody>
                            {data.recent_conversations.map((conv, idx) => (
                                <tr key={idx} style={{ borderBottom: '1px solid #333' }}>
                                    <td style={{ padding: 15, color: '#888' }}>
                                        {new Date(conv.started_at).toLocaleDateString()} <br />
                                        <small>{new Date(conv.started_at).toLocaleTimeString()}</small>
                                    </td>
                                    <td style={{ padding: 15 }}>
                                        <div style={{ fontWeight: 600, color: '#fff' }}>{conv.customer_name || 'Unknown'}</div>
                                        <div style={{ fontSize: '0.85em', color: '#aaa', marginTop: 4 }}>{conv.customer_phone || 'No Number'}</div>
                                    </td>
                                    <td style={{ padding: 15 }}>
                                        <Badge type={conv.lead_classification} />
                                    </td>
                                    <td style={{ padding: 15 }}>{conv.language || 'English'}</td>
                                    <td style={{ padding: 15, maxWidth: 300, lineHeight: 1.4, color: '#ccc' }}>
                                        {conv.summary || <span style={{ opacity: 0.5, fontStyle: 'italic' }}>No summary available</span>}
                                    </td>
                                </tr>
                            ))}
                            {data.recent_conversations.length === 0 && (
                                <tr>
                                    <td colSpan={5} style={{ padding: 40, textAlign: 'center', color: '#666' }}>
                                        No conversations recorded yet.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

const StatCard = ({ title, value, color, bg = '#1e1e1e' }: { title: string, value: number, color: string, bg?: string }) => (
    <div style={{
        flex: 1,
        minWidth: 200,
        background: bg,
        padding: 20,
        borderRadius: 8,
        border: `1px solid ${color}44`,
        boxShadow: '0 4px 6px rgba(0,0,0,0.2)'
    }}>
        <div style={{ fontSize: '2.5rem', fontWeight: 700, color: color, marginBottom: 5 }}>{value}</div>
        <div style={{ fontSize: '0.9rem', color: '#aaa', textTransform: 'uppercase', letterSpacing: 1 }}>{title}</div>
    </div>
);

const Badge = ({ type }: { type?: string }) => {
    let color = '#718096';
    let bg = '#2d3748';
    let label = type || 'Unknown';

    if (type === 'HOT_LEAD') { color = '#fc8181'; bg = '#4a1515'; label = '🔥 Hot Lead'; }
    if (type === 'GENERAL_INQUIRY') { color = '#63b3ed'; bg = '#1a365d'; label = 'ℹ️ Inquiry'; }
    if (type === 'SPAM') { color = '#f6e05e'; bg = '#5f370e'; label = '⚠️ Spam'; }

    return (
        <span style={{
            display: 'inline-block',
            padding: '4px 10px',
            borderRadius: 12,
            fontSize: '0.75rem',
            fontWeight: 600,
            color: color,
            backgroundColor: bg,
            textTransform: 'uppercase'
        }}>
            {label}
        </span>
    );
};

export default DashboardView;
