'use client';

import { useEffect, useState } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { getLibraries, addLibrary, updateLibrary, deleteLibrary, browseDirectory, API_BASE } from '@/lib/api';
import {
    Library as LibraryIcon, FolderOpen, Plus, Trash2, ChevronUp,
    Folder, HardDrive, AlertTriangle, Settings2, Clock, CheckCircle2, X, ArrowUp
} from 'lucide-react';

interface FileEntry {
    name: string;
    path: string;
    type: 'file' | 'directory';
    size: number | null;
}

interface Library {
    id: string; name: string; path: string; scan_mode: string;
    scan_interval_hours: number; path_exists: boolean;
}

const DHMInputs = ({ valueHours, onChange, disabled }: { valueHours: number, onChange: (h: number) => void, disabled?: boolean }) => {
    // Round to avoid float precision issues in UI
    const totalMinutes = Math.round(valueHours * 60);
    const d = Math.floor(totalMinutes / (24 * 60));
    const h = Math.floor((totalMinutes % (24 * 60)) / 60);
    const m = totalMinutes % 60;

    const update = (newD: number, newH: number, newM: number) => {
        const total = (newD * 24 * 60) + (newH * 60) + newM;
        onChange(total / 60);
    };

    return (
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', opacity: disabled ? 0.5 : 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <input type="number" className="form-input" style={{ width: 42, padding: 4, textAlign: 'center', fontSize: 12 }}
                    value={d} min={0} disabled={disabled} onChange={e => update(Number(e.target.value), h, m)} />
                <span style={{ fontSize: 10, fontWeight: 800, color: 'var(--text-muted)' }}>D</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <input type="number" className="form-input" style={{ width: 42, padding: 4, textAlign: 'center', fontSize: 12 }}
                    value={h} min={0} max={23} disabled={disabled} onChange={e => update(d, Number(e.target.value), m)} />
                <span style={{ fontSize: 10, fontWeight: 800, color: 'var(--text-muted)' }}>H</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <input type="number" className="form-input" style={{ width: 42, padding: 4, textAlign: 'center', fontSize: 12 }}
                    value={m} min={0} max={59} disabled={disabled} onChange={e => update(d, h, Number(e.target.value))} />
                <span style={{ fontSize: 10, fontWeight: 800, color: 'var(--text-muted)' }}>M</span>
            </div>
        </div>
    );
};

