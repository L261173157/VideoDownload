# 视频下载器

一个简单易用的桌面视频下载应用程序，支持从各大视频网站下载视频。

## 功能特性

- ✅ **支持1000+视频网站**：YouTube, B站, 抖音, 快手, Twitter, Vimeo等
- 🎯 **一键解析**：输入网址即可自动解析视频信息
- 📊 **实时进度**：显示下载速度、剩余时间、文件大小
- 💾 **自定义保存**：自由选择视频保存路径
- 🎬 **质量选择**：支持选择不同视频质量
- 🖥️ **图形界面**：简洁直观的Tkinter桌面界面

## 安装说明

### 1. 克隆或下载项目

```bash
cd VideoDownload
```

### 2. 安装依赖

使用pip安装所需的Python包：

```bash
pip install -r requirements.txt
```

### 3. 运行程序

```bash
python main.py
```

## 使用方法

1. **输入视频链接**
   - 在顶部URL输入框中粘贴视频网址
   - 点击"解析"按钮

2. **查看视频信息**
   - 程序会显示视频标题、时长、上传者等信息
   - 确认视频信息正确后继续

3. **选择保存位置**
   - 默认保存到当前工作目录
   - 点击"浏览..."可选择其他文件夹

4. **选择视频质量**
   - 最佳质量：下载最高质量视频
   - 最佳MP4：下载MP4格式的最佳质量
   - 仅音频：只下载音频

5. **开始下载**
   - 点击"开始下载"按钮
   - 查看实时下载进度
   - 等待下载完成

## 支持的网站

本程序基于[yt-dlp](https://github.com/yt-dlp/yt-dlp)开发，支持以下主流网站：

- 📺 YouTube
- 🎬 Bilibili (B站)
- 🎵 抖音 / TikTok
- 📱 快手
- 🐦 Twitter / X
- 🎥 Vimeo
- 以及更多...

查看完整支持列表：[yt-dlp支持的网站](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

## 项目结构

```
VideoDownload/
├── main.py                      # 程序入口
├── requirements.txt             # 依赖列表
├── gui/                         # 图形界面模块
│   ├── __init__.py
│   └── main_window.py          # 主窗口
├── downloader/                  # 下载器模块
│   ├── __init__.py
│   ├── video_downloader.py     # 视频下载核心
│   └── progress_handler.py     # 进度处理
└── utils/                       # 工具模块
    ├── __init__.py
    └── url_validator.py        # URL验证
```

## 系统要求

- Python 3.7 或更高版本
- Windows / macOS / Linux
- 网络连接

## 常见问题

### Q: 提示"无法找到模块"？
A: 请确保已安装所有依赖：`pip install -r requirements.txt`

### Q: 下载失败？
A: 可能的原因：
   - 网络连接问题
   - 视频网站限制访问
   - 视频链接无效或已删除
   - 需要登录才能下载（当前版本不支持登录）

### Q: 下载速度慢？
A: 下载速度取决于：
   - 您的网络带宽
   - 视频服务器的速度
   - 当前网络状况

### Q: 可以下载播放列表吗？
A: 当前版本仅支持单个视频下载，播放列表下载功能正在开发中。

## 注意事项

⚠️ **版权声明**：
- 请仅下载您有权下载的内容
- 遵守目标网站的服务条款
- 请勿将本工具用于商业用途
- 下载的内容仅供个人学习使用

## 依赖库

- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)**: 强大的视频下载库
- **[Tkinter](https://docs.python.org/3/library/tkinter.html)**: Python标准GUI库

## 更新日志

### v1.0.0 (2025-01-21)
- ✨ 首次发布
- 支持基本视频解析和下载功能
- 实时下载进度显示
- 多质量选择
- 自定义保存路径

## 贡献

欢迎提交Issue和Pull Request！

## 许可证

本项目基于 MIT 许可证开源。

---

**享受下载的乐趣！** 🎉