'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { X, ChevronDown, Trash2, Copy, Terminal, Scroll, Activity } from 'lucide-react';
import { getConfig, saveConfig } from '@/lib/api';

export default function DebugPanel() {
    const [isOpen, setIsOpen] = useState(false);
    const [logs, setLogs] = useState<string[]>([]);
    const [logLevel, setLogLevel] = useState('normal');
    const [limit, setLimit] = useState(500);
    const [autoScroll, setAutoScroll] = useState(true);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');
    const logContainerRef = useRef<HTMLDivElement>(null);
    const { t } = useLanguage();

    useEffect(() => {
        const handleOpen = () => setIsOpen(true);
        window.addEventListener('open-debug-panel', handleOpen);
        return () => window.removeEventListener('open-debug-panel', handleOpen);
    }, []);

    useEffect(() => {
        const fetchCurrentConfig = async () => {
            try {
                const config = await getConfig();
                setLogLevel(config.log_level || 'normal');
            } catch (e) {
                console.error("Failed to fetch config for debug panel", e);
            }
        };
        if (isOpen) fetchCurrentConfig();
    }, [isOpen]);

    const fetchLogs = async () => {
        if (!isOpen) return;
        try {
            const res = await fetch(`/api/debug/logs?lines=${limit}`);
            const data = await res.json();
            if (data.success && data.data && data.data.logs) {
                setLogs(data.data.logs);
            }
        } catch (e) {
            console.error("Failed to fetch logs", e);
        }
    };

    useEffect(() => {
        if (isOpen) {
            fetchLogs();
            const interval = setInterval(fetchLogs, 3000);
            return () => clearInterval(interval);
        }
    }, [isOpen, limit]);

    useEffect(() => {
        if (autoScroll && logContainerRef.current) {
            logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
        }
    }, [logs, autoScroll]);

    const handleLevelChange = async (level: string) => {
        try {
            setLoading(true);
            const config = await getConfig();
            config.log_level = level;
            await saveConfig(config);
            setLogLevel(level);
        } catch (e) {
            setMessage(`${t('Error')}: ${e}`);
        } finally {
            setLoading(false);
        }
    };

    const clearLogs = async () => {
        try {
            await fetch('/api/debug/logs', { method: 'DELETE' });
            setLogs([]);
            setMessage(t('Logs cleared successfully.'));
            setTimeout(() => setMessage(''), 3000);
        } catch (e) {
            setMessage(`${t('Error')}: ${e}`);
        }
    };

    const copyToClipboard = async () => {
        const text = logs.join('\n');
        try {
            await navigator.clipboard.writeText(text);
            setMessage(t('Copied to clipboard!'));
        } catch (err) {
            // Fallback for older browsers or non-HTTPS
            const textArea = document.createElement("textarea");
            textArea.value = text;
            textArea.style.position = "absolute";
            textArea.style.left = "-999999px";
            document.body.prepend(textArea);
            textArea.select();
            try {
                document.execCommand('copy');
                setMessage(t('Copied to clipboard!'));
            } catch (error) {
                console.error(error);
                setMessage(t('Failed to copy'));
            } finally {
                textArea.remove();
            }
        }
        setTimeout(() => setMessage(''), 3000);
    };

    if (!isOpen) return null;

    return (
        <div className="debug-overlay">
            <div className="debug-panel">
                <div className="debug-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <Terminal size={18} />
                        <h2 style={{ fontSize: 16, fontWeight: 600 }}>{t('Debug Panel')}</h2>
                    </div>
                    <button onClick={() => setIsOpen(false)} className="btn-icon">
                        <X size={20} />
                    </button>
                </div>

                <div className="debug-controls">
                    <div className="debug-control-group">
                        <label>{t('Log Level')}:</label>
                        <select
                            value={logLevel}
                            onChange={(e) => handleLevelChange(e.target.value)}
                            disabled={loading}
                            className="form-select"
                            style={{ width: 'auto', fontSize: 13 }}
                        >
                            <option value="off">{t('Off')}</option>
                            <option value="normal">{t('Normal')}</option>
                            <option value="debug">{t('Debug')}</option>
                        </select>
                    </div>

                    <div className="debug-control-group">
                        <label>{t('Lines to show')}:</label>
                        <select
                            value={limit}
                            onChange={(e) => setLimit(Number(e.target.value))}
                            className="form-select"
                            style={{ width: 'auto', fontSize: 13 }}
                        >
                            <option value={100}>100</option>
                            <option value={500}>500</option>
                            <option value={1000}>1000</option>
                            <option value={5000}>5000</option>
                        </select>
                    </div>

                    <div className="debug-control-group">
                        <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                            <input
                                type="checkbox"
                                checked={autoScroll}
                                onChange={(e) => setAutoScroll(e.target.checked)}
                            />
                            {t('Auto-scroll')}
                        </label>
                    </div>

                    <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
                        <button onClick={copyToClipboard} className="btn btn-sm btn-ghost" title={t('Copy to Clipboard')}>
                            <Copy size={14} />
                        </button>
                        <button onClick={clearLogs} className="btn btn-sm btn-red" title={t('Clear Logs')}>
                            <Trash2 size={14} />
                        </button>
                    </div>
                </div>

                {message && <div className="debug-message">{message}</div>}

                <div className="debug-log-container" ref={logContainerRef}>
                    {logs.length === 0 ? (
                        <div className="debug-empty">{t('No logs found')}</div>
                    ) : (
                        logs.map((log, i) => (
                            <div key={i} className="debug-log-line">
                                <span className="line-num">{i + 1}</span>
                                <span className="line-text">{log}</span>
                            </div>
                        ))
                    )}
                </div>
            </div>

            <style jsx>{`
                .debug-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0, 0, 0, 0.4);
                    backdrop-filter: blur(4px);
                    z-index: 1000;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                }
                .debug-panel {
                    width: 1000px;
                    max-width: 95vw;
                    height: 80vh;
                    background: #0d1117;
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-md);
                    display: flex;
                    flex-direction: column;
                    overflow: hidden;
                    box-shadow: 0 20px 50px rgba(0,0,0,0.5);
                }
                .debug-header {
                    padding: 16px 20px;
                    border-bottom: 1px solid var(--border-subtle);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    background: #161b22;
                }
                .debug-controls {
                    padding: 12px 20px;
                    display: flex;
                    gap: 20px;
                    align-items: center;
                    background: #0d1117;
                    border-bottom: 1px solid var(--border-subtle);
                    font-size: 13px;
                }
                .debug-control-group {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                .debug-message {
                    padding: 8px 20px;
                    background: var(--bg-hover);
                    font-size: 12px;
                    color: var(--accent-blue);
                }
                .debug-log-container {
                    flex: 1;
                    padding: 12px;
                    overflow-y: auto;
                    font-family: var(--font-mono), monospace;
                    font-size: 12px;
                    color: #e6edf3;
                    background: #0d1117;
                }
                .debug-log-line {
                    display: flex;
                    gap: 12px;
                    padding: 2px 0;
                    border-bottom: 1px solid rgba(255,255,255,0.03);
                }
                .line-num {
                    color: #484f58;
                    width: 32px;
                    text-align: right;
                    flex-shrink: 0;
                    user-select: none;
                }
                .line-text {
                    white-space: pre-wrap;
                    word-break: break-all;
                }
                .debug-empty {
                    height: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: #484f58;
                }
                .btn-icon {
                    background: transparent;
                    border: none;
                    color: #8b949e;
                    cursor: pointer;
                    padding: 4px;
                    border-radius: 4px;
                }
                .btn-icon:hover {
                    color: #e6edf3;
                    background: rgba(255,255,255,0.1);
                }
            `}</style>
        </div>
    );
}
