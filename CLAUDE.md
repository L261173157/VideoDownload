# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language Preference

**IMPORTANT: Always respond in Chinese (中文) when working with this project.**

## Project Overview

Python 桌面视频下载器，基于 Tkinter GUI + yt-dlp 引擎，支持 1000+ 视频网站。包含独立的 M3U8/HLS 下载器作为备用方案。

## Running the Application

```bash
pip install -r requirements.txt
python main.py
```

依赖：yt-dlp, requests, beautifulsoup4, lxml。可选：ffmpeg（用于合并视频/音频流和 TS→MP4 转换）。

## File Organization

指南文档、调试记录、临时脚本等非项目核心代码的文件统一放在 `docs/` 目录下，禁止散落在项目根目录。

## Architecture

```
main.py → MainWindow (gui/main_window.py)
              ├── VideoDownloader (downloader/video_downloader.py)
              │     ├── ProgressHandler (downloader/progress_handler.py)
              │     └── M3U8Downloader (downloader/m3u8_downloader.py) [延迟加载]
              └── URLValidator (utils/url_validator.py)
```

日志通过 `utils/logger.py` 写入 `logs/` 目录（每日轮转）。

### Download Strategy Chain

VideoDownloader 按优先级尝试以下策略，前一个失败时自动回退到下一个：

1. **直接 MP4 下载** — 检测到直接 MP4 URL 时，用 requests 直接下载（通过 `DirectMP4UrlException` 异常流控制）
2. **yt-dlp 下载** — 标准路径，支持 1000+ 网站
3. **M3U8 备用方案** — yt-dlp 失败时，自动尝试 M3U8Downloader 解析和下载 HLS 流

M3U8Downloader 自身也有多层解析策略：先尝试 video_id 构造 URL → 提取直接 MP4 → 从 URL 参数提取 viewkey → 从路径提取数字 ID → 从页面 HTML 提取 video_id → 直接 M3U8 URL。

### Threading Model

所有耗时操作（URL 解析、下载）在 daemon 线程中执行，GUI 更新通过 `root.after(0, callback)` 调度回主线程，确保 Tkinter 线程安全。

进度回调流：yt-dlp hook → `ProgressHandler.progress_hook()` → 格式化数据 → `MainWindow.update_download_progress()` → `root.after()` 更新 UI。

### Proxy and Cookie Propagation

代理和 Cookie 设置从 GUI 传入 VideoDownloader，并同步传递给 M3U8Downloader。Cookie 以临时 Netscape 格式文件传给 yt-dlp，用完即删。代理格式自动补全协议前缀（如 `127.0.0.1:7890` → `http://127.0.0.1:7890`）。

### Quality Options

| GUI 显示 | 内部值 | yt-dlp 格式 |
|----------|--------|-------------|
| 最佳质量 | `best` | `bestvideo+bestaudio/best` |
| 最佳MP4 | `best-mp4` | `bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best` |
| 仅音频 | `best-audio` | `bestaudio/best` |

### M3U8 Download Process

1. 解析 M3U8 获取 TS 片段列表
2. 逐个下载 TS 到临时目录（带重试，片段间随机延迟 0.1-0.3s 防封）
3. 二进制合并所有 TS 片段
4. 可选 ffmpeg 转 MP4
5. 清理临时文件
