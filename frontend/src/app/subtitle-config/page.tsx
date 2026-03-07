'use client';

import { useState, useEffect, useRef } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { getConfig, saveConfig, getSubtitleStyle, updateSubtitleStyle } from '@/lib/api';
import { Save, RefreshCcw, Palette as PaletteIcon, FileText } from 'lucide-react';
import { toast } from 'react-hot-toast';

// Helper to convert ASS color (&H00BBGGRR) to Hex (#RRGGBB)
const assToHex = (ass: string) => {
    if (!ass || !ass.startsWith('&H')) return '#ffffff';
    const bgr = ass.substring(4, 10);
    return `#${bgr.substring(4, 6)}${bgr.substring(2, 4)}${bgr.substring(0, 2)}`;
};

// Helper to convert Hex (#RRGGBB) to ASS color (&H00BBGGRR)
const hexToAss = (hex: string) => {
    return `&H00${hex.substring(5, 7)}${hex.substring(3, 5)}${hex.substring(1, 3)}`;
};

// ASS PlayRes 288p to match backend converter
const PLAY_RES_Y = 288;

// Font sizes matching the converter logic (PlayRes 384x288)
const FONT_SCALE: Record<number, number> = {
    1: 10, 2: 14, 3: 18, 4: 22, 5: 28, 6: 34, 7: 40
};

const SIZE_LABELS: Record<number, string> = {
    1: 'XS', 2: 'S', 3: 'M', 4: 'L', 5: 'XL', 6: '2XL', 7: '3XL'
};

