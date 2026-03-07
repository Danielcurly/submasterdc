# SubMasterDC
### NAS 智能字幕管家

许可协议: [AGPL-3.0](LICENSE)

SubMasterDC 是一款基于 Whisper 和大型语言模型 (LLM) 的全自动视频字幕提取与翻译工具，专为 NAS 设备（Synology、QNAP、Unraid）通过 Docker 部署而优化设计。

---

## 声明与归属
本项目是一个基于 [aexachao/nas-submaster](https://github.com/aexachao/nas-submaster) 原创工作的分支 (Fork)。

SubMasterDC 是在人工智能辅助下开发的个人业余项目。根据原项目要求，本项目遵循 GNU Affero General Public License v3.0 (AGPL-3.0) 协议开源。

---

## 界面展示 (UI Showcase)
![SubMasterDC 界面预览](docs/images/clean_app_walkthrough.webp)
*干净状态下的控制面板、媒体库设置和 AI 配置页面导览。*

---

## 核心特性

### 智能工作流
- **多点语言检测**：在视频的多个时间点（起始、5分钟、10分钟）评估音频，以确认真实语言，避免因音乐片头导致识别错误。
- **内嵌字幕提取**：自动检测并优先提取视频已有的内嵌字幕轨，显著加快处理速度并减少 AI API 调用消耗。
- **投票与采样系统**：提取内嵌轨道的片段（2分钟采样）进行分析，在全量提取前核实语言。

### AI 处理能力
- **大语言模型翻译**：深度集成 Ollama (本地部署)、DeepSeek、OpenAI 和 Google Gemini（支持多模型自动轮换）。
- **Faster-Whisper 转录**：针对无内嵌字幕的视频，提供本地高性能语音转文字服务。
- **双语样式支持 (ASS)**：支持生成双语字幕，并可为第一和第二语言设置不同的专业样式（颜色、大小）。

### 管理与自动化
- **高级媒体库监控**：支持三种媒体库扫描模式：
    - **实时监控 (Watchdog)**：新文件添加瞬间即刻自动触发处理。
    - **周期扫描**：针对静态媒体库的定时全盘扫描。
    - **手动扫描**：用户自主触发检测。
- **现代化控制面板**：全方位任务监控，支持按状态（等待中、处理中、已完成、失败、已跳过）过滤。
- **字幕数字签名**：在生成的 SRT 和 ASS 文件中嵌入元数据，无需数据库即可识别 SubMasterDC 创作身份。
- **媒体库存统计**：自动统计每座媒体库的视频文件总数，方便管理。

---

## 部署指南 (Docker)

### 1. 文件结构
在您的 NAS 上创建以下结构：
```text
/volume1/docker/submasterdc/
├── data/           # 配置与数据库
├── models/         # Whisper 模型
└── docker-compose.yml
```

### 2. 配置文件
建议的 `docker-compose.yml` 示例配置：

```yaml
version: '3.8'

services:
  submasterdc:
    image: ghcr.io/danielcurly/submasterdc:latest
    container_name: submasterdc
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./models:/app/data/models
      - /您的/媒体/路径:/media
    environment:
      - PUID=1026    # NAS 用户 ID
      - PGID=100     # NAS 用户组 ID
      - TZ=Asia/Shanghai
```

### 3. 运行服务
在终端执行：
```bash
docker-compose up -d
```

---

## 快速使用指南

### 初始化设置
1. 在浏览器访问 `http://[NAS-IP]:8000`。
2. 进入 **AI Configuration** (AI 配置) 页面，设置您的 LLM 服务商和 Whisper 模型大小。
3. 对于没有独立显卡的设备，建议使用 `base` 模型以获得最佳性能。

### 媒体库设置
在 **Libraries** (媒体库) 选项卡中添加文件夹，并选择最适合您工作流的模式。
- Sonarr/Radarr 管理的文件夹建议使用 **自动监控 (Watchdog)**。
- 长期不动的静态收藏建议使用 **周期扫描**。

### 翻译与 API 限制
配置 API 凭证和批次大小。较小的批次能显著提升翻译质量（减少大模型幻觉），但会增加 API 请求频率。
- **无 API 模式**：未配置 AI 时，程序仍保留内嵌字幕提取、原始语言转录及现有 ASS 文件的样式处理功能。

---

## 鸣谢
核心代码基于 [aexachao/nas-submaster](https://github.com/aexachao/nas-submaster)。借助 AI 辅助开发的个人业余项目。
