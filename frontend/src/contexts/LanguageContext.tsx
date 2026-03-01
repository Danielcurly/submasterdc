'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';

type Language = 'en' | 'zh';

interface Translations {
    [key: string]: string;
}

const translations: Record<Language, Translations> = {
    en: {
        'Dashboard': 'Dashboard',
        'Libraries': 'Libraries',
        'Translation': 'Translation Tasks',
        'Manual Generation': 'Manual Generation',
        'AI Configuration': 'AI Configuration',
        'Monitor your task queue and trigger library scans.': 'Monitor your task queue and trigger library scans.',
        'automatic': 'Automatic',
        'periodic': 'Periodic',
        'manual': 'Manual',
        'Added {n} new media files': 'Added {n} new media files',
        'No new media found': 'No new media found',
        'Library renamed to {name}': 'Library renamed to "{name}"',
        'Failed to rename library: {error}': 'Failed to rename library: {error}',
        'CPU Threads': 'CPU Threads',
        'Cancelled': 'Cancelled',
        'All': 'All',
        'Fallback Tip': 'Config tip: You can use comma-separated values (e.g., key1, key2 or model1, model2) to automatically fallback when rate limits are hit.',
        'Language Detection Offset (sec)': 'Language Detection Offset (sec)',
        'Seek into video to avoid intros/music for auto-detect. (e.g., 600 for 10m)': 'Seek into video to avoid intros/music for auto-detect. (e.g., 600 for 10m)',
    },
    zh: {
        'Dashboard': '仪表盘',
        'Libraries': '媒体库',
        'Translation': '翻译任务',
        'Manual Generation': '手动生成',
        'AI Configuration': 'AI配置',
        'Monitor your task queue and trigger library scans.': '监控您的任务队列并触发媒体库扫描。',
        'automatic': '自动 (监控)',
        'periodic': '定期',
        'manual': '手动',
        'Added {n} new media files': '新增 {n} 个媒体文件',
        'No new media found': '未发现新媒体',
        'Library renamed to {name}': '媒体库已重命名为 "{name}"',
        'Failed to rename library: {error}': '重命名媒体库失败: {error}',
        'Fallback Tip': '配置提示：您可以使用逗号分隔的值（例如 key1, key2）来设置备用配置。遇到速率限制时系统将自动切换。',

        // Libraries Page
        'Configure and manage your media library folders.': '配置并管理您的媒体库文件夹。',
        'New Library': '新增媒体库',
        'Configured Libraries': '已配置的媒体库',
        'total': '个',
        'No libraries configured yet': '暂未配置任何媒体库',
        'PATH VALID': '路径有效',
        'PATH NOT FOUND': '路径不存在',
        'Scan Mode': '扫描模式',
        'Manual': '手动',
        'Periodic': '定期',
        'Automatic (Watchdog)': '自动 (监控)',
        'Interval': '间隔',
        'Add New Library': '添加新媒体库',
        'Library Name': '媒体库名称',
        'e.g. My Movies': '例如：我的电影',
        'Directory Path': '目录路径',
        'Contents of': '内容：',
        'Loading...': '加载中...',
        'No subdirectories found': '未找到子目录',
        'Interval (D H M)': '间隔 (天 时 分)',
        'Interval (disabled)': '间隔 (已禁用)',
        'Cancel': '取消',
        'Create Library': '创建媒体库',

        // Translation Page
        'Translation Rules': '翻译规则',
        'Configure how subtitles are translated and output formats.': '配置字幕翻译和输出格式。',
        'Translation Workflow': '翻译工作流',
        'Enabled': '已启用',
        'Disabled': '已禁用',
        'Translation Tasks': '翻译任务',
        'tasks': '个任务',
        'task': '个任务',
        'No translation tasks configured. Add one to get started.': '暂未配置翻译任务。添加一个以开始。',
        'Target Lang': '目标语言',
        'Secondary Lang': '次要语言',
        'Suffix Code': '后缀代码',
        'Primary': '主要',
        'Secondary': '次要',
        'Add New Task': '添加新任务',
        'Batch Size (lines)': '批次大小 (行数)',
        'Subtitle Formats': '字幕格式',
        'SRT': 'SRT',
        'Universal': '通用',
        'Widest compatibility, plain text.': '最广泛的兼容性，纯文本。',
        'ASS': 'ASS',
        'Advanced': '高级',
        'Supports rich styles and position.': '支持丰富的样式和位置。',
        'Saving...': '保存中...',
        'Save Settings': '保存设置',
        'Add Translation Task': '添加翻译任务',
        'Target Language': '目标语言',
        'Create Bilingual Subtitles': '生成双语字幕',
        'Secondary Language': '次要语言',
        'Bilingual Filename Code': '双语文件名后缀',
        'Determines the language code suffix used in the final filename...': '确定最终文件名中使用的语言代码后缀 (例如 video.en.srt 和 video.es.srt)。',
        'Add Task': '添加任务',

        // Manual Generation Page
        'Bypass library settings and forcibly generate subtitles for a specific file.': '绕过媒体库设置，强制为特定文件生成字幕。',
        'Select Video File': '选择视频文件',
        'Directory is empty': '目录为空',
        'Selected': '已选',
        'Configuration & Execution': '配置与执行',
        'English': '英语',
        'Chinese': '中文',
        'Spanish': '西班牙语',
        'French': '法语',
        'German': '德语',
        'Japanese': '日语',
        'Italian': '意大利语',
        'Portuguese': '葡萄牙语',
        'Russian': '俄语',
        'Korean': '韩语',
        'Generate Bilingual Subtitles': '生成双语字幕',
        'Submitting Task...': '提交任务中...',
        'Force Generate Subtitles': '强制生成字幕',
        'Warning: This will skip metadata checks and overwrite existing external subtitles with the same name.': '警告：此操作将跳过元数据检查，并覆盖同名的现有外部字幕。',
        'Failed to submit task': '提交任务失败',
        'Task submitted to generate subtitles for': '已提交任务以生成字幕：',

        // AI Config Page
        'Configure AI providers, models, and audio processing.': '配置AI服务商、模型和音频处理。',
        'LLM Provider': 'LLM服务商',
        'Provider': '服务商',
        'API Key': 'API密钥',
        'Base URL': '基础URL',
        'Model': '模型',
        'Fetch': '获取',
        'Test Connection': '测试连接',
        'Testing...': '测试中...',
        'Whisper Audio Processing': 'Whisper音频处理',
        'Model Size': '模型大小',
        'Source Language': '源语言',
        'Content Type': '内容类型',
        'auto': '自动',
        'Save Configuration': '保存配置',
        'CPU Threads': 'CPU线程数',
        'Configuration saved!': '配置已保存！',
        'Error': '错误',
        'Language Detection Offset (sec)': '语言检测偏移 (秒)',
        'Seek into video to avoid intros/music for auto-detect. (e.g., 600 for 10m)': '跳过片头/音乐以提高自动检测准确性。 (例如: 600 表示 10分钟)',

        // Dashboard
        'Pending': '等待中',
        'Processing': '处理中',
        'Completed': '已完成',
        'Failed': '已失败',
        'Cancelled': '已取消',
        'Skipped': '已跳过',
        'No libraries configured': '暂未配置媒体库',
        'Go to Libraries to add one.': '前往媒体库页面添加一个。',
        'Scanning...': '扫描中...',
        'Analyze Now': '立即分析',
        'Processing Queue': '处理队列',
        'Refresh': '刷新',
        'Queue is empty': '队列为空',
        'Scan a library to add tasks.': '扫描媒体库以添加任务。',
        'Retry': '重试',
        'Clean List': '清理列表',
        'Hide Completed': '隐藏已完成',
        'Hide Failed': '隐藏已失败',
        'Hide Skipped': '隐藏已跳过',
        'All': '全部',
        'Show': '显示',
        'entries': '条记录',
        'Previous': '上一页',
        'Next': '下一页',
        'Cancel All': '取消全部',

        // Movie Content Type Labels
        'Movies & Serials': '电影和剧集',
        'Anime & Cartoons': '动漫和卡通',
        'Documentary': '纪录片',
        'Lecture & Tutorial': '讲座和教程',
        'Music Video / Auto': '音乐视频 / 自动'
    }
};

interface LanguageContextType {
    language: Language;
    setLanguage: (lang: Language) => void;
    t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextType>({
    language: 'en',
    setLanguage: () => { },
    t: (key: string) => key,
});

export function LanguageProvider({ children }: { children: React.ReactNode }) {
    const [language, setLanguageState] = useState<Language>('en');

    useEffect(() => {
        // Load preference from local storage on mount
        const saved = localStorage.getItem('ly-lang') as Language;
        if (saved && (saved === 'en' || saved === 'zh')) {
            setLanguageState(saved);
        }
    }, []);

    const setLanguage = (lang: Language) => {
        setLanguageState(lang);
        localStorage.setItem('ly-lang', lang);
    };

    const t = (key: string) => {
        return translations[language][key] || key;
    };

    return (
        <LanguageContext.Provider value={{ language, setLanguage, t }}>
            {children}
        </LanguageContext.Provider>
    );
}

export function useLanguage() {
    return useContext(LanguageContext);
}