export default function SubtitleConfigPage() {
    const { t } = useLanguage();
    const [style, setStyle] = useState({
        font_size_step: 4,
        primary_color: '&H00DFDFDF',
        secondary_color: '&H0000FFFF',
        target_format: 'ass'
    });
    const [formats, setFormats] = useState<string[]>(['ass']);
    const [config, setConfig] = useState<Record<string, any> | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    // We use a container width ref to calculate proportions
    const previewContainerRef = useRef<HTMLDivElement>(null);
    const [containerWidth, setContainerWidth] = useState(0);

    useEffect(() => {
        Promise.all([getSubtitleStyle(), getConfig()]).then(([styleData, cfg]) => {
            setStyle(styleData);
            setConfig(cfg);
            const savedFormats = cfg.export?.formats ?? ['ass'];
            setFormats(savedFormats.length > 0 ? [savedFormats[0]] : ['ass']);
        }).catch((error) => {
            console.error('Failed to load settings:', error);
            toast.error(t('Failed to load subtitle settings'));
        }).finally(() => setLoading(false));
    }, []);

    // Monitor container width to update live preview scaling
    useEffect(() => {
        if (!previewContainerRef.current) return;

        const updateWidth = () => {
            if (previewContainerRef.current) {
                setContainerWidth(previewContainerRef.current.offsetWidth);
            }
        };

        const resizeObserver = new ResizeObserver(updateWidth);
        resizeObserver.observe(previewContainerRef.current);
        updateWidth(); // Initial measure

        return () => resizeObserver.disconnect();
    }, [loading]);

    const handleSave = async () => {
        setSaving(true);
        try {
            await updateSubtitleStyle(style);
            if (config) {
                const newConfig = { ...config, export: { ...config.export, formats }, subtitle_style: style };
                await saveConfig(newConfig);
            }
            toast.success(t('Subtitle settings saved'));
        } catch (error) {
            toast.error(t('Failed to save subtitle settings'));
        } finally {
            setSaving(false);
        }
    };

    const handleReset = () => {
        setStyle({
            font_size_step: 4,
            primary_color: '&H00DFDFDF',
            secondary_color: '&H0000FFFF',
            target_format: 'ass'
        });
        setFormats(['ass']);
        toast.success(t('Settings reset to default'));
    };

    if (loading) return <div className="p-8 text-center">{t('Loading...')}</div>;

    const primaryFontSize = FONT_SCALE[style.font_size_step] || 82;
    const secondaryFontSize = Math.floor(primaryFontSize * 0.5);
    const isASS = formats[0] === 'ass';

    // Proportional scaling for the preview:
    // Subtitles in ASS are relative to PlayResY. 
    // Our preview box is 16:9, so height = width * 0.5625.
    const boxHeight = containerWidth * 0.5625;
    const scaledPrimary = boxHeight > 0 ? (primaryFontSize / PLAY_RES_Y) * boxHeight : 0;
    const scaledSecondary = boxHeight > 0 ? (secondaryFontSize / PLAY_RES_Y) * boxHeight : 0;

    const sliderFill = ((style.font_size_step - 1) / 6) * 100;

    return (
        <>
            <div className="page-header">
                <h1 className="page-title">
                    <span className="page-title-icon"><PaletteIcon size={20} /></span>
                    {t('Subtitle Settings')}
                </h1>
                <p className="page-subtitle">{t('Configure output format and visual styling for generated subtitles.')}</p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                {/* Output Format Section */}
                <div className="section">
                    <div className="section-header">
                        <div className="section-title">
                            <FileText size={18} className="section-title-icon" />
                            <h2>{t('Output Format')}</h2>
                        </div>
                    </div>

                    <div style={{ display: 'flex', gap: 16 }}>
                        {[
                            { id: 'ass', label: 'ASS', desc: t('Rich styles, colors and bilingual layout support.') },
                            { id: 'srt', label: 'SRT', desc: t('Universal compatibility, plain text only.') },
                        ].map(f => {
                            const isChecked = formats.includes(f.id);
                            return (
                                <label key={f.id} className="card" style={{
                                    flex: 1, cursor: 'pointer', display: 'flex', gap: 12, alignItems: 'center',
                                    borderColor: isChecked ? 'var(--accent-primary)' : undefined,
                                    background: isChecked ? 'var(--bg-hover)' : undefined,
                                    transition: 'all 0.2s ease'
                                }}>
                                    <input
                                        type="radio" name="subtitle_format" checked={isChecked}
                                        onChange={() => setFormats([f.id])}
                                        style={{ accentColor: 'var(--accent-primary)', width: 18, height: 18 }}
                                    />
                                    <div style={{ flex: 1 }}>
                                        <div style={{ fontWeight: 600, color: isChecked ? 'var(--text-bright)' : 'var(--text-primary)' }}>{f.label}</div>
                                        <p className="text-muted" style={{ fontSize: 12, margin: 0 }}>{f.desc}</p>
                                    </div>
                                </label>
                            );
                        })}
                    </div>
                </div>

                {/* Visual Style Section */}
                <div className="section" style={{ opacity: isASS ? 1 : 0.4, pointerEvents: isASS ? 'auto' : 'none', transition: 'opacity 0.3s ease' }}>
                    <div className="section-header">
                        <div className="section-title">
                            <PaletteIcon size={18} className="section-title-icon" />
                            <h2>{t('Visual Style')}</h2>
                        </div>
                        {!isASS && <span className="chip chip-gray">{t('ASS format required')}</span>}
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: 24 }}>
                        {/* Left Column Controls */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                            {/* Font Size Card */}
                            <div className="card" style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
                                <label style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-bright)', marginBottom: 4, display: 'block' }}>
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
                                                background: style.font_size_step === s ? 'var(--accent-primary)' : 'var(--bg-secondary)',
                                                color: style.font_size_step === s ? '#fff' : 'var(--text-muted)',
                                            }}
                                        >
                                            {SIZE_LABELS[s]}
                                        </button>
                                    ))}
                                </div>

                                <div style={{
                                    padding: '0 7.14%', // Align slider extremes with button centers: (100/7)/2 = 7.14%
                                    position: 'relative',
                                    marginTop: 4
                                }}>
                                    <input
                                        type="range"
                                        min={1} max={7} step={1}
                                        value={style.font_size_step}
                                        onChange={(e) => setStyle({ ...style, font_size_step: parseInt(e.target.value) })}
                                        style={{
                                            width: '100%', height: 6,
                                            background: `linear-gradient(to right, var(--accent-primary) ${sliderFill}%, var(--bg-secondary) ${sliderFill}%)`,
                                            borderRadius: 3,
                                            display: 'block'
                                        }}
                                    />
                                </div>
                            </div>

                            {/* Colors Card */}
                            <div className="card" style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
                                <label style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-bright)', marginBottom: 4, display: 'block' }}>
                                    {t('Colors')}
                                </label>

                                <div style={{ display: 'flex', gap: 12 }}>
                                    <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: 10, border: '1px solid var(--border)' }}>
                                        <input
                                            type="color"
                                            value={assToHex(style.primary_color)}
                                            onChange={(e) => setStyle({ ...style, primary_color: hexToAss(e.target.value) })}
                                            style={{ width: 34, height: 34, borderRadius: 6, border: 'none', cursor: 'pointer', background: 'transparent', padding: 0 }}
                                        />
                                        <div>
                                            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-bright)' }}>{t('Primary')}</div>
                                            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{t('Main Text')}</div>
                                        </div>
                                    </div>

                                    <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: 10, border: '1px solid var(--border)' }}>
                                        <input
                                            type="color"
                                            value={assToHex(style.secondary_color)}
                                            onChange={(e) => setStyle({ ...style, secondary_color: hexToAss(e.target.value) })}
                                            style={{ width: 34, height: 34, borderRadius: 6, border: 'none', cursor: 'pointer', background: 'transparent', padding: 0 }}
                                        />
                                        <div>
                                            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-bright)' }}>{t('Secondary')}</div>
                                            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{t('Translation')}</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Right Column - Live Preview */}
                        <div ref={previewContainerRef} className="card" style={{ padding: 0, overflow: 'hidden', position: 'relative', display: 'flex', flexDirection: 'column' }}>
                            <div style={{
                                position: 'absolute', top: 12, left: 16, fontSize: 10,
                                fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase',
                                letterSpacing: '0.12em', background: 'rgba(0,0,0,0.7)', padding: '4px 10px',
                                borderRadius: 4, zIndex: 10, backdropFilter: 'blur(8px)'
                            }}>
                                {t('Live Preview')}
                            </div>

                            <div style={{
                                position: 'relative', width: '100%', paddingBottom: '56.25%', /* 16:9 */
                                background: '#000', overflow: 'hidden'
                            }}>
                                {/* Fake video backdrop */}
                                <div style={{
                                    position: 'absolute', inset: 0,
                                    background: 'linear-gradient(135deg, #151515 0%, #080808 100%)',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                                }}>
                                    <div style={{ opacity: 0.05 }}>
                                        <PaletteIcon size={80} color="white" />
                                    </div>
                                </div>

                                {/* Actual Subtitles Layer */}
                                <div style={{
                                    position: 'absolute', inset: 0,
                                    display: 'flex', flexDirection: 'column', justifyContent: 'flex-end',
                                    alignItems: 'center', paddingBottom: '8%', pointerEvents: 'none'
                                }}>
                                    <div style={{
                                        color: assToHex(style.primary_color),
                                        fontSize: scaledPrimary ? `${scaledPrimary}px` : '16px',
                                        fontFamily: 'Microsoft YaHei, sans-serif',
                                        fontWeight: 'bold',
                                        textAlign: 'center',
                                        lineHeight: 1.15,
                                        textShadow: '2px 2px 1px #000, -1px -1px 0px #000, 1px -1px 0px #000, -1px 1px 0px #000',
                                        maxWidth: '92%',
                                        transition: 'all 0.1s ease-out'
                                    }}>
                                        你好，这是预览字幕。
                                    </div>
                                    <div style={{
                                        color: assToHex(style.secondary_color),
                                        fontSize: scaledSecondary ? `${scaledSecondary}px` : '10px',
                                        fontFamily: 'Microsoft YaHei, sans-serif',
                                        textAlign: 'center',
                                        lineHeight: 1.15,
                                        marginTop: '0.8%',
                                        textShadow: '1px 1px 1px #000, -1px -1px 0px #000, 1px -1px 0px #000, -1px 1px 0px #000',
                                        maxWidth: '92%',
                                        transition: 'all 0.1s ease-out'
                                    }}>
                                        Hello, this is a bilingual subtitle preview.
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Actions */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
                    <button className="btn btn-secondary" onClick={handleReset} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <RefreshCcw size={15} />
                        {t('Reset')}
                    </button>
                    <button className="btn btn-primary" onClick={handleSave} disabled={saving} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Save size={15} />
                        {saving ? t('Saving...') : t('Save Settings')}
                    </button>
                </div>
            </div>
        </>
    );
}
