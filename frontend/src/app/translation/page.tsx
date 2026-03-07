'use client';

import { useEffect, useState } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { getConfig, saveConfig, getLanguages } from '@/lib/api';
import { Languages, Plus, X, Save } from 'lucide-react';

interface TranslationTask {
    target_language: string;
    bilingual_subtitles: boolean;
    secondary_language: string;
    bilingual_filename_code: string;
}

export default function TranslationPage() {
    const [config, setConfig] = useState<Record<string, any> | null>(null);
    const [tasks, setTasks] = useState<TranslationTask[]>([]);
    const [batchSize, setBatchSize] = useState(500);

    const [langMap, setLangMap] = useState<Record<string, string>>({});
    const [langOptions, setLangOptions] = useState<string[]>([]);
    const defaultTask: TranslationTask = {
        target_language: 'es',
        bilingual_subtitles: false,
        secondary_language: 'en',
        bilingual_filename_code: 'primary'
    };

    const [message, setMessage] = useState('');
    const [saving, setSaving] = useState(false);
    const [showAddMenu, setShowAddMenu] = useState(false);
    const [newTask, setNewTask] = useState<TranslationTask>(defaultTask);
    const { t } = useLanguage();

    useEffect(() => {
        Promise.all([getConfig(), getLanguages()]).then(([cfg, langs]) => {
            setConfig(cfg);
            setTasks(cfg.translation?.tasks ?? []);
            setBatchSize(cfg.translation?.max_lines_per_batch ?? 500);



            setLangMap(langs.iso_map);
            setLangOptions(langs.target_options);
        });
    }, []);

    const removeTask = (i: number) => setTasks(tasks.filter((_, idx) => idx !== i));

    const handleSave = async () => {
        if (!config) return;
        setSaving(true);
        try {
            const newConfig = {
                ...config,
                translation: { ...config.translation, enabled: true, tasks, max_lines_per_batch: batchSize },
            };
            await saveConfig(newConfig);
            setMessage(t('Settings saved successfully!'));
            setTimeout(() => setMessage(''), 3000);
        } catch (e: unknown) { setMessage(`${t('Error')}: ${e instanceof Error ? e.message : 'Unknown'}`); }
        finally { setSaving(false); }
    };

    if (!config) return (
        <div className="page-header">
            <h1 className="page-title"><span className="page-title-icon"><Languages size={20} /></span>{t('Translation')}</h1>
            <div style={{ marginTop: 24 }}><div className="skeleton" style={{ height: 200, width: '100%' }} /></div>
        </div>
    );

    return (
        <>
            <div className="page-header">
                <h1 className="page-title">
                    <span className="page-title-icon"><Languages size={20} /></span>
                    {t('Translation Rules')}
                </h1>
                <p className="page-subtitle">{t('Configure how subtitles are translated and output formats.')}</p>
            </div>

            {message && <div className="info-box animate-in" style={{ marginBottom: 24 }}>{message}</div>}

            {/* Tasks */}
            <div className="section">
                <div className="section-header">
                    <div className="section-title"><h3>{t('Translation Tasks')}</h3></div>
                    <span className="chip chip-gray">{tasks.length} {tasks.length !== 1 ? t('tasks') : t('task')}</span>
                </div>

                <div style={{ display: 'flex', gap: 16, overflowX: 'auto', paddingBottom: 16, minHeight: 180 }}>
                    {tasks.length === 0 ? (
                        <div className="card" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: 0.6, borderStyle: 'dashed' }}>
                            <p>{t('No translation tasks configured. Add one to get started.')}</p>
                        </div>
                    ) : tasks.map((task, i) => (
                        <div key={i} className="card" style={{ width: 300, flexShrink: 0, padding: 18, display: 'flex', flexDirection: 'column', gap: 14 }}>
                            {/* Header */}
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                                    <div className="card-icon purple" style={{ width: 32, height: 32, padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                                        <Languages size={16} />
                                    </div>
                                    <div style={{ minWidth: 0 }}>
                                        <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: 'var(--text-bright)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                            {t(langMap[task.target_language] || task.target_language)}
                                        </h3>
                                        {task.bilingual_subtitles && (
                                            <span className="chip chip-green" style={{ marginTop: 4, display: 'inline-block', fontSize: 10, padding: '2px 6px', fontWeight: 600 }}>
                                                {t('BILINGUAL')} (+{t(langMap[task.secondary_language] || task.secondary_language)})
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <button className="btn btn-danger btn-sm btn-icon" onClick={() => removeTask(i)} style={{ padding: 6, opacity: 0.6, margin: '-6px -6px 0 0' }}>
                                    <X size={14} />
                                </button>
                            </div>

                            {/* Details */}
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 'auto', fontSize: 13, color: 'var(--text-muted)' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                    <span>{t('Target Lang')}:</span>
                                    <strong style={{ color: 'var(--text)' }}>{t(langMap[task.target_language] || task.target_language)} ({task.target_language})</strong>
                                </div>
                                {task.bilingual_subtitles && (
                                    <>
                                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                            <span>{t('Secondary Lang')}:</span>
                                            <strong style={{ color: 'var(--text)' }}>{t(langMap[task.secondary_language] || task.secondary_language)} ({task.secondary_language})</strong>
                                        </div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                            <span>{t('Suffix Code')}:</span>
                                            <strong style={{ color: 'var(--text)' }}>{task.bilingual_filename_code === 'secondary' ? `${t('Secondary')} (${task.secondary_language})` : `${t('Primary')} (${task.target_language})`}</strong>
                                        </div>
                                    </>
                                )}
                            </div>
                        </div>
                    ))}

                    {/* Add Button Card */}
                    <div
                        className="card"
                        onClick={() => { setNewTask(defaultTask); setShowAddMenu(true); }}
                        style={{ width: 220, flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, cursor: 'pointer', borderStyle: 'dashed', backgroundColor: 'transparent', transition: 'all 0.2s ease' }}
                        onMouseEnter={e => e.currentTarget.style.backgroundColor = 'var(--bg-hover)'}
                        onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
                    >
                        <div style={{ width: 44, height: 44, borderRadius: '50%', backgroundColor: 'var(--bg-darker)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                            <Plus size={20} />
                        </div>
                        <span style={{ fontWeight: 600, color: 'var(--text-muted)' }}>{t('Add New Task')}</span>
                    </div>
                </div>
            </div>

            {/* Batch Size */}
            <div className="form-group" style={{ maxWidth: 300, marginTop: 24 }}>
                <label className="form-label">{t('Batch Size (lines)')}</label>
                <input type="number" className="form-input" value={batchSize} min={50} max={5000} step={50} onChange={e => setBatchSize(Number(e.target.value))} />
            </div>



            <button className="btn btn-primary btn-block" onClick={handleSave} disabled={saving}>
                <Save size={15} /> {saving ? t('Saving...') : t('Save Settings')}
            </button>

            {/* Modal Popup for Adding Translation Task */}
            {showAddMenu && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    background: 'rgba(0, 0, 0, 0.75)', backdropFilter: 'blur(8px)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    zIndex: 9999, padding: 20
                }} onClick={() => setShowAddMenu(false)}>

                    <div className="card animate-in" style={{
                        width: '100%', maxWidth: 550, maxHeight: '90vh', overflowY: 'auto',
                        padding: 32, position: 'relative',
                        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
                        border: '1px solid var(--border-medium)',
                        backgroundColor: 'var(--bg-secondary)'
                    }} onClick={e => e.stopPropagation()}>

                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                <div className="card-icon purple" style={{ width: 40, height: 40, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <Plus size={20} />
                                </div>
                                <h2 style={{ margin: 0, fontSize: '1.5rem' }}>{t('Add Translation Task')}</h2>
                            </div>
                            <button className="btn btn-icon btn-ghost" onClick={() => setShowAddMenu(false)} style={{ padding: 8 }}>
                                <X size={20} />
                            </button>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                            <div className="form-group">
                                <label className="form-label">{t('Target Language')}</label>
                                <select
                                    className="form-select"
                                    value={newTask.target_language}
                                    onChange={e => setNewTask({ ...newTask, target_language: e.target.value })}
                                >
                                    {langOptions.map(c => <option key={c} value={c}>{t(langMap[c] || c)}</option>)}
                                </select>
                            </div>

                            <div className="toggle-wrapper" style={{ margin: '8px 0' }}>
                                <button className={`toggle ${newTask.bilingual_subtitles ? 'active' : ''}`} onClick={() => setNewTask({ ...newTask, bilingual_subtitles: !newTask.bilingual_subtitles })} />
                                <span style={{ fontSize: 13, fontWeight: 500 }}>{t('Create Bilingual Subtitles')}</span>
                            </div>

                            {newTask.bilingual_subtitles && (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '16px', background: 'var(--bg-darker)', borderRadius: 8, border: '1px solid var(--border)' }}>
                                    <div className="form-group" style={{ marginBottom: 0 }}>
                                        <label className="form-label">{t('Secondary Language')}</label>
                                        <select
                                            className="form-select"
                                            value={newTask.secondary_language}
                                            onChange={e => setNewTask({ ...newTask, secondary_language: e.target.value })}
                                        >
                                            {langOptions.map(c => <option key={c} value={c}>{t(langMap[c] || c)}</option>)}
                                        </select>
                                    </div>
                                    <div className="form-group" style={{ marginBottom: 0 }}>
                                        <label className="form-label">{t('Bilingual Filename Code')}</label>
                                        <select
                                            className="form-select"
                                            value={newTask.bilingual_filename_code || 'primary'}
                                            onChange={e => setNewTask({ ...newTask, bilingual_filename_code: e.target.value })}
                                        >
                                            <option value="primary">{t('Primary')} ({newTask.target_language})</option>
                                            <option value="secondary">{t('Secondary')} ({newTask.secondary_language})</option>
                                        </select>
                                        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6, marginBottom: 0 }}>
                                            {t('Determines the language code suffix used in the final filename...')}
                                        </p>
                                    </div>
                                </div>
                            )}
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 32 }}>
                            <button className="btn btn-secondary" onClick={() => setShowAddMenu(false)}>{t('Cancel')}</button>
                            <button className="btn btn-primary" onClick={() => {
                                setTasks([...tasks, newTask]);
                                setShowAddMenu(false);
                            }}>{t('Add Task')}</button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
