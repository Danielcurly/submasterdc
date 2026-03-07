'use client';

import { useEffect, useState } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { getConfig, saveConfig, getAIProviders, testAIConnection, getOllamaModels, getAIContentTypes, getAIUsage } from '@/lib/api';
import { Cpu, Zap, Save, RefreshCw, CheckCircle2, XCircle, Mic, Loader2 } from 'lucide-react';

interface ContentTypeOption { value: string; label: string; description: string; }

export default function AIConfigPage() {
    const [config, setConfig] = useState<Record<string, any> | null>(null);
    const [providers, setProviders] = useState<Record<string, any>>({});
    const [selectedProvider, setSelectedProvider] = useState('');
    const [apiKey, setApiKey] = useState('');
    const [baseUrl, setBaseUrl] = useState('');
    const [modelName, setModelName] = useState('');
    const [ollamaModels, setOllamaModels] = useState<string[]>([]);
    const [contentTypes, setContentTypes] = useState<ContentTypeOption[]>([]);
    const [selectedContentType, setSelectedContentType] = useState('movie');
    const [whisperModel, setWhisperModel] = useState('base');
    const [whisperThreads, setWhisperThreads] = useState(4);
    const [sourceLang, setSourceLang] = useState('auto');
    const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
    const [testing, setTesting] = useState(false);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState('');
    const [maxDailyCalls, setMaxDailyCalls] = useState(0);
    const [usage, setUsage] = useState<{ used: number; limit: number } | null>(null);
    const { t } = useLanguage();

    const fetchUsage = async () => {
        try { setUsage(await getAIUsage()); }
        catch (e) { console.error('Failed to fetch usage', e); }
    };

    useEffect(() => {
        Promise.all([getConfig(), getAIProviders(), getAIContentTypes()]).then(([cfg, provs, cts]) => {
            setConfig(cfg); setProviders(provs); setContentTypes(cts);
            setConfig(cfg); setProviders(provs); setContentTypes(cts);
            const prov = cfg.current_provider || 'Ollama (Local)';
            setSelectedProvider(prov);
            setSelectedContentType(cfg.whisper?.content_type || 'movie');
            setWhisperModel(cfg.whisper?.model_size || 'base');
            setWhisperThreads(cfg.whisper?.cpu_threads || 4);
            setSourceLang(cfg.whisper?.source_language || 'auto');
            setMaxDailyCalls(cfg.translation?.max_daily_calls || 0);
            const pc = cfg.provider_configs?.[prov];
            if (pc) { setApiKey(pc.api_key || ''); setBaseUrl(pc.base_url || provs[prov]?.base_url || ''); setModelName(pc.model_name || provs[prov]?.model || ''); }
            else if (provs[prov]) { setApiKey(''); setBaseUrl(provs[prov].base_url || ''); setModelName(provs[prov].model || ''); }
        });
        fetchUsage();
    }, []);

    const handleProviderChange = (p: string) => {
        setSelectedProvider(p); setTestResult(null);
        const pc = config?.provider_configs?.[p];
        if (pc) { setApiKey(pc.api_key || ''); setBaseUrl(pc.base_url || providers[p]?.base_url || ''); setModelName(pc.model_name || providers[p]?.model || ''); }
        else if (providers[p]) { setApiKey(''); setBaseUrl(providers[p].base_url || ''); setModelName(providers[p].model || ''); }
    };

    const handleTest = async () => {
        setTesting(true); setTestResult(null);
        try { setTestResult(await testAIConnection({ api_key: apiKey, base_url: baseUrl, model: modelName })); }
        catch (e: unknown) { setTestResult({ success: false, message: e instanceof Error ? e.message : 'Error' }); }
        setTesting(false);
    };

    const handleSave = async () => {
        if (!config) return;
        setSaving(true);
        try {
            await saveConfig({
                ...config,
                current_provider: selectedProvider,
                provider_configs: { ...config.provider_configs, [selectedProvider]: { api_key: apiKey, base_url: baseUrl, model_name: modelName } },
                whisper: { ...config.whisper, model_size: whisperModel, cpu_threads: whisperThreads, source_language: sourceLang, content_type: selectedContentType },
                translation: { ...config.translation, max_daily_calls: maxDailyCalls }
            });
            setMessage(t('Configuration saved!'));
            fetchUsage();
            setTimeout(() => setMessage(''), 3000);
        } catch (e: unknown) { setMessage(`${t('Error')}: ${e instanceof Error ? e.message : 'Unknown'}`); }
        finally { setSaving(false); }
    };

    if (!config) return (
        <div className="page-header">
            <h1 className="page-title"><span className="page-title-icon"><Cpu size={20} /></span>{t('AI Configuration')}</h1>
            <div style={{ marginTop: 24 }}><div className="skeleton" style={{ height: 300, width: '100%' }} /></div>
        </div>
    );

    return (
        <>
            <div className="page-header">
                <h1 className="page-title">
                    <span className="page-title-icon"><Cpu size={20} /></span>
                    {t('AI Configuration')}
                </h1>
                <p className="page-subtitle">{t('Configure AI providers, models, and audio processing.')}</p>
            </div>

            {message && <div className="info-box animate-in" style={{ marginBottom: 24 }}>{message}</div>}

            {/* LLM Provider */}
            <div className="section">
                <div className="section-header">
                    <div className="section-title">
                        <Zap size={18} className="section-title-icon" />
                        <h2>{t('LLM Provider')}</h2>
                    </div>
                </div>

                <div className="card">
                    <div className="form-group">
                        <label className="form-label">{t('Provider')}</label>
                        <select className="form-select" value={selectedProvider} onChange={e => handleProviderChange(e.target.value)}>
                            {Object.keys(providers).map(p => <option key={p} value={p}>{p}</option>)}
                        </select>
                        {providers[selectedProvider]?.help && (
                            <p className="text-caption" style={{ marginTop: 6 }}>{t(providers[selectedProvider].help)}</p>
                        )}
                    </div>

                    <p className="text-caption mb-4" style={{ marginBottom: 16 }}>
                        {t('Fallback Tip')}
                    </p>

                    <div className="grid-cols-2">
                        <div className="form-group">
                            <label className="form-label">{t('API Key')}</label>
                            <input type="password" className="form-input" value={apiKey} onChange={e => setApiKey(e.target.value)} placeholder={t('sk-... (key1, key2)')} />
                        </div>
                        <div className="form-group">
                            <label className="form-label">{t('Base URL')}</label>
                            <input className="form-input" value={baseUrl} onChange={e => setBaseUrl(e.target.value)} placeholder={t('url1, url2')} />
                        </div>
                    </div>

                    <div className="form-group">
                        <label className="form-label">{t('Model')}</label>
                        <div style={{ display: 'flex', gap: 8 }}>
                            <input className="form-input" value={modelName} onChange={e => setModelName(e.target.value)} style={{ flex: 1 }} placeholder={t('model1, model2')} />
                            {selectedProvider.includes('Ollama') && (
                                <button className="btn btn-sm" onClick={async () => setOllamaModels(await getOllamaModels(baseUrl))}>
                                    <RefreshCw size={13} /> {t('Fetch')}
                                </button>
                            )}
                        </div>
                        {ollamaModels.length > 0 && (
                            <div style={{ marginTop: 8, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                                {ollamaModels.map(m => (
                                    <button key={m} className={`btn btn-sm ${modelName === m ? 'btn-primary' : ''}`} onClick={() => setModelName(m)}>{m}</button>
                                ))}
                            </div>
                        )}
                    </div>

                    <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginTop: 12 }}>
                        <button className="btn btn-primary" onClick={handleTest} disabled={testing}>
                            {testing ? <><Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> {t('Testing...')}</> : <><Zap size={14} /> {t('Test Connection')}</>}
                        </button>
                        {testResult && (
                            <span className={`chip ${testResult.success ? 'chip-green' : 'chip-red'}`} style={{ fontSize: 12 }}>
                                {testResult.success ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
                                {testResult.message}
                            </span>
                        )}
                    </div>
                </div>

                <div className="section-header" style={{ marginTop: 24 }}>
                    <div className="section-title">
                        <Save size={18} className="section-title-icon" />
                        <h2>{t('Usage Limits')}</h2>
                    </div>
                </div>
                <div className="card">
                    <div className="form-group">
                        <label className="form-label">{t('Daily AI Call Limit')}</label>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                            <input
                                type="number"
                                className="form-input"
                                style={{ width: 120 }}
                                value={maxDailyCalls}
                                onChange={e => setMaxDailyCalls(parseInt(e.target.value) || 0)}
                                min="0"
                            />
                            <div style={{ flex: 1 }}>
                                <p className="text-caption" style={{ margin: 0 }}>
                                    {t('0 = Unlimited. Hard cap on daily AI translation requests to avoid unexpected costs.')}
                                </p>
                                {usage && (
                                    <p className="text-caption" style={{ margin: '4px 0 0 0', fontWeight: 'bold', color: 'var(--primary-color)' }}>
                                        {t('Used')}: {usage.used} / {usage.limit === 0 ? t('Unlimited') : usage.limit} {t('Calls')}
                                    </p>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Whisper */}
            <div className="section">
                <div className="section-header">
                    <div className="section-title">
                        <Mic size={18} className="section-title-icon" />
                        <h2>{t('Whisper Audio Processing')}</h2>
                    </div>
                </div>

                <div className="card">
                    <div className="grid-cols-2">
                        <div className="form-group">
                            <label className="form-label">{t('Model Size')}</label>
                            <select className="form-select" value={whisperModel} onChange={e => setWhisperModel(e.target.value)}>
                                {['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3'].map(m => <option key={m} value={m}>{m}</option>)}
                            </select>
                        </div>
                        <div className="form-group">
                            <label className="form-label">{t('Source Language')}</label>
                            <input className="form-input" value={sourceLang} onChange={e => setSourceLang(e.target.value)} placeholder={t('auto')} />
                        </div>
                    </div>

                    <div className="grid-cols-2">
                        <div className="form-group">
                            <label className="form-label">{t('Content Type')}</label>
                            <select className="form-select" value={selectedContentType} onChange={e => setSelectedContentType(e.target.value)}>
                                {contentTypes.map(ct => <option key={ct.value} value={ct.value}>{t(ct.label)}</option>)}
                            </select>
                        </div>
                        <div className="form-group">
                            <label className="form-label">{t('CPU Threads')} {t('(N100: 4)')}</label>
                            <input type="number" className="form-input" value={whisperThreads} onChange={e => setWhisperThreads(parseInt(e.target.value) || 1)} min="1" max="64" />
                        </div>
                    </div>

                    {contentTypes.find(c => c.value === selectedContentType)?.description && (
                        <p className="text-caption mt-2">{t(contentTypes.find(c => c.value === selectedContentType)!.description)}</p>
                    )}
                </div>
            </div>

            <button className="btn btn-primary btn-block" onClick={handleSave} disabled={saving}>
                <Save size={15} /> {saving ? t('Saving...') : t('Save Configuration')}
            </button>
        </>
    );
}