export default function LibrariesPage() {
    const [libraries, setLibraries] = useState<Library[]>([]);
    const [newName, setNewName] = useState('New Library');
    const [currentPath, setCurrentPath] = useState('');
    const [dirs, setDirs] = useState<FileEntry[]>([]);
    const [loadingDirs, setLoadingDirs] = useState(false);
    const [newMode, setNewMode] = useState('manual');
    const [newInterval, setNewInterval] = useState(24);
    const [message, setMessage] = useState('');
    const [showAddMenu, setShowAddMenu] = useState(false);

    // Inline editing states
    const [editingId, setEditingId] = useState<string | null>(null);
    const [editName, setEditName] = useState('');
    const { t } = useLanguage();

    const load = async () => { setLibraries(await getLibraries()); };
    useEffect(() => { load(); }, []);

    const browse = async (path: string) => {
        setLoadingDirs(true);
        try {
            const res = await fetch(`${API_BASE}/api/explorer?path=${encodeURIComponent(path)}`);
            if (!res.ok) throw new Error('Failed to load');
            const data = await res.json();
            setCurrentPath(data.current_path);
            setDirs(data.contents.filter((e: any) => e.type === 'directory' || e.name === '..'));
        } catch { setDirs([]); } finally { setLoadingDirs(false); }
    };
    useEffect(() => { browse('/'); }, []);

    const handleAdd = async () => {
        if (!currentPath) return;
        try {
            await addLibrary({ name: newName, path: currentPath, scan_mode: newMode });
            setMessage(`Library "${newName}" added!`);
            setNewName('New Library');
            setShowAddMenu(false);
            await load();
        } catch (e: unknown) { setMessage(`Error: ${e instanceof Error ? e.message : 'Unknown'}`); }
    };

    const handleModeChange = async (id: string, mode: string) => {
        await updateLibrary(id, { scan_mode: mode });
        await load();
    };

    const handleIntervalChange = async (id: string, hours: number) => {
        await updateLibrary(id, { scan_interval_hours: hours });
        await load();
    };

    const handleRenameSubmit = async (id: string) => {
        if (!editName.trim()) {
            setEditingId(null);
            return;
        }
        setEditingId(null);
        try {
            await updateLibrary(id, { name: editName.trim() });
            setMessage(t('Library renamed to {name}').replace('{name}', editName.trim()));
            await load();
        } catch (error: any) {
            setMessage(t('Failed to rename library: {error}').replace('{error}', error.message || error));
        }
    };

    const startEditing = (id: string, currentName: string) => {
        setEditName(currentName);
        setEditingId(id);
    };

    const handleDelete = async (id: string, name: string) => {
        try {
            await deleteLibrary(id);
            setMessage(`Library "${name}" deleted.`);
            await load();
        } catch (error: any) {
            console.error('[handleDelete] Error:', error);
            setMessage(`Failed to delete library: ${error.message || error}`);
        }
    };

    return (
        <>
            <div className="page-header">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        <h1 className="page-title">
                            <span className="page-title-icon"><LibraryIcon size={20} /></span>
                            {t('Libraries')}
                        </h1>
                        <p className="page-subtitle">{t('Configure and manage your media library folders.')}</p>
                    </div>
                    <button className="btn btn-primary" onClick={() => setShowAddMenu(true)}>
                        <Plus size={16} /> {t('New Library')}
                    </button>
                </div>
            </div>

            {message && <div className="info-box" style={{ marginBottom: 20 }}>{message}</div>}

            {/* Existing Libraries */}
            <div className="section">
                <div className="section-header">
                    <div className="section-title">
                        <FolderOpen size={18} className="section-title-icon" />
                        <h2>{t('Configured Libraries')}</h2>
                    </div>
                    <span className="chip chip-gray">{libraries.length} {t('total')}</span>
                </div>

                {libraries.length === 0 ? (
                    <div className="empty-state">
                        <FolderOpen size={48} className="empty-state-icon" />
                        <p>{t('No libraries configured yet')}</p>
                    </div>
                ) : (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'flex-start' }}>
                        {libraries.map(lib => (
                            <div key={lib.id} className="card" style={{ width: 320, flexShrink: 0, padding: 18, display: 'flex', flexDirection: 'column', gap: 14 }}>
                                {/* Header (Icon, Name, Delete) */}
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                    <div style={{ display: 'flex', gap: 12, alignItems: 'center', minWidth: 0, flex: 1 }}>
                                        <div className="card-icon purple" style={{ flexShrink: 0, width: 32, height: 32, padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                            <HardDrive size={16} />
                                        </div>
                                        {editingId === lib.id ? (
                                            <input
                                                type="text"
                                                className="form-input"
                                                value={editName}
                                                onChange={e => setEditName(e.target.value)}
                                                onBlur={() => handleRenameSubmit(lib.id)}
                                                onKeyDown={e => {
                                                    if (e.key === 'Enter') {
                                                        e.currentTarget.blur();
                                                    } else if (e.key === 'Escape') {
                                                        setEditingId(null);
                                                    }
                                                }}
                                                // eslint-disable-next-line jsx-a11y/no-autofocus
                                                autoFocus
                                                style={{ flex: 1, padding: '4px 8px', fontSize: 13, minWidth: 0, height: 28 }}
                                            />
                                        ) : (
                                            <h3
                                                style={{ margin: 0, fontSize: 15, fontWeight: 600, color: 'var(--text-bright)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', cursor: 'text' }}
                                                onClick={() => startEditing(lib.id, lib.name)}
                                                title="Click to rename"
                                            >
                                                {lib.name}
                                            </h3>
                                        )}
                                    </div>
                                    <button
                                        className="btn btn-danger btn-sm btn-icon"
                                        onClick={() => handleDelete(lib.id, lib.name)}
                                        title="Delete library"
                                        style={{ padding: 6, opacity: 0.6, margin: '-6px -6px 0 0' }}
                                        onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
                                        onMouseLeave={(e) => e.currentTarget.style.opacity = '0.6'}
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                </div>

                                {/* Path */}
                                <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-muted)', fontSize: 12, marginTop: 4 }}>
                                    <FolderOpen size={14} style={{ flexShrink: 0 }} />
                                    <code style={{ background: 'var(--bg-darker)', padding: '2px 6px', borderRadius: 4, fontFamily: 'monospace', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', flex: 1 }}>
                                        {lib.path}
                                    </code>
                                </div>

                                {/* Path Status */}
                                <div style={{ marginTop: -6, minHeight: 24 }}>
                                    {lib.path_exists ? (
                                        <span className="chip chip-green" style={{
                                            color: '#4ade80',
                                            background: 'rgba(34, 197, 94, 0.15)',
                                            fontWeight: 700
                                        }}>
                                            <CheckCircle2 size={10} /> {t('PATH VALID')}
                                        </span>
                                    ) : (
                                        <span className="chip chip-red" style={{ fontWeight: 700 }}>
                                            <AlertTriangle size={10} /> {t('PATH NOT FOUND')}
                                        </span>
                                    )}
                                </div>

                                {/* Scan Mode */}
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 4 }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-muted)', fontSize: 13 }}>
                                        <Settings2 size={14} />
                                        <span>{t('Scan Mode')}</span>
                                    </div>
                                    <select
                                        className="form-select"
                                        value={lib.scan_mode}
                                        onChange={e => handleModeChange(lib.id, e.target.value)}
                                        style={{ width: 140, padding: '4px 8px', fontSize: 12 }}
                                    >
                                        <option value="manual">{t('Manual')}</option>
                                        <option value="periodic">{t('Periodic')}</option>
                                        <option value="automatic">{t('Automatic (Watchdog)')}</option>
                                    </select>
                                </div>

                                {/* Interval */}
                                <div style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'space-between',
                                    opacity: lib.scan_mode === 'periodic' ? 1 : 0.3,
                                    pointerEvents: lib.scan_mode === 'periodic' ? 'auto' : 'none',
                                    transition: 'opacity 0.2s ease'
                                }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-muted)', fontSize: 13 }}>
                                        <Clock size={14} />
                                        <span>{t('Interval')}</span>
                                    </div>
                                    <DHMInputs
                                        valueHours={lib.scan_interval_hours}
                                        disabled={lib.scan_mode !== 'periodic'}
                                        onChange={h => handleIntervalChange(lib.id, h)}
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Modal Popup for Adding Library */}
            {showAddMenu && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: 'rgba(0, 0, 0, 0.75)',
                    backdropFilter: 'blur(8px)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 9999,
                    padding: 20
                }} onClick={() => setShowAddMenu(false)}>
                    <div className="card animate-in" style={{
                        width: '100%',
                        maxWidth: 600,
                        maxHeight: '90vh',
                        overflowY: 'auto',
                        padding: 32,
                        position: 'relative',
                        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
                        border: '1px solid var(--border-medium)',
                        backgroundColor: 'var(--bg-secondary)'
                    }} onClick={e => e.stopPropagation()}>

                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                <div className="card-icon purple" style={{ width: 40, height: 40, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <Plus size={20} />
                                </div>
                                <h2 style={{ margin: 0, fontSize: '1.5rem' }}>{t('Add New Library')}</h2>
                            </div>
                            <button className="btn btn-icon btn-ghost" onClick={() => setShowAddMenu(false)} style={{ padding: 8 }}>
                                <X size={20} />
                            </button>
                        </div>

                        {/* Form Body */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                            <div className="form-group">
                                <label className="form-label">{t('Library Name')}</label>
                                <input
                                    className="form-input"
                                    value={newName}
                                    onChange={e => setNewName(e.target.value)}
                                    placeholder={t('e.g. My Movies')}
                                    style={{ padding: '10px 14px' }}
                                />
                            </div>

                            <div className="form-group">
                                <label className="form-label">{t('Directory Path')}</label>
                                <div style={{ display: 'flex', gap: 10 }}>
                                    <input
                                        className="form-input"
                                        value={currentPath}
                                        onChange={e => { setCurrentPath(e.target.value); browse(e.target.value); }}
                                        placeholder="/media..."
                                        style={{ flex: 1, padding: '10px 14px' }}
                                    />
                                    <button className="btn btn-ghost" onClick={() => {
                                        const parent = currentPath.replace(/[/\\][^/\\]*$/, '') || '';
                                        browse(parent);
                                    }} style={{ padding: '10px' }}>
                                        <ChevronUp size={18} />
                                    </button>
                                </div>
                            </div>

                            {/* Directory browser inside modal */}
                            <div className="dir-browser" style={{ maxHeight: 250, overflowY: 'auto', background: 'var(--surface-hover)', borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
                                <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-subtle)', fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', position: 'sticky', top: 0, backgroundColor: 'var(--bg-secondary)', zIndex: 1 }}>
                                    {t('Contents of')} {currentPath || '/'}
                                </div>
                                {loadingDirs ? (
                                    <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>{t('Loading...')}</div>
                                ) : dirs.length === 0 ? (
                                    <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>{t('No subdirectories found')}</div>
                                ) : (
                                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
                                        <tbody>
                                            {dirs.map((entry, idx) => (
                                                <tr
                                                    key={idx}
                                                    onClick={() => browse(entry.path)}
                                                    style={{ cursor: 'pointer', borderBottom: '1px solid var(--border-subtle)', transition: 'background-color 0.2s' }}
                                                    className="table-row-hover"
                                                >
                                                    <td style={{ padding: '10px 15px', color: 'var(--text)' }}>
                                                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                                            {entry.name === '..' ? <ArrowUp size={16} color="var(--text-secondary)" /> : <Folder size={16} color="var(--primary)" fill="var(--primary-light)" />}
                                                            <span style={{ fontWeight: 500 }}>{entry.name}</span>
                                                        </div>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                )}
                            </div>

                            <div className="grid-cols-2" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
                                <div className="form-group">
                                    <label className="form-label">{t('Scan Mode')}</label>
                                    <select className="form-select" value={newMode} onChange={e => setNewMode(e.target.value)} style={{ padding: '10px' }}>
                                        <option value="manual">{t('Manual')}</option>
                                        <option value="periodic">{t('Periodic')}</option>
                                        <option value="automatic">{t('Automatic (Watchdog)')}</option>
                                    </select>
                                </div>
                                {newMode === 'periodic' ? (
                                    <div className="form-group">
                                        <label className="form-label">{t('Interval (D H M)')}</label>
                                        <DHMInputs
                                            valueHours={newInterval}
                                            onChange={h => setNewInterval(h)}
                                        />
                                    </div>
                                ) : (
                                    <div style={{ opacity: 0.4 }}>
                                        <label className="form-label">{t('Interval (disabled)')}</label>
                                        <input type="text" className="form-input" value="N/A" disabled style={{ padding: '10px', background: 'transparent' }} />
                                    </div>
                                )}
                            </div>

                            <div style={{ display: 'flex', gap: 16, marginTop: 12 }}>
                                <button className="btn btn-ghost" style={{ flex: 1, padding: '12px' }} onClick={() => setShowAddMenu(false)}>{t('Cancel')}</button>
                                <button className="btn btn-primary" style={{ flex: 1.5, padding: '12px' }} onClick={handleAdd}>
                                    <Plus size={18} /> {t('Create Library')}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
