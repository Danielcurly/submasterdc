'use client';

import { useState, useEffect, useRef } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { API_BASE, getSubtitleStyle, updateSubtitleStyle } from '@/lib/api';
import { ChevronRight, ChevronDown, ChevronUp, Folder, FileVideo, ArrowUp, RefreshCw, AlertCircle, Palette as PaletteIcon } from 'lucide-react';
import { toast } from 'react-hot-toast';

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

// ASS color helpers
const assToHex = (ass: string) => {
    if (!ass || !ass.startsWith('&H')) return '#ffffff';
    const bgr = ass.substring(4, 10);
    return `#${bgr.substring(4, 6)}${bgr.substring(2, 4)}${bgr.substring(0, 2)}`;
};
const hexToAss = (hex: string) => {
    return `&H00${hex.substring(5, 7)}${hex.substring(3, 5)}${hex.substring(1, 3)}`;
};

const PLAY_RES_Y = 288;
const FONT_SCALE: Record<number, number> = {
    1: 10, 2: 14, 3: 18, 4: 22, 5: 28, 6: 34, 7: 40
};
const SIZE_LABELS: Record<number, string> = {
    1: 'XS', 2: 'S', 3: 'M', 4: 'L', 5: 'XL', 6: '2XL', 7: '3XL'
};

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
    const [styleUpdateLoading, setStyleUpdateLoading] = useState(false);
    const [isManualOpen, setIsManualOpen] = useState(true);
    const [isStyleEditorOpen, setIsStyleEditorOpen] = useState(false);
    const [successMessage, setSuccessMessage] = useState('');
    const { t } = useLanguage();

    // Style state
    const [style, setStyle] = useState({
        font_size_step: 4,
        primary_color: '&H00DFDFDF',
        secondary_color: '&H0000FFFF',
        target_format: 'ass'
    });
    const previewRef = useRef<HTMLDivElement>(null);
    const [previewWidth, setPreviewWidth] = useState(0);

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
        fetchDirectory('/');
        // Load global style
        getSubtitleStyle().then(s => setStyle(s)).catch(() => { });
    }, []);

    // Preview sizing
    useEffect(() => {
        if (!previewRef.current) return;
        const update = () => { if (previewRef.current) setPreviewWidth(previewRef.current.offsetWidth); };
        const ro = new ResizeObserver(update);
        ro.observe(previewRef.current);
        update();
        return () => ro.disconnect();
    }, [isStyleEditorOpen]);

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

    const handleUpdateStyles = async () => {
        if (!selectedFile) return;
        setStyleUpdateLoading(true);
        setSuccessMessage('');
        setError('');

        try {
            // Save the style globally first
            await updateSubtitleStyle(style);

            const res = await fetch(`${API_BASE}/api/tasks`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_path: selectedFile,
                    params: JSON.stringify({ action: 'update_style' })
                })
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || t('Failed to submit task'));
            }

            setSuccessMessage(`${t('Task submitted to update styles for')} ${selectedFile.split(/[\/\\]/).pop()}`);
            toast.success(t('Style saved and update task queued'));
        } catch (err: any) {
            setError(err.message);
        } finally {
            setStyleUpdateLoading(false);
        }
    };

    const primaryFontSize = FONT_SCALE[style.font_size_step] || 22;
    const secondaryFontSize = Math.floor(primaryFontSize * 0.5);
    const boxHeight = previewWidth * 0.5625;
    const scaledPrimary = boxHeight > 0 ? (primaryFontSize / PLAY_RES_Y) * boxHeight : 0;
    const scaledSecondary = boxHeight > 0 ? (secondaryFontSize / PLAY_RES_Y) * boxHeight : 0;

    return (
        <div className="page-container">
            <header className="page-header">
                <div>
                    <h1 className="page-title">{t('Single File Operations')}</h1>
                    <p className="page-description">{t('Bypass library settings and forcibly generate or update subtitles for a specific file.')}</p>
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

            <div style={{ display: 'flex', flexDirection: 'column', gap: '15px', opacity: selectedFile ? 1 : 0.5, transition: 'opacity 0.3s' }}>
                <div className="card" style={{ padding: '0' }}>
                    <div
                        style={{ padding: '15px 20px', cursor: selectedFile ? 'pointer' : 'default', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                        onClick={() => selectedFile && setIsManualOpen(!isManualOpen)}
                    >
                        <h3 className="card-title" style={{ margin: 0 }}>2. {t('Manual Generation')}</h3>
                        {isManualOpen ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                    </div>

                    {isManualOpen && (
                        <div style={{ padding: '20px', paddingTop: '10px', borderTop: '1px solid var(--border)' }}>
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
                                    <div style={{ padding: '10px 12px', backgroundColor: 'rgba(59, 130, 246, 0.05)', border: '1px solid rgba(59, 130, 246, 0.2)', borderRadius: '6px', marginBottom: '15px', fontSize: '12px', display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                                        <AlertCircle size={14} style={{ marginTop: '2px', color: 'var(--primary)' }} />
                                        <div style={{ color: 'var(--text-secondary)' }}>
                                            <strong style={{ color: 'var(--primary)', display: 'block', marginBottom: '2px' }}>{t('Bilingual Styling Note')}</strong>
                                            {t('Advanced styling (colors, sizes) is only supported in ASS format for bilingual subtitles. SRT format will remain plain text.')}
                                        </div>
                                    </div>
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
                    )}
                </div>

                <div className="card" style={{ padding: '0' }}>
                    <div
                        style={{ padding: '15px 20px', cursor: selectedFile ? 'pointer' : 'default', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                        onClick={() => selectedFile && setIsStyleEditorOpen(!isStyleEditorOpen)}
                    >
                        <h3 className="card-title" style={{ margin: 0 }}>3. {t('Style Editor')}</h3>
                        {isStyleEditorOpen ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                    </div>

                    {isStyleEditorOpen && (
                        <div style={{ padding: '20px', paddingTop: '10px', borderTop: '1px solid var(--border)' }}>
                            <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '20px' }}>
                                {t('Apply your global subtitle styles to the currently selected file. This will re-export the subtitles matching the target format without re-translating.')}
                            </p>

                            {/* Font Size Selector */}
                            <div style={{ marginBottom: '20px' }}>
                                <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', marginBottom: 8, display: 'block' }}>
                                    {t('Font Size')}
                                </label>
                                <div style={{ display: 'flex', gap: 4 }}>
                                    {[1, 2, 3, 4, 5, 6, 7].map(s => (
                                        <button
                                            key={s}
                                            onClick={() => setStyle({ ...style, font_size_step: s })}
                                            style={{
                                                flex: 1, padding: '8px 0', borderRadius: 6, border: 'none', cursor: 'pointer',
                                                fontSize: 11, fontWeight: 700, transition: 'all 0.15s ease',
                                                background: style.font_size_step === s ? 'var(--primary)' : 'var(--surface-hover)',
                                                color: style.font_size_step === s ? '#fff' : 'var(--text-secondary)',
                                            }}
                                        >
                                            {SIZE_LABELS[s]}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Color Pickers */}
                            <div style={{ display: 'flex', gap: 12, marginBottom: '20px' }}>
                                <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', background: 'var(--surface-hover)', borderRadius: 8, border: '1px solid var(--border)' }}>
                                    <input
                                        type="color"
                                        value={assToHex(style.primary_color)}
                                        onChange={(e) => setStyle({ ...style, primary_color: hexToAss(e.target.value) })}
                                        style={{ width: 30, height: 30, borderRadius: 6, border: 'none', cursor: 'pointer', background: 'transparent', padding: 0 }}
                                    />
                                    <div>
                                        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>{t('Primary')}</div>
                                        <div style={{ fontSize: 10, color: 'var(--text-secondary)' }}>{t('Main Text')}</div>
                                    </div>
                                </div>
                                <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', background: 'var(--surface-hover)', borderRadius: 8, border: '1px solid var(--border)' }}>
                                    <input
                                        type="color"
                                        value={assToHex(style.secondary_color)}
                                        onChange={(e) => setStyle({ ...style, secondary_color: hexToAss(e.target.value) })}
                                        style={{ width: 30, height: 30, borderRadius: 6, border: 'none', cursor: 'pointer', background: 'transparent', padding: 0 }}
                                    />
                                    <div>
                                        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>{t('Secondary')}</div>
                                        <div style={{ fontSize: 10, color: 'var(--text-secondary)' }}>{t('Translation')}</div>
                                    </div>
                                </div>
                            </div>

                            {/* Live Preview */}
                            <div ref={previewRef} style={{ marginBottom: '20px', borderRadius: 8, overflow: 'hidden', border: '1px solid var(--border)' }}>
                                <div style={{ position: 'relative', width: '100%', paddingBottom: '56.25%', background: '#000' }}>
                                    <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', alignItems: 'center', paddingBottom: '8%' }}>
                                        <div style={{
                                            color: assToHex(style.primary_color),
                                            fontSize: scaledPrimary ? `${scaledPrimary}px` : '14px',
                                            fontFamily: 'Microsoft YaHei, sans-serif',
                                            fontWeight: 'bold', textAlign: 'center', lineHeight: 1.15,
                                            textShadow: '2px 2px 1px #000, -1px -1px 0px #000, 1px -1px 0px #000, -1px 1px 0px #000',
                                            maxWidth: '92%', transition: 'all 0.1s ease-out'
                                        }}>
                                            你好，这是预览字幕。
                                        </div>
                                        <div style={{
                                            color: assToHex(style.secondary_color),
                                            fontSize: scaledSecondary ? `${scaledSecondary}px` : '8px',
                                            fontFamily: 'Microsoft YaHei, sans-serif',
                                            textAlign: 'center', lineHeight: 1.15, marginTop: '0.8%',
                                            textShadow: '1px 1px 1px #000, -1px -1px 0px #000',
                                            maxWidth: '92%', transition: 'all 0.1s ease-out'
                                        }}>
                                            Hello, this is a bilingual subtitle preview.
                                        </div>
                                    </div>
                                    <div style={{
                                        position: 'absolute', top: 8, left: 12, fontSize: 9,
                                        fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase',
                                        letterSpacing: '0.1em', background: 'rgba(0,0,0,0.7)', padding: '3px 8px',
                                        borderRadius: 3, backdropFilter: 'blur(8px)'
                                    }}>
                                        {t('Live Preview')}
                                    </div>
                                </div>
                            </div>

                            <button
                                className="btn btn-primary"
                                onClick={handleUpdateStyles}
                                disabled={styleUpdateLoading || !selectedFile}
                                style={{ width: '100%', padding: '12px', fontSize: '15px', fontWeight: 600 }}
                            >
                                <PaletteIcon size={16} style={{ marginRight: 8, verticalAlign: 'middle' }} />
                                {styleUpdateLoading ? t('Submitting Task...') : t('Save & Update Styles for Selected File')}
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
