'use client';

import { useEffect, useState } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { getLibraries, addLibrary, updateLibrary, deleteLibrary, browseDirectory, API_BASE } from '@/lib/api';
import {
    Library as LibraryIcon, FolderOpen, Plus, Trash2, ChevronUp,
    Folder, HardDrive, AlertTriangle, Settings2, Clock, CheckCircle2, X, ArrowUp, Film
} from 'lucide-react';

interface FileEntry {
    name: string;
    path: string;
    type: 'file' | 'directory';
    size: number | null;
}

interface Library {
    id: string; name: string; path: string; scan_mode: string;
    scan_interval_hours: number; path_exists: boolean; file_count?: number;
}

const DHMInputs = ({ valueHours, onChange, disabled }: { valueHours: number, onChange: (h: number) => void, disabled?: boolean }) => {
    const totalMinutes = Math.round(valueHours * 60);
    const d = Math.floor(totalMinutes / (24 * 60));
    const h = Math.floor((totalMinutes % (24 * 60)) / 60);
    const m = totalMinutes % 60;

    const update = (newD: number, newH: number, newM: number) => {
        const total = (newD * 24 * 60) + (newH * 60) + newM;
        onChange(total / 60);
    };

    const inputStyle: React.CSSProperties = {
        width: 42,
        padding: '4px 0',
        textAlign: 'center' as const,
        fontSize: '13px',
        fontWeight: 700,
        backgroundColor: 'rgba(0,0,0,0.25)',
        border: '1px solid rgba(255,255,255,0.05)',
        borderRadius: '8px',
        color: '#f8fafc',
        outline: 'none'
    };

    const labelStyle: React.CSSProperties = {
        fontSize: '11px',
        fontWeight: 700,
        color: '#475569',
        marginLeft: '2px'
    };

    return (
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', opacity: disabled ? 0.5 : 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <input type="number" style={inputStyle} value={d} min={0} disabled={disabled} onChange={e => update(Number(e.target.value), h, m)} />
                <span style={labelStyle}>D</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <input type="number" style={inputStyle} value={h} min={0} max={23} disabled={disabled} onChange={e => update(d, Number(e.target.value), m)} />
                <span style={labelStyle}>H</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <input type="number" style={inputStyle} value={m} min={0} max={59} disabled={disabled} onChange={e => update(d, h, Number(e.target.value))} />
                <span style={labelStyle}>M</span>
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
            setMessage(t('Library "{name}" added!').replace('{name}', newName));
            setNewName('New Library');
            setShowAddMenu(false);
            await load();
        } catch (e: unknown) { setMessage(`${t('Error')}: ${e instanceof Error ? e.message : 'Unknown'}`); }
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
            setMessage(t('Library "{name}" deleted').replace('{name}', name));
            await load();
        } catch (error: any) {
            console.error('[handleDelete] Error:', error);
            setMessage(`${t('Failed to delete library')}: ${error.message || error}`);
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
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, 360px)', gap: 24, padding: '4px 0' }}>
                        {libraries.map(lib => (
                            <div key={lib.id} className="card" style={{
                                display: 'flex', flexDirection: 'column', gap: 10,
                                padding: '16px 24px 12px 24px',
                                border: '1px solid rgba(255, 255, 255, 0.05)',
                                boxShadow: '0 8px 30px rgba(0, 0, 0, 0.2)',
                                borderRadius: '16px',
                                backgroundColor: 'var(--bg-secondary)',
                                transition: 'all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1)',
                            }}>
                                {/* Top Content Flexbox (Two Rows) */}
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>

                                    {/* Upper Section: Icon, Title, Path, Trash */}
                                    <div style={{ display: 'flex', gap: '20px', alignItems: 'flex-start' }}>
                                        {/* Icon */}
                                        <div style={{
                                            width: '48px', height: '48px', borderRadius: '12px',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            backgroundColor: 'rgba(99, 102, 241, 0.08)',
                                            boxShadow: 'inset 0 0 0 1px rgba(99, 102, 241, 0.1), 0 0 24px rgba(99, 102, 241, 0.15)',
                                            color: '#818cf8', flexShrink: 0
                                        }}>
                                            <HardDrive size={24} strokeWidth={1.5} />
                                        </div>

                                        {/* Title & Path */}
                                        <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '6px', paddingTop: '4px' }}>
                                            {editingId === lib.id ? (
                                                <input
                                                    type="text"
                                                    className="form-input"
                                                    value={editName}
                                                    onChange={e => setEditName(e.target.value)}
                                                    onBlur={() => handleRenameSubmit(lib.id)}
                                                    onKeyDown={e => {
                                                        if (e.key === 'Enter') e.currentTarget.blur();
                                                        else if (e.key === 'Escape') setEditingId(null);
                                                    }}
                                                    // eslint-disable-next-line jsx-a11y/no-autofocus
                                                    autoFocus
                                                    style={{ width: '100%', padding: '6px 12px', fontSize: '18px', fontWeight: 800 }}
                                                />
                                            ) : (
                                                <h3 style={{
                                                    margin: 0, fontSize: '18px', fontWeight: 800,
                                                    color: '#f8fafc', whiteSpace: 'nowrap',
                                                    overflow: 'hidden', textOverflow: 'ellipsis', cursor: 'pointer',
                                                    letterSpacing: '-0.02em', lineHeight: 1.2
                                                }} onClick={() => startEditing(lib.id, lib.name)} title={t("Click to rename")}>
                                                    {lib.name}
                                                </h3>
                                            )}
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#64748b', fontSize: '13px', fontFamily: 'monospace' }}>
                                                <FolderOpen size={14} style={{ opacity: 0.8 }} />
                                                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{lib.path}</span>
                                            </div>
                                        </div>

                                        {/* Trash */}
                                        <button
                                            className="btn btn-ghost"
                                            onClick={() => handleDelete(lib.id, lib.name)}
                                            style={{ padding: '10px', borderRadius: '10px', color: '#ef4444', border: '1px solid rgba(239,68,68,0.15)', backgroundColor: 'transparent', flexShrink: 0 }}
                                            title={t("Delete library")}
                                        >
                                            <Trash2 size={20} />
                                        </button>
                                    </div>

                                    {/* Middle Section: Status and Videos count */}
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                        <div style={{
                                            display: 'flex', alignItems: 'center', gap: '8px',
                                            padding: '6px 14px', borderRadius: '20px',
                                            backgroundColor: lib.path_exists ? 'rgba(74, 222, 128, 0.08)' : 'rgba(239, 68, 68, 0.08)',
                                            boxShadow: lib.path_exists
                                                ? '0 2px 10px rgba(74, 222, 128, 0.1), inset 0 0 10px rgba(74, 222, 128, 0.05)'
                                                : '0 2px 10px rgba(239, 68, 68, 0.1), inset 0 0 10px rgba(239, 68, 68, 0.05)',
                                            whiteSpace: 'nowrap'
                                        }}>
                                            <div style={{
                                                width: '8px', height: '8px', borderRadius: '50%',
                                                backgroundColor: lib.path_exists ? '#4ade80' : '#ef4444',
                                                boxShadow: lib.path_exists
                                                    ? '0 0 8px rgba(74, 222, 128, 0.8)'
                                                    : '0 0 8px rgba(239, 68, 68, 0.8)'
                                            }} />
                                            <span style={{
                                                fontSize: '11px', fontWeight: 800, letterSpacing: '0.05em',
                                                color: lib.path_exists ? '#4ade80' : '#ef4444'
                                            }}>
                                                {lib.path_exists ? t('PATH VALID') : t('PATH NOT FOUND')}
                                            </span>
                                        </div>
                                        <div style={{
                                            display: 'flex', alignItems: 'center', gap: '6px',
                                            padding: '8px 16px', borderRadius: '20px',
                                            backgroundColor: 'rgba(99, 102, 241, 0.1)', color: '#a5b4fc',
                                            fontSize: '13px', fontWeight: 700, border: '1px solid rgba(99, 102, 241, 0.25)',
                                            boxShadow: '0 0 15px rgba(99, 102, 241, 0.15)'
                                        }}>
                                            <Film size={14} strokeWidth={2.5} />
                                            <span>{lib.file_count || 0} {t('Videos')}</span>
                                        </div>
                                    </div>
                                </div>

                                {/* Divider */}
                                <div style={{ height: '1px', backgroundColor: 'rgba(255,255,255,0.05)', margin: '0' }} />

                                {/* Bottom Controls */}
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                    <div style={{ fontSize: '12px', fontWeight: 800, color: '#64748b', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                                        SCAN MODE
                                    </div>

                                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                        <Settings2 size={14} color="#64748b" />
                                        <select
                                            className="form-select"
                                            value={lib.scan_mode}
                                            onChange={e => handleModeChange(lib.id, e.target.value)}
                                            style={{
                                                padding: '8px 12px', fontSize: '14px',
                                                backgroundColor: 'rgba(255,255,255,0.03)',
                                                border: '1px solid rgba(255,255,255,0.08)',
                                                borderRadius: '8px', minWidth: '180px',
                                                color: '#f8fafc',
                                                cursor: 'pointer'
                                            }}
                                        >
                                            <option style={{ backgroundColor: '#1e293b', color: '#f8fafc' }} value="manual">{t('Manual')}</option>
                                            <option style={{ backgroundColor: '#1e293b', color: '#f8fafc' }} value="periodic">{t('Periodic')}</option>
                                            <option style={{ backgroundColor: '#1e293b', color: '#f8fafc' }} value="automatic">{t('Automatic (Watchdog)')}</option>
                                        </select>
                                    </div>
                                </div>

                                {/* Interval (Periodic only) */}
                                <div style={{
                                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px',
                                    height: lib.scan_mode === 'periodic' ? '32px' : '0',
                                    opacity: lib.scan_mode === 'periodic' ? 1 : 0,
                                    marginTop: lib.scan_mode === 'periodic' ? '2px' : '0',
                                    overflow: 'hidden', transition: 'all 0.3s ease'
                                }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#475569', fontSize: '14px', fontWeight: 600 }}>
                                        <Clock size={16} />
                                        <span>{t('Interval')}:</span>
                                    </div>
                                    <DHMInputs
                                        valueHours={lib.scan_interval_hours}
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
