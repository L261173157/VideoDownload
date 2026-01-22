# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based desktop video downloader application using Tkinter for the GUI and yt-dlp as the core download engine. It supports 1000+ video websites including YouTube, Bilibili, TikTok, Twitter, and more.

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Run the GUI application (includes automatic M3U8 fallback)
python main.py
```

## Architecture

### Entry Point
- [main.py](main.py) - Creates the Tkinter root window and initializes the MainWindow class

### Module Structure

**gui/** - Graphical User Interface
- [main_window.py](gui/main_window.py) - MainWindow class that handles all UI interactions. Uses threading for non-blocking URL parsing and downloads. The log_message() method handles color-coded logging display.

**downloader/** - Download Core
- [video_downloader.py](downloader/video_downloader.py) - VideoDownloader class wraps yt-dlp. Key methods:
  - `get_video_info(url)` - Extracts video metadata without downloading
  - `download_video(url, output_path, quality)` - Downloads video with progress hooks
  - `_get_format_string(quality)` - Maps quality options to yt-dlp format strings
- [m3u8_downloader.py](downloader/m3u8_downloader.py) - M3U8Downloader class handles M3U8 video streams. Key methods:
  - `parse_m3u8_from_url(page_url, video_id)` - Parses M3U8 info from a page URL with optional video ID
  - `parse_m3u8_direct(m3u8_url)` - Parses M3U8 file directly from URL
  - `download_m3u8_video(m3u8_info, output_path, merge)` - Downloads M3U8 video and merges TS segments
  - `get_video_ids_from_page(page_url)` - Extracts all video IDs from a page
  - `_merge_ts_files(temp_folder, output_file, ts_list)` - Merges TS segments into a single file
  - `_convert_to_mp4(ts_file)` - Converts TS to MP4 using ffmpeg (if available)
- [progress_handler.py](downloader/progress_handler.py) - ProgressHandler class formats download progress (bytes, speed, ETA) and invokes callbacks to update the GUI

**utils/** - Utilities
- [url_validator.py](utils/url_validator.py) - URLValidator validates URL format and normalizes URLs (adds https:// prefix if missing)
- [logger.py](utils/logger.py) - File-based logging to `logs/` directory with daily rotating logs

### Threading Model
URL parsing and downloads run in daemon threads to avoid blocking the UI. GUI updates are scheduled using `root.after(0, callback)` to ensure thread-safe UI modifications.

### Quality Options
The downloader supports these quality settings:
- `best`: bestvideo+bestaudio/best (requires ffmpeg for merging)
- `best-mp4`: bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best
- `best-audio`: bestaudio/best

### Progress Callback Flow
1. yt-dlp progress hook → ProgressHandler.progress_hook()
2. ProgressHandler formats data and invokes callback
3. MainWindow.update_download_progress() updates GUI via root.after()

## M3U8 Video Support

The application includes a dedicated M3U8 downloader for handling HLS (HTTP Live Streaming) video streams. This is particularly useful for sites that serve video content in M3U8 format with TS (Transport Stream) segments.

### M3U8 Downloader Features

- **Page URL Parsing**: Extract video IDs from web pages automatically using BeautifulSoup
- **Direct M3U8 Parsing**: Parse M3U8 files directly from URLs
- **Batch Download**: Download multiple videos from a single page
- **Auto-Merge**: Automatically merge TS segments into MP4 files
- **FFmpeg Integration**: Optional video conversion using ffmpeg if available
- **Retry Logic**: Built-in retry mechanism for failed downloads
- **Progress Tracking**: Real-time download progress reporting

### Usage Examples

**Python API:**
```python
from downloader.m3u8_downloader import M3U8Downloader

downloader = M3U8Downloader()

# Parse from page URL with video ID
m3u8_info = downloader.parse_m3u8_from_url(page_url, video_id="879508")

# Or parse M3U8 file directly
m3u8_info = downloader.parse_m3u8_direct("https://example.com/video.m3u8")

# Download video
result = downloader.download_m3u8_video(m3u8_info, output_path="./videos")
```

**GUI Usage:**
Simply paste any M3U8 URL (or page containing M3U8 videos) into the GUI and click "解析" (Parse). The app will automatically detect and handle M3U8 videos.

### M3U8 Download Process

1. Parse M3U8 file to extract TS segment URLs
2. Download each TS segment to a temporary folder
3. Merge all TS segments into a single video file
4. Optionally convert to MP4 using ffmpeg
5. Clean up temporary files

### TS URL Format

The downloader supports flexible TS URL formats:
- Base URL + relative TS path: `https://cdn.com/m3u8/{video_id}/{segment}.ts`
- Fully qualified TS URLs
- Custom base URL patterns
