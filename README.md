# SubMasterDC
### Intelligent Subtitle Automation for NAS

License: [AGPL-3.0](LICENSE)

SubMasterDC is an automated tool for subtitle extraction and translation using Whisper and Large Language Models (LLM). It is specifically optimized for NAS devices (Synology, QNAP, Unraid) via Docker.

---

## Attribution and Note
This project is a fork based on the original work by [aexachao/nas-submaster](https://github.com/aexachao/nas-submaster).

SubMasterDC is a personal hobby project developed with AI assistance for private use. Distributed under the GNU Affero General Public License v3.0 (AGPL-3.0), as per the original project's requirements.

---

## UI Showcase
![SubMasterDC Interface Walkthrough](docs/images/clean_app_walkthrough.webp)
*A quick tour of the clean Dashboard, Library setup, and AI Configuration pages.*

---

## Key Features

### Intelligent Workflow
- **Multi-Point Language Detection**: Evaluates audio at multiple points (start, 5m, 10m) to confirm the true language and avoid detection errors caused by musical intros.
- **Embedded Subtitle Extraction**: Automatically detects and leverages existing internal subtitle tracks when available, speeding up the process and minimizing AI API usage.
- **Vote & Probe System**: Fragments of internal tracks (2-minute samples) are extracted and analyzed to verify languages before full extraction.

### AI Processing
- **LLM Translation**: Deep integration with Ollama (Local), DeepSeek, OpenAI, and Google Gemini (featuring automatic model rotation).
- **Faster-Whisper Transcription**: Local high-performance speech-to-text for videos without any usable embedded tracks.
- **Bilingual Styling (ASS)**: Ability to generate dual-language subtitles with professional styling (different colors/sizes for primary and secondary languages).

### Management & Automation
- **Advanced Library Monitoring**: selective scanning of NAS folders with three modes:
    - **Watchdog (Real-time)**: Immediate detection and processing when new files are added.
    - **Periodic**: Scheduled full scans for static libraries.
    - **Manual**: User-triggered scanning.
- **Centralized Dashboard**: Monitoring of tasks with filtering by status (Pending, Processing, Completed, Failed, Skipped).
- **Subtitle Signatures**: Embedded metadata in SRT and ASS files to identify SubMasterDC authorship without database dependency.
- **Inventory Counting**: Automatic counting of media files per library for easier catalog control.

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
      - /path/to/your/media:/media
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
Add your media folders in the **Libraries** tab. Choose the scan mode that best fits your workflow.
- Use **Automatic (Watchdog)** for folders managed by tools like Sonarr/Radarr.
- Use **Periodic** for large, static collections.

### Translation & API Limits
Define your API credentials and batch sizes in the **AI Configuration**. Smaller batches improve translation quality (reducing hallucinations) but use more API requests.
- **No API Mode**: If no AI provider is set, the app still extracts embedded subtitles, transcribes to original language, and handles existing .ass files.

---

## Credits
Based on the core of [aexachao/nas-submaster](https://github.com/aexachao/nas-submaster). Developed with AI assistance for personal hobby use.
