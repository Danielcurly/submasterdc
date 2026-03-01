'use client';

import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { API_BASE } from '@/lib/api';
import { ChevronRight, Folder, FileVideo, ArrowUp, RefreshCw, AlertCircle } from 'lucide-react';

interface FileEntry {
    name: string;
    path: string;
    type: 'file' | 'directory';
    size: number | null;
}

interface ExplorerResponse {
    current_path: string;
    contents: FileEntry[];
}

export default function ManualPage() {
    const [currentPath, setCurrentPath] = useState<string>('/');
    const [contents, setContents] = useState<FileEntry[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    // Form state
    const [selectedFile, setSelectedFile] = useState<string>('');
    const [targetLang, setTargetLang] = useState('es');
    const [bilingual, setBilingual] = useState(false);
    const [secondaryLang, setSecondaryLang] = useState('en');
    const [bilingualFilenameCode, setBilingualFilenameCode] = useState('primary');
    const [submitLoading, setSubmitLoading] = useState(false);
    const [successMessage, setSuccessMessage] = useState('');
    const { t } = useLanguage();

    const langOptions = [
        { code: 'en', name: 'English' }, { code: 'zh', name: 'Chinese' },
        { code: 'es', name: 'Spanish' }, { code: 'fr', name: 'French' },
        { code: 'de', name: 'German' }, { code: 'ja', name: 'Japanese' },
        { code: 'it', name: 'Italian' }, { code: 'pt', name: 'Portuguese' },
        { code: 'ru', name: 'Russian' }, { code: 'ko', name: 'Korean' }
    ];

    const fetchDirectory = async (path: string) => {
        setLoading(true);
        setError('');
        try {
            const res = await fetch(`${API_BASE}/api/explorer?path=${encodeURIComponent(path)}`);
            if (!res.ok) throw new Error('Failed to load directory');
            const data: ExplorerResponse = await res.json();
            setContents(data.contents);
            setCurrentPath(data.current_path);
        } catch (err: any) {
            setError(err.message || 'Error communicating with server');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        // Initial load
        fetchDirectory('/');
    }, []);

    const handleEntryClick = (entry: FileEntry) => {
        if (entry.type === 'directory') {
            fetchDirectory(entry.path);
        } else {
            setSelectedFile(entry.path);
        }
    };

    const handleGenerate = async () => {
        if (!selectedFile) return;
        setSubmitLoading(true);
        setSuccessMessage('');
        setError('');

        const paramsObj = {
            target_language: targetLang,
            bilingual_subtitles: bilingual,
            secondary_language: bilingual ? secondaryLang : 'en',
            bilingual_filename_code: bilingualFilenameCode
        };

        try {
            const res = await fetch(`${API_BASE}/api/tasks`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_path: selectedFile,
                    params: JSON.stringify(paramsObj)
                })
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || t('Failed to submit task'));
            }

            setSuccessMessage(`${t('Task submitted to generate subtitles for')} ${selectedFile.split(/[\/\\]/).pop()}`);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setSubmitLoading(false);
        }
    };

    return (
        <div className="page-container">
            <header className="page-header">
                <div>
                    <h1 className="page-title">{t('Manual Generation')}</h1>
                    <p className="page-description">{t('Bypass library settings and forcibly generate subtitles for a specific file.')}</p>
                </div>
            </header>

            <div className="card" style={{ marginBottom: '20px' }}>
                <h3 className="card-title">1. {t('Select Video File')}</h3>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '15px' }}>
                    <div className="form-input" style={{ flex: 1, padding: '8px 12px', fontSize: '13px', backgroundColor: 'var(--surface)' }}>
                        {currentPath}
                    </div>
                    <button className="btn btn-secondary" onClick={() => fetchDirectory(currentPath)} disabled={loading}>
                        <RefreshCw size={14} className={loading ? 'spin' : ''} />
                    </button>
                </div>

                <div style={{
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    maxHeight: '300px',
                    overflowY: 'auto',
                    backgroundColor: 'var(--surface-hover)',
                    marginBottom: '15px'
                }}>
                    {loading && contents.length === 0 ? (
                        <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-secondary)' }}>{t('Loading...')}</div>
                    ) : (
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
                            <tbody>
                                {contents.map((entry, idx) => (
                                    <tr
                                        key={idx}
                                        onClick={() => handleEntryClick(entry)}
                                        style={{
                                            cursor: 'pointer',
                                            borderBottom: '1px solid var(--border)',
                                            backgroundColor: selectedFile === entry.path ? 'var(--primary-light)' : 'transparent',
                                            transition: 'background-color 0.2s'
                                        }}
                                        className="table-row-hover"
                                    >
                                        <td style={{ padding: '10px 15px', color: selectedFile === entry.path ? 'var(--primary)' : 'var(--text)' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                                {entry.name === '..' ? <ArrowUp size={16} color="var(--text-secondary)" /> :
                                                    entry.type === 'directory' ? <Folder size={16} color="var(--primary)" fill="var(--primary-light)" /> :
                                                        <FileVideo size={16} color="var(--text-secondary)" />}
                                                <span style={{ fontWeight: entry.type === 'directory' ? 500 : 400 }}>{entry.name}</span>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                                {contents.length === 0 && !loading && (
                                    <tr>
                                        <td style={{ padding: '20px', textAlign: 'center', color: 'var(--text-secondary)' }}>{t('Directory is empty')}</td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    )}
                </div>

                {selectedFile && (
                    <div style={{ fontSize: '13px', color: 'var(--primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <FileVideo size={14} /> <strong>{t('Selected')}:</strong> {selectedFile}
                    </div>
                )}
            </div>

            <div className="card" style={{ opacity: selectedFile ? 1 : 0.5, transition: 'opacity 0.3s' }}>
                <h3 className="card-title">2. {t('Configuration & Execution')}</h3>
                {error && (
                    <div style={{ padding: '12px', backgroundColor: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', borderRadius: '6px', marginBottom: '15px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <AlertCircle size={16} /> {error}
                    </div>
                )}
                {successMessage && (
                    <div style={{ padding: '12px', backgroundColor: 'rgba(34, 197, 94, 0.1)', color: '#22c55e', borderRadius: '6px', marginBottom: '15px', fontSize: '13px' }}>
                        ✅ {successMessage}
                    </div>
                )}

                <div className="form-group">
                    <label className="form-label">{t('Target Language')}</label>
                    <select
                        className="form-input"
                        value={targetLang}
                        onChange={(e) => setTargetLang(e.target.value)}
                        disabled={!selectedFile}
                    >
                        {langOptions.map(l => <option key={l.code} value={l.code}>{t(l.name)} ({l.code})</option>)}
                    </select>
                </div>

                <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '20px' }}>
                    <input
                        type="checkbox"
                        id="bilingual"
                        checked={bilingual}
                        onChange={(e) => setBilingual(e.target.checked)}
                        disabled={!selectedFile}
                        style={{ width: '16px', height: '16px', accentColor: 'var(--primary)' }}
                    />
                    <label htmlFor="bilingual" className="form-label" style={{ marginBottom: 0, cursor: 'pointer' }}>
                        {t('Generate Bilingual Subtitles')}
                    </label>
                </div>

                {bilingual && (
                    <>
                        <div className="form-group" style={{ marginTop: '15px', paddingLeft: '26px' }}>
                            <label className="form-label">{t('Secondary Language')}</label>
                            <select
                                className="form-input"
                                value={secondaryLang}
                                onChange={(e) => setSecondaryLang(e.target.value)}
                                disabled={!selectedFile}
                            >
                                {langOptions.map(l => <option key={l.code} value={l.code}>{t(l.name)} ({l.code})</option>)}
                            </select>
                        </div>

                        <div className="form-group" style={{ marginTop: '15px', paddingLeft: '26px' }}>
                            <label className="form-label">{t('Bilingual Filename Code')}</label>
                            <select
                                className="form-input"
                                value={bilingualFilenameCode}
                                onChange={(e) => setBilingualFilenameCode(e.target.value)}
                                disabled={!selectedFile}
                            >
                                <option value="primary">{t('Primary')} ({targetLang})</option>
                                <option value="secondary">{t('Secondary')} ({secondaryLang})</option>
                            </select>
                        </div>
                    </>
                )}

                <div style={{ marginTop: '25px' }}>
                    <button
                        className="btn btn-primary"
                        onClick={handleGenerate}
                        disabled={submitLoading || !selectedFile}
                        style={{ width: '100%', padding: '12px', fontSize: '15px', fontWeight: 600 }}
                    >
                        {submitLoading ? t('Submitting Task...') : t('Force Generate Subtitles')}
                    </button>
                    <p style={{ marginTop: '10px', fontSize: '12px', color: 'var(--text-secondary)', textAlign: 'center' }}>
                        {t('Warning: This will skip metadata checks and overwrite existing external subtitles with the same name.')}
                    </p>
                </div>
            </div>
        </div>
    );
}
