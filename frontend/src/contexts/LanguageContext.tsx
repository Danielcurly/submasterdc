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
        'Single File Ops': 'Single File Ops',
        'Subtitle Styling': 'Subtitle Styling',
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

        // Debug
        'Logs': 'Logs',
        'Log Level': 'Log Level',
        'Off': 'Off',
        'Normal': 'Normal',
        'Debug': 'Debug',
        'Lines to show': 'Lines to show',
        'Auto-scroll': 'Auto-scroll',
        'Clear Logs': 'Clear Logs',
        'Copy to Clipboard': 'Copy to Clipboard',
        'Logs cleared successfully.': 'Logs cleared successfully.',
        'Copied to clipboard!': 'Copied to clipboard!',
        'Debug Panel': 'Debug Panel',
        'Show': 'Show',
        'Search tasks...': 'Search tasks...',
        'Search': 'Search',
        'Configure how your generated subtitles look': 'Configure how your generated subtitles look',
        'Subtitle style saved': 'Subtitle style saved',
        'Failed to load subtitle style': 'Failed to load subtitle style',
        'Failed to save subtitle style': 'Failed to save subtitle style',
        'Target Format': 'Target Format',
        'Font Size': 'Font Size',
        'Smallest': 'Smallest',
        'Largest': 'Largest',
        'Colors': 'Colors',
        'Primary Color': 'Primary Color',
        'Secondary Color': 'Secondary Color',
        'Style Editor': 'Style Editor',
        'Update Styles': 'Update Styles',
        'Note': 'Note',
        'The preview approximate the final look. Final rendering depends on the font installed on your system or the player Used.': 'The preview approximate the final look. Final rendering depends on the font installed on your system or the player Used.',
        'Secondary colors and custom fonts are not supported by the SRT format': 'Secondary colors and custom fonts are not supported by the SRT format',
        'tasks found': 'tasks found',
        'External Subs': 'External Subs',
    },
    zh: {
        'Dashboard': '仪表盘',
        'Libraries': '媒体库',
        'Translation': '翻译任务',
        'Manual Generation': '手动生成',
        'Single File Ops': '单文件操作',
        'Subtitle Styling': '字幕样式',
        'AI Configuration': 'AI配置',
        'Monitor your task queue and trigger library scans.': '监控您的任务队列并触发媒体库扫描。',
        'automatic': '自动 (监控)',
        'periodic': '定期',
        'manual': '手动',
        'Added {n} new media files': '新增 {n} 个媒体文件',
        'No new media found': '未发现新媒体',
        'Library renamed to {name}': '媒体库已重命名为 "{name}"',
        'Failed to rename library: {error}': '重命名媒体库失败: {error}',
        'Library "{name}" added!': '媒体库 "{name}" 已添加！',
        'Library "{name}" deleted': '媒体库 "{name}" 已删除',
        'Failed to delete library: {error}': '删除媒体库失败: {error}',
        'Settings saved successfully!': '设置保存成功！',
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
        'External Subs': '外部字幕',
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
        'Auto Detect': '自动检测',
        'Simplified Chinese': '简体中文',
        'Traditional Chinese': '繁体中文',

        // Debug
        'Logs': '运行日志',
        'Log Level': '日志级别',
        'Off': '关闭',
        'Normal': '普通',
        'Debug': '调试',
        'Lines to show': '显示行数',
        'Auto-scroll': '自动滚动',
        'Clear Logs': '清除日志',
        'Copy to Clipboard': '复制到剪贴板',
        'Logs cleared successfully.': '日志已成功清除。',
        'Copied to clipboard!': '已复制到剪贴板！',
        'Debug Panel': '调试面板',
        'Show': '显示',
        'Search tasks...': '搜索任务...',
        'Search': '搜索',

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
        'Used': '已用',
        'Calls': '次调用',
        'Usage': '使用量',
        'Unlimited': '无限制',
        '(N100: 4)': '(N100 推荐: 4)',
        'sk-... (key1, key2)': 'sk-... (支持多个密钥，用逗号分隔)',
        'url1, url2': 'url1, url2 (支持多个URL)',
        'model1, model2': 'model1, model2 (支持多个模型)',
        'Configure how your generated subtitles look': '配置生成的字幕外观',
        'Subtitle style saved': '字幕样式已保存',
        'Failed to load subtitle style': '加载字幕样式失败',
        'Failed to save subtitle style': '保存字幕样式失败',
        'Target Format': '目标格式',
        'Font Size': '字体大小',
        'Smallest': '最小',
        'Largest': '最大',
        'Colors': '颜色',
        'Primary Color': '主颜色',
        'Secondary Color': '副颜色',
        'Style Editor': '样式编辑器',
        'Update Styles': '更新样式',
        'Note': '注意',
        'The preview approximate the final look. Final rendering depends on the font installed on your system or the player Used.': '预览仅供参考。最终渲染取决于您系统中安装的字体或使用的播放器。',
        'Secondary colors and custom fonts are not supported by the SRT format': 'SRT格式不支持副颜色和自定义字体',

        // Dashboard
        'Pending': '等待中',
        'Processing': '处理中',
        'Completed': '已完成',
        'Failed': '已失败',
        'Cancelled': '已取消',
        'Skipped': '已跳过',
        'Permission Error': '权限错误',
        'Quota Exhausted': '配额已耗尽',
        'BILINGUAL': '双语',
        'Selected': '已选择',
        'Click to rename': '点击重命名',
        'Delete library': '删除媒体库',
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
        'entries': '条记录',
        'Previous': '上一页',
        'Next': '下一页',
        'Cancel All': '取消全部',

        // AI Config Extra Translations
        'Usage Limits': '使用限制',
        'Daily AI Call Limit': '每日 AI 调用限制',
        '0 = Unlimited. Hard cap on daily AI translation requests to avoid unexpected costs.': '0 = 无限制。每日 AI 翻译请求的硬上限，以避免意外费用。',

        // LLM Provider Help Strings
        'No internet required, use local compute': '不需要互联网，使用本地计算',
        'High performance': '高性能',
        'Modern Google models (v2.5, v3) with automatic rotation': '现代 Google 模型 (v2.5, v3)，支持自动轮换',
        'Optimized for long text': '针对长文本优化',
        'Aliyun Official': '阿里云官方服务',
        'Zhipu Official': '智谱 AI 官方服务',
        'Stable and powerful': '稳定且强大',
        'Manual input': '手动输入配置',

        // Content Type Display Names (Matching backend display_names)
        '🎬 Movies/TV (Standard)': '🎬 电影/电视 (标准)',
        '📺 Documentaries/News': '📺 纪录片/新闻',
        '🎤 Variety/Talk Shows': '🎤 综艺/脱口秀',
        '🎨 Animation/Anime': '🎨 动画/动漫',
        '🎓 Lectures/Courses': '🎓 讲座/课程',
        '🎵 Music Videos/MVs': '🎵 音乐视频/MV',
        '⚙️ Custom': '⚙️ 自定义',

        // Content Type Descriptions
        'Standard configuration for movies and TV series with clear dialogue. High timeline accuracy.': '适用于对话清晰的电影和电视剧的标准配置。时间轴准确度高。',
        'Optimized for voiceover recognition, reducing background music interference. Suitable for documentaries, news, and interviews.': '针对旁白识别进行了优化，减少背景音乐干扰。适用于纪录片、新闻和访谈。',
        'High threshold to filter laughter, applause, and background noise. Suitable for variety shows, talk shows, and group interviews.': '高阈值以过滤笑声、掌声和背景噪音。适用于综艺节目、脱口秀和小组访谈。',
        'Adapted for fast speech delivery, reducing stuttering. Suitable for anime and cartoons.': '适配快速语速，减少卡顿。适用于动画和卡通。',
        'Focuses on complete sentence recognition, adding pause buffering. Suitable for educational videos, speeches, and training courses.': '专注于完整句子识别，增加停顿缓冲。适用于教育视频、演讲和培训课程。',
        'Extremely high threshold to extract only vocals, ignoring background music. Suitable for MVs, concerts, and singing shows.': '极高阈值以仅提取人声，忽略背景音乐。适用于 MV、演唱会和歌唱节目。',
        'Default configuration, VAD parameters can be manually adjusted for special needs.': '默认配置，可根据特殊需求手动调整 VAD 参数。',

        // Movie Content Type Labels (Short version)
        'Movies & Serials': '电影和剧集',
        'Anime & Cartoons': '动漫和卡通',
        'Documentary': '纪录片',
        'Lecture & Tutorial': '讲座和教程',
        'Music Video / Auto': '音乐视频 / 自动',
        'tasks found': '项任务',
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
