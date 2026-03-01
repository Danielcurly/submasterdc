# SubMasterDC
### Intelligent Subtitle Automation for NAS

License: [AGPL-3.0](LICENSE)

SubMasterDC is an automated tool for subtitle extraction and translation using Whisper and Large Language Models (LLM). It is specifically optimized for NAS devices (Synology, QNAP, Unraid) via Docker.

---

## Attribution and Note
This project is a fork based on the original work by [aexachao/nas-submaster](https://github.com/aexachao/nas-submaster).

SubMasterDC is a personal hobby project developed with AI assistance for private use. It is not under active development, except for critical maintenance and bug fixes.

Distributed under the GNU Affero General Public License v3.0 (AGPL-3.0), as per the original project's requirements.

---

## UI Showcase
![SubMasterDC Interface Walkthrough](docs/images/clean_app_walkthrough.webp)
*A quick tour of the clean Dashboard, Library setup, and AI Configuration pages.*

---

## Key Features
- **Smart Language Detection**: Evaluates audio at multiple points (start, 5m, 10m) to confirm the language and avoid detection errors caused by musical intros.
- **Embedded Subtitle Extraction**: Automatically detects and leverages existing internal subtitle tracks when available, speeding up the process and minimizing AI API usage.
- **LLM Translation**: Deep integration with Ollama (Local), DeepSeek, OpenAI, and Gemini.
- **Library Management**: Selective scanning of NAS folders with support for automatic file monitoring (Watchdog).
- **Processing Queue**: Dashboard for monitoring tasks with filtering by status.
- **Manual Generation**: Ability to trigger subtitle processing for specific files independently of library rules.
- **Bilingual Support**: Optional generation of dual-language subtitles (.srt or .ass).

---

## Deployment Guide (Docker)

### 1. Structure
Create the following structure on your NAS:
```text
/volume1/docker/submasterdc/
├── data/           # Config and database
├── models/         # Whisper models
└── docker-compose.yml
```

### 2. Configuration
Sample `docker-compose.yml`:

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
      - /your/media/path:/media
    environment:
      - PUID=1026    # NAS User ID
      - PGID=100     # NAS Group ID
      - TZ=Europe/Madrid
```

### 3. Execution
Run from your terminal:
```bash
docker-compose up -d
```

---

## Usage Guide

### Initial Setup
1. Access the web interface at `http://[NAS-IP]:8000`.
2. Go to **AI Configuration** to set up your LLM provider and Whisper model size.
3. For devices without a dedicated GPU, the `base` model is recommended for performance.

### Library Setup
Add your media folders in the **Libraries** tab. You have two scanning modes available:
- **Automatic Mode**: Uses file system monitoring (Watchdog) to detect the exact moment a new file is added to the folder, immediately placing it in the processing queue. Ideal for libraries managed by Sonarr/Radarr.
- **Periodic Mode**: Scans the entire folder at a specified interval (e.g. every 24 hours) to find missing subtitles. Good for large, static libraries.
- **Manual Mode**: Disables automatic background processing. You must click the scan button directly from your Dashboard to detect new files and add them to the queue.

### Translation & API Limits
In the **AI Configuration** page, you can define your API credentials. You can set the maximum characters per batch. Lower batches are safer to avoid hallucinations, but will cost more API requests.
> **Note on API Usage**: If you do not configure an AI translation provider (or if it is invalid), the application will still function, but with limited features:
> 1. It will generate bilingual subtitles if the video file already contains embedded subtitle tracks for *both* of the selected languages.
> 2. It will transcribe the audio to text in its *original language*, generating a subtitle file in that language (since no translation can be performed).
> 3. It will skip generating target language files if translation is required but unavailable.

### Subtitle Logic
1. **Scanning**: Identifies video files missing external subtitles.
2. **Extraction**: Attempts to extract existing internal subtitle tracks to use as a primary source, saving time and resources.
3. **Voting System**: If no internal tracks are available, it samples three different audio points to ensure accurate language detection.
4. **Transcription**: Converts speech to text using Faster-Whisper (when no internal source is found).
5. **Translation**: Processes the source text through the selected LLM for natural-sounding results.

---

## Credits
Based on the core of [aexachao/nas-submaster](https://github.com/aexachao/nas-submaster). Developed with AI assistance for personal hobby use.
