"""GUI主窗口模块"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
from downloader.video_downloader import VideoDownloader
from utils.url_validator import URLValidator


class MainWindow:
    """主窗口类"""

    def __init__(self, root):
        self.root = root
        self.root.title("视频下载器")
        self.root.geometry("700x650")
        self.root.resizable(True, True)

        # 初始化下载器和验证器
        self.downloader = VideoDownloader()
        self.url_validator = URLValidator()
        self.current_video_info = None
        self.is_downloading = False
        self.current_video_file = None  # 保存当前视频文件路径

        # 设置样式
        self.setup_styles()

        # 创建UI组件
        self.create_widgets()

        # 设置下载进度回调
        self.downloader.set_progress_callback(self.update_download_progress)

    def setup_styles(self):
        """设置UI样式"""
        style = ttk.Style()
        style.theme_use('clam')  # 使用现代主题

        # 配置按钮样式
        style.configure('Action.TButton', font=('Arial', 10))

    def create_widgets(self):
        """创建UI组件"""
        # ===== 顶部区域 - URL输入 =====
        top_frame = ttk.LabelFrame(self.root, text="视频链接", padding=10)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        # URL输入框
        url_frame = ttk.Frame(top_frame)
        url_frame.pack(fill=tk.X)

        ttk.Label(url_frame, text="URL:").pack(side=tk.LEFT, padx=(0, 5))

        self.url_entry = ttk.Entry(url_frame)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.url_entry.bind('<Return>', lambda e: self.parse_video_url())

        self.parse_btn = ttk.Button(url_frame, text="解析", command=self.parse_video_url, style='Action.TButton')
        self.parse_btn.pack(side=tk.LEFT)

        # ===== 中间区域 - 视频信息和日志 =====
        info_frame = ttk.LabelFrame(self.root, text="视频信息 / 操作日志", padding=10)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 创建滚动文本框显示视频信息和日志
        info_text_frame = ttk.Frame(info_frame)
        info_text_frame.pack(fill=tk.BOTH, expand=True)

        self.info_text = tk.Text(info_text_frame, height=12, wrap=tk.WORD, font=('Consolas', 9))
        scrollbar = ttk.Scrollbar(info_text_frame, orient=tk.VERTICAL, command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=scrollbar.set)

        self.info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 添加清空日志按钮
        ttk.Button(info_frame, text="清空日志", command=self.clear_log).pack(anchor=tk.E, pady=(5, 0))

        # ===== Cookie设置 =====
        cookie_frame = ttk.LabelFrame(self.root, text="Cookie设置（可选）", padding=10)
        cookie_frame.pack(fill=tk.X, padx=10, pady=5)

        cookie_input_frame = ttk.Frame(cookie_frame)
        cookie_input_frame.pack(fill=tk.X)

        ttk.Label(cookie_input_frame, text="Cookie:").pack(side=tk.LEFT, padx=(0, 5))

        self.cookie_entry = ttk.Entry(cookie_input_frame)
        self.cookie_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        ttk.Button(cookie_input_frame, text="清除", command=self.clear_cookie, style='Action.TButton').pack(side=tk.LEFT)

        # 添加帮助提示
        help_label = ttk.Label(cookie_frame, text="提示: 如果遇到403错误，可以从浏览器复制Cookie粘贴到这里",
                              font=('Arial', 8), foreground='gray')
        help_label.pack(anchor=tk.W, pady=(5, 0))

        # ===== 保存路径选择 =====
        path_frame = ttk.LabelFrame(self.root, text="保存设置", padding=10)
        path_frame.pack(fill=tk.X, padx=10, pady=5)

        path_input_frame = ttk.Frame(path_frame)
        path_input_frame.pack(fill=tk.X)

        ttk.Label(path_input_frame, text="保存路径:").pack(side=tk.LEFT, padx=(0, 5))

        self.path_entry = ttk.Entry(path_input_frame)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        # 设置默认下载路径为videos文件夹
        default_path = os.path.join(os.getcwd(), 'videos')
        # 如果videos文件夹不存在，创建它
        if not os.path.exists(default_path):
            try:
                os.makedirs(default_path)
            except:
                default_path = os.getcwd()  # 如果创建失败，使用当前目录

        self.path_entry.insert(0, default_path)

        self.browse_btn = ttk.Button(path_input_frame, text="浏览...", command=self.browse_folder, style='Action.TButton')
        self.browse_btn.pack(side=tk.LEFT)

        # 质量选择
        quality_frame = ttk.Frame(path_frame)
        quality_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(quality_frame, text="视频质量:").pack(side=tk.LEFT, padx=(0, 10))

        self.quality_var = tk.StringVar(value='best')
        quality_options = [
            ('最佳质量', 'best'),
            ('最佳MP4', 'best-mp4'),
            ('仅音频', 'best-audio')
        ]

        for text, value in quality_options:
            ttk.Radiobutton(quality_frame, text=text, variable=self.quality_var, value=value).pack(side=tk.LEFT, padx=5)

        # ===== 下载按钮 =====
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=10, pady=5)

        self.download_btn = ttk.Button(
            button_frame,
            text="开始下载",
            command=self.start_download,
            style='Action.TButton'
        )
        self.download_btn.pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)

        # 添加播放按钮（初始禁用）
        self.play_btn = ttk.Button(
            button_frame,
            text="播放视频",
            command=self.play_video,
            style='Action.TButton',
            state='disabled'
        )
        self.play_btn.pack(side=tk.LEFT, padx=(5, 0), expand=True, fill=tk.X)

        # ===== 底部区域 - 进度显示 =====
        progress_frame = ttk.LabelFrame(self.root, text="下载进度", padding=10)
        progress_frame.pack(fill=tk.X, padx=10, pady=5)

        # 进度条
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=400)
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))

        # 状态标签
        status_frame = ttk.Frame(progress_frame)
        status_frame.pack(fill=tk.X)

        self.status_label = ttk.Label(status_frame, text="等待操作...", font=('Arial', 9))
        self.status_label.pack(side=tk.LEFT)

        self.percentage_label = ttk.Label(status_frame, text="0%", font=('Arial', 9, 'bold'))
        self.percentage_label.pack(side=tk.RIGHT)

        # 详细信息
        detail_frame = ttk.Frame(progress_frame)
        detail_frame.pack(fill=tk.X, pady=(5, 0))

        self.speed_label = ttk.Label(detail_frame, text="", font=('Arial', 9))
        self.speed_label.pack(side=tk.LEFT)

        self.eta_label = ttk.Label(detail_frame, text="", font=('Arial', 9))
        self.eta_label.pack(side=tk.RIGHT)

        self.size_label = ttk.Label(detail_frame, text="", font=('Arial', 9))
        self.size_label.pack()

    def parse_video_url(self):
        """解析视频URL"""
        url = self.url_entry.get().strip()

        if not url:
            messagebox.showwarning("警告", "请输入视频URL")
            return

        # 验证并规范化URL
        if not self.url_validator.is_valid_url(url):
            messagebox.showerror("错误", "无效的URL格式")
            self.log_message("URL 格式验证失败", 'ERROR')
            return

        url = self.url_validator.normalize_url(url)
        self.log_message(f"开始解析视频: {url}", 'INFO')

        # 更新状态
        self.status_label.config(text="正在解析视频信息...")
        self.parse_btn.config(state='disabled')
        self.info_text.delete(1.0, tk.END)

        # 在新线程中解析视频信息
        def parse_thread():
            try:
                # 获取Cookie
                cookie = self.get_cookie()
                video_info = self.downloader.get_video_info(url, cookie=cookie)
                self.root.after(0, lambda: self.display_video_info(video_info))
            except Exception as e:
                error_msg = f"解析失败: {str(e)}"
                self.root.after(0, lambda: self.log_message(error_msg, 'ERROR'))
                self.root.after(0, lambda: self.show_error(error_msg))
            finally:
                self.root.after(0, lambda: self.parse_btn.config(state='normal'))

        threading.Thread(target=parse_thread, daemon=True).start()

    def log_message(self, message, level='INFO'):
        """
        在日志文本框中添加消息

        Args:
            message: 日志消息
            level: 日志级别 (INFO, WARNING, ERROR)
        """
        import datetime
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')

        # 根据级别设置颜色标签
        if level == 'ERROR':
            tag = 'error'
        elif level == 'WARNING':
            tag = 'warning'
        else:
            tag = 'info'

        # 配置文本标签颜色
        self.info_text.tag_config(tag, foreground=self._get_color_for_level(level))
        self.info_text.tag_config('timestamp', foreground='gray')

        # 插入日志
        self.info_text.insert(tk.END, f"[{timestamp}] ", 'timestamp')
        self.info_text.insert(tk.END, f"[{level}] ", tag)
        self.info_text.insert(tk.END, f"{message}\n")

        # 自动滚动到底部
        self.info_text.see(tk.END)

    def _get_color_for_level(self, level):
        """获取日志级别对应的颜色"""
        colors = {
            'INFO': 'black',
            'WARNING': '#FF8C00',  # 深橙色
            'ERROR': '#DC143C',    # 深红色
            'SUCCESS': '#228B22'   # 深绿色
        }
        return colors.get(level, 'black')

    def clear_log(self):
        """清空日志文本框"""
        self.info_text.delete(1.0, tk.END)

    def display_video_info(self, video_info):
        """显示视频信息"""
        self.current_video_info = video_info

        # 格式化时长
        duration = int(video_info.get('duration', 0))
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60
        if hours > 0:
            duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            duration_str = f"{minutes:02d}:{seconds:02d}"

        # 格式化观看次数
        view_count = video_info.get('view_count', 0)
        if view_count > 10000:
            views_str = f"{view_count / 10000:.1f}万"
        else:
            views_str = str(view_count)

        # 检查是否为M3U8视频
        is_m3u8 = video_info.get('is_m3u8', False)

        # 记录到日志
        self.log_message(f"视频标题: {video_info.get('title', '未知')}", 'SUCCESS')

        if is_m3u8:
            self.log_message("类型: M3U8视频流", 'WARNING')
            self.log_message(f"描述: {video_info.get('description', 'N/A')}", 'INFO')
        else:
            self.log_message(f"上传者: {video_info.get('uploader', '未知')}", 'INFO')
            self.log_message(f"时长: {duration_str}", 'INFO')
            self.log_message(f"观看次数: {views_str}", 'INFO')
            self.log_message(f"可用格式: {len(video_info.get('formats', []))} 种", 'INFO')

        self.log_message("-" * 50, 'INFO')

        self.status_label.config(text="视频信息解析完成")

    def browse_folder(self):
        """浏览文件夹"""
        folder = filedialog.askdirectory(initialdir=self.path_entry.get())
        if folder:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, folder)

    def clear_cookie(self):
        """清空Cookie输入框"""
        self.cookie_entry.delete(0, tk.END)

    def get_cookie(self):
        """获取Cookie字符串"""
        return self.cookie_entry.get().strip()

    def start_download(self):
        """开始下载"""
        if self.is_downloading:
            messagebox.showinfo("提示", "正在下载中,请等待...")
            return

        if not self.current_video_info:
            messagebox.showwarning("警告", "请先解析视频URL")
            return

        url = self.url_validator.normalize_url(self.url_entry.get())
        output_path = self.path_entry.get().strip()
        quality = self.quality_var.get()

        # 验证保存路径
        if not os.path.exists(output_path):
            messagebox.showerror("错误", "保存路径不存在")
            self.log_message(f"保存路径不存在: {output_path}", 'ERROR')
            return

        self.log_message(f"开始下载视频到: {output_path}", 'INFO')
        self.log_message(f"视频质量: {quality}", 'INFO')

        # 开始下载
        self.is_downloading = True
        self.download_btn.config(state='disabled')
        self.progress_bar['value'] = 0
        self.status_label.config(text="正在下载...")

        def download_thread():
            try:
                # 获取Cookie
                cookie = self.get_cookie()
                # 传递video_info和cookie参数
                result = self.downloader.download_video(url, output_path, quality, self.current_video_info, cookie=cookie)
                self.root.after(0, lambda: self.download_finished(result))
            except Exception as e:
                error_msg = f"下载失败: {str(e)}"
                self.root.after(0, lambda: self.log_message(error_msg, 'ERROR'))
                self.root.after(0, lambda: self.show_error(error_msg))
            finally:
                self.is_downloading = False
                self.root.after(0, lambda: self.download_btn.config(state='normal'))

        threading.Thread(target=download_thread, daemon=True).start()

    def update_download_progress(self, downloaded, total, percentage, speed, eta, size):
        """更新下载进度"""
        def update():
            if percentage > 0:
                self.progress_bar['value'] = percentage
                self.percentage_label.config(text=f"{percentage:.1f}%")

            self.status_label.config(text=f"正在下载...")
            self.speed_label.config(text=f"速度: {speed}")
            self.eta_label.config(text=f"ETA: {eta}")
            self.size_label.config(text=size)

        self.root.after(0, update)

    def download_finished(self, result):
        """下载完成"""
        self.progress_bar['value'] = 100
        self.percentage_label.config(text="100%")

        if result.get('success'):
            self.status_label.config(text="下载完成!")
            self.speed_label.config(text="")
            self.eta_label.config(text="")

            filename = result.get('filename', '')
            if filename and os.path.exists(filename):
                # 保存视频文件路径
                self.current_video_file = filename
                # 启用播放按钮
                self.play_btn.config(state='normal')

                success_msg = f"下载完成! 文件: {os.path.basename(filename)}"
                self.log_message(success_msg, 'SUCCESS')
                self.log_message(f"文件位置: {filename}", 'INFO')
                messagebox.showinfo("成功", f"{success_msg}\n位置: {filename}")
            else:
                # 清空视频文件路径
                self.current_video_file = None
                # 禁用播放按钮
                self.play_btn.config(state='disabled')

                success_msg = f"下载完成! 标题: {result.get('title', '未知')}"
                self.log_message(success_msg, 'SUCCESS')
                self.log_message("注意: 无法确认文件位置", 'WARNING')
                messagebox.showinfo("成功", f"{success_msg}\n注意: 无法确认文件位置")
        else:
            # 下载失败，清空视频文件路径并禁用播放按钮
            self.current_video_file = None
            self.play_btn.config(state='disabled')

            self.status_label.config(text="下载失败")
            error_msg = result.get('error', '未知错误')

            # 在GUI日志中显示完整错误
            self.log_message("=" * 50, 'ERROR')
            self.log_message("下载失败", 'ERROR')
            self.log_message(error_msg, 'ERROR')
            self.log_message("=" * 50, 'ERROR')

            # 如果错误信息太长，只显示前500字符在弹窗
            if len(error_msg) > 500:
                popup_msg = error_msg[:500] + "\n...(错误信息被截断，完整信息请查看日志)"
            else:
                popup_msg = error_msg

            messagebox.showerror("错误", f"下载失败!\n\n错误详情:\n{popup_msg}")

    def show_error(self, message):
        """显示错误消息"""
        self.status_label.config(text="发生错误")
        messagebox.showerror("错误", message)

    def play_video(self):
        """使用系统默认播放器播放视频"""
        if not self.current_video_file:
            messagebox.showwarning("警告", "没有可播放的视频文件")
            return

        if not os.path.exists(self.current_video_file):
            messagebox.showerror("错误", f"视频文件不存在:\n{self.current_video_file}")
            return

        try:
            import platform
            import subprocess

            system = platform.system()

            if system == 'Windows':
                os.startfile(self.current_video_file)
            elif system == 'Darwin':  # macOS
                subprocess.run(['open', self.current_video_file])
            elif system == 'Linux':
                subprocess.run(['xdg-open', self.current_video_file])
            else:
                # 其他系统尝试使用subprocess
                subprocess.run(['xdg-open' if system == 'Linux' else 'open', self.current_video_file])

            self.log_message(f"已打开视频: {os.path.basename(self.current_video_file)}", 'SUCCESS')

        except Exception as e:
            error_msg = f"无法打开视频文件:\n{str(e)}"
            self.log_message(error_msg, 'ERROR')
            messagebox.showerror("播放失败", error_msg)
