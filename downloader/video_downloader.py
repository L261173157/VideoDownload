"""视频下载器核心模块"""

import yt_dlp
import os
import re
import time
from .progress_handler import ProgressHandler
from utils.logger import get_logger


class VideoDownloader:
    """视频下载器类"""

    def __init__(self):
        self.progress_handler = ProgressHandler()
        self.logger = get_logger()
        self.logger.info("VideoDownloader 初始化")

        # 延迟导入M3U8Downloader，避免循环导入
        self._m3u8_downloader = None

    @property
    def m3u8_downloader(self):
        """延迟加载M3U8下载器"""
        if self._m3u8_downloader is None:
            from .m3u8_downloader import M3U8Downloader
            self._m3u8_downloader = M3U8Downloader()
            # 设置相同的进度回调
            if self.progress_handler.progress_callback:
                self._m3u8_downloader.set_progress_callback(self._wrap_m3u8_callback())
        return self._m3u8_downloader

    def _wrap_m3u8_callback(self):
        """包装M3U8进度回调以适配GUI格式"""
        def callback(downloaded, total, percentage, speed, eta, size):
            if self.progress_handler.progress_callback:
                # M3U8下载器返回的是片段数，转换为字节格式
                self.progress_handler.progress_callback(
                    downloaded * 1024 * 1024,  # 假设每个片段1MB
                    total * 1024 * 1024,
                    percentage,
                    speed,
                    eta,
                    f"{downloaded}/{total} 片段"
                )
        return callback

    def set_progress_callback(self, callback):
        """
       设置下载进度回调函数

        Args:
            callback: 回调函数
        """
        self.progress_handler.set_callback(callback)

    def get_video_info(self, url, use_m3u8_fallback=True, cookie=None):
        """
        获取视频信息（不下载）

        Args:
            url: 视频URL
            use_m3u8_fallback: 是否在yt-dlp失败时尝试M3U8
            cookie: 可选的Cookie字符串

        Returns:
            dict: 视频信息字典
            {
                'title': 视频标题,
                'duration': 时长(秒),
                'thumbnail': 缩略图URL,
                'uploader': 上传者,
                'view_count': 观看次数,
                'formats': 可用格式列表,
                'is_m3u8': 是否为M3U8视频
            }
        """
        self.logger.info(f"开始解析视频URL: {url}")
        if cookie:
            self.logger.info("使用自定义Cookie")

        # 策略0: 检测直接的MP4 URL（优先级最高）
        if self._is_direct_mp4_url(url):
            self.logger.info("检测到直接MP4 URL，使用直接解析模式")
            return self._get_direct_mp4_info(url, url, cookie=cookie)

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }

        # 如果提供了Cookie，添加到yt-dlp选项
        if cookie:
            ydl_opts['cookiefile'] = self._create_cookie_file(cookie)
            self.logger.info("已将Cookie添加到yt-dlp请求")

        # 首先尝试使用yt-dlp
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                # 提取视频信息
                video_info = {
                    'title': info.get('title', '未知标题'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'uploader': info.get('uploader', '未知上传者'),
                    'view_count': info.get('view_count', 0),
                    'description': info.get('description', ''),
                    'formats': [],
                    'is_m3u8': False
                }

                self.logger.info(f"成功获取视频信息: {video_info['title']}")

                # 提取可用格式（只取主要的几种）
                formats = info.get('formats', [])
                seen_resolutions = set()

                for fmt in formats:
                    # 过滤掉只有视频没有音频的格式
                    if fmt.get('vcodec') == 'none':
                        continue

                    resolution = fmt.get('resolution', 'unknown')
                    ext = fmt.get('ext', 'mp4')
                    filesize = fmt.get('filesize', 0)

                    # 避免重复分辨率
                    if resolution not in seen_resolutions:
                        video_info['formats'].append({
                            'format_id': fmt.get('format_id'),
                            'ext': ext,
                            'resolution': resolution,
                            'filesize': filesize,
                            'quality': fmt.get('format_note', 'unknown')
                        })
                        seen_resolutions.add(resolution)

                return video_info

        except Exception as e:
            self.logger.warning(f"yt-dlp解析失败: {str(e)}")

            # 尝试使用M3U8下载器作为备用方案
            if use_m3u8_fallback:
                self.logger.info("尝试使用M3U8下载器解析...")
                try:
                    return self._get_m3u8_video_info(url, cookie=cookie)
                except Exception as m3u8_error:
                    self.logger.error(f"M3U8解析也失败: {str(m3u8_error)}")
                    raise Exception(f"获取视频信息失败:\nyt-dlp错误: {str(e)}\nM3U8错误: {str(m3u8_error)}")
            else:
                raise Exception(f"获取视频信息失败: {str(e)}")

    def _get_m3u8_video_info(self, url, cookie=None):
        """使用M3U8下载器获取视频信息（增强错误处理）"""
        self.logger.info(f"使用M3U8方式解析: {url}")

        # 如果提供了Cookie，设置到M3U8下载器
        if cookie:
            self.m3u8_downloader.set_cookie(cookie)
            self.logger.info("已将Cookie设置到M3U8下载器")

        try:
            # 判断是直接的M3U8 URL还是包含M3U8视频的页面
            if '.m3u8' in url.lower():
                # 直接的M3U8 URL
                m3u8_info = self.m3u8_downloader.parse_m3u8_direct(url)
            else:
                # 从页面解析 - 不传递video_id，让parse_m3u8_from_url自己按顺序尝试
                # 这样它会先尝试提取直接MP4 URL，然后再尝试其他方法
                m3u8_info = self.m3u8_downloader.parse_m3u8_from_url(url, video_id=None)

            # 转换为统一格式
            return {
                'title': m3u8_info.get('title', 'M3U8视频'),
                'duration': 0,
                'thumbnail': '',
                'uploader': 'M3U8视频流',
                'view_count': 0,
                'description': f"M3U8视频流 - {m3u8_info.get('ts_count', 0)} 个片段",
                'formats': [{
                    'format_id': 'm3u8',
                    'ext': 'mp4',
                    'resolution': 'unknown',
                    'filesize': 0,
                    'quality': 'M3U8流'
                }],
                'is_m3u8': True,
                'm3u8_info': m3u8_info
            }

        except Exception as e:
            # 检查是否是DirectMP4UrlException
            if type(e).__name__ == 'DirectMP4UrlException':
                # 提取MP4 URL并使用yt-dlp解析
                from .m3u8_downloader import DirectMP4UrlException
                if isinstance(e, DirectMP4UrlException):
                    mp4_url = e.mp4_url
                    self.logger.info(f"检测到直接MP4 URL，使用yt-dlp解析: {mp4_url}")
                    return self._get_direct_mp4_info(mp4_url, url)

            # 提供可操作的错误消息
            error_str = str(e)
            self.logger.error(f"M3U8解析失败: {error_str}")

            if "403" in error_str or "Forbidden" in error_str:
                raise Exception(
                    "M3U8下载失败: 网站拒绝访问 (403 Forbidden)\n\n"
                    "可能的原因:\n"
                    "1. 网站需要特定的请求头或Cookie\n"
                    "2. 网站检测到自动化访问\n"
                    "3. 视频可能需要登录才能访问\n\n"
                    "建议: 请检查日志获取详细信息"
                )
            elif "404" in error_str or "Not Found" in error_str:
                raise Exception(
                    "M3U8下载失败: 找不到视频资源 (404 Not Found)\n\n"
                    "可能的原因:\n"
                    "1. 视频已被删除\n"
                    "2. URL格式不正确\n"
                    "3. 视频ID提取失败\n\n"
                    f"URL: {url}"
                )
            elif "无法获取M3U8文件内容" in error_str:
                raise Exception(
                    "M3U8下载失败: 无法获取M3U8文件内容\n\n"
                    "可能的原因:\n"
                    "1. 视频资源已被删除\n"
                    "2. M3U8服务器不可用\n"
                    "3. 网络连接问题\n\n"
                    "建议: 请检查网络连接或稍后重试"
                )
            else:
                # 保留原始错误信息
                raise Exception(f"M3U8下载失败: {error_str}")

    def _get_direct_mp4_info(self, mp4_url, original_url, cookie=None):
        """
        使用yt-dlp获取直接MP4 URL的视频信息

        Args:
            mp4_url: 直接的MP4视频URL
            original_url: 原始页面URL（用于获取标题等）
            cookie: 可选的Cookie字符串

        Returns:
            dict: 视频信息字典
        """
        self.logger.info(f"使用yt-dlp解析直接MP4 URL: {mp4_url}")

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }

        # 如果提供了Cookie，添加到yt-dlp选项
        if cookie:
            ydl_opts['cookiefile'] = self._create_cookie_file(cookie)
            self.logger.info("已将Cookie添加到yt-dlp请求（直接MP4）")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(mp4_url, download=False)

                # 提取视频信息
                video_info = {
                    'title': info.get('title', '直接MP4视频'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'uploader': info.get('uploader', 'MP4视频'),
                    'view_count': info.get('view_count', 0),
                    'description': info.get('description', '直接MP4视频文件'),
                    'formats': [],
                    'is_m3u8': False,
                    'direct_mp4_url': mp4_url  # 保存直接的MP4 URL
                }

                self.logger.info(f"成功获取直接MP4视频信息: {video_info['title']}")

                # 提取可用格式
                formats = info.get('formats', [])
                seen_resolutions = set()

                for fmt in formats:
                    if fmt.get('vcodec') == 'none':
                        continue

                    resolution = fmt.get('resolution', 'unknown')
                    ext = fmt.get('ext', 'mp4')
                    filesize = fmt.get('filesize', 0)

                    if resolution not in seen_resolutions:
                        video_info['formats'].append({
                            'format_id': fmt.get('format_id'),
                            'ext': ext,
                            'resolution': resolution,
                            'filesize': filesize,
                            'quality': fmt.get('format_note', 'unknown')
                        })
                        seen_resolutions.add(resolution)

                return video_info

        except Exception as e:
            self.logger.warning(f"yt-dlp解析直接MP4 URL失败: {str(e)}")
            # 如果yt-dlp无法解析，返回基本信息
            return {
                'title': f'MP4视频_{int(time.time())}',
                'duration': 0,
                'thumbnail': '',
                'uploader': 'MP4视频',
                'view_count': 0,
                'description': '直接MP4视频文件',
                'formats': [{
                    'format_id': 'mp4',
                    'ext': 'mp4',
                    'resolution': 'unknown',
                    'filesize': 0,
                    'quality': 'unknown'
                }],
                'is_m3u8': False,
                'direct_mp4_url': mp4_url
            }

    def download_video(self, url, output_path='.', quality='best', video_info=None, cookie=None):
        """
        下载视频

        Args:
            url: 视频URL
            output_path: 保存路径
            quality: 视频质量 (best/worst/best[ext]/worst[ext])
            video_info: 可选的视频信息（用于M3U8下载）
            cookie: 可选的Cookie字符串

        Returns:
            dict: 下载结果
        """
        self.logger.info(f"开始下载视频: {url}")
        self.logger.info(f"保存路径: {output_path}")
        self.logger.info(f"视频质量: {quality}")
        if cookie:
            self.logger.info("使用自定义Cookie")

        # 如果提供了video_info且是M3U8，使用M3U8下载器
        if video_info and video_info.get('is_m3u8'):
            return self._download_m3u8_video(video_info.get('m3u8_info'), output_path, cookie=cookie)

        # 如果提供了video_info且包含直接MP4 URL，使用直接下载
        if video_info and video_info.get('direct_mp4_url'):
            self.logger.info(f"使用直接MP4 URL下载: {video_info['direct_mp4_url']}")
            return self._download_with_ytdlp(video_info['direct_mp4_url'], output_path, quality, cookie=cookie)

        # 格式化输出路径
        if not output_path.endswith('/') and not output_path.endswith('\\'):
            output_path += '/'

        # 首先尝试使用yt-dlp下载
        try:
            return self._download_with_ytdlp(url, output_path, quality, cookie=cookie)
        except Exception as e:
            self.logger.warning(f"yt-dlp下载失败: {str(e)}")

            # 如果yt-dlp失败，尝试M3U8下载
            self.logger.info("尝试使用M3U8下载器...")
            try:
                from .m3u8_downloader import DirectMP4UrlException

                # 如果提供了Cookie，设置到M3U8下载器
                if cookie:
                    self.m3u8_downloader.set_cookie(cookie)
                    self.logger.info("已将Cookie设置到M3U8下载器")

                # 策略1: 如果是直接的M3U8 URL
                if '.m3u8' in url.lower():
                    m3u8_info = self.m3u8_downloader.parse_m3u8_direct(url)
                else:
                    # 策略2: 尝试从URL参数提取viewkey
                    video_id = None
                    from urllib.parse import urlparse, parse_qs
                    parsed = urlparse(url)
                    params = parse_qs(parsed.query)

                    if 'viewkey' in params:
                        video_id = params['viewkey'][0]
                        self.logger.info(f"从URL参数提取到viewkey: {video_id}")
                    else:
                        # 策略3: 从URL路径提取数字ID
                        id_match = re.search(r'/(\d{6,})', url)
                        if id_match:
                            video_id = id_match.group(1)

                    m3u8_info = self.m3u8_downloader.parse_m3u8_from_url(url, video_id)

                return self._download_m3u8_video(m3u8_info, output_path, cookie=cookie)

            except DirectMP4UrlException as mp4_ex:
                # 如果找到直接MP4 URL，使用yt-dlp下载
                self.logger.info(f"检测到直接MP4 URL: {mp4_ex.mp4_url}")
                return self._download_with_ytdlp(mp4_ex.mp4_url, output_path, quality, cookie=cookie)

            except Exception as m3u8_error:
                self.logger.error(f"M3U8下载也失败: {str(m3u8_error)}")
                import traceback
                error_details = f"yt-dlp错误: {str(e)}\n\nM3U8错误: {str(m3u8_error)}\n\n{traceback.format_exc()}"
                return {
                    'success': False,
                    'error': error_details
                }

    def _download_with_ytdlp(self, url, output_path, quality, cookie=None):
        """使用yt-dlp下载视频"""
        ydl_opts = {
            'outtmpl': f'{output_path}%(title)s.%(ext)s',
            'format': self._get_format_string(quality),
            'progress_hooks': [self.progress_handler.progress_hook],
            'quiet': True,
            'no_warnings': True,
        }

        # 如果提供了Cookie，添加到yt-dlp选项
        if cookie:
            ydl_opts['cookiefile'] = self._create_cookie_file(cookie)
            self.logger.info("已将Cookie添加到yt-dlp下载请求")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            self.logger.info("正在调用 yt-dlp 下载...")
            info = ydl.extract_info(url, download=True)

            self.logger.info(f"下载完成，视频标题: {info.get('title', '未知')}")

            # 获取下载后的文件名
            filename = ydl.prepare_filename(info)
            self.logger.debug(f"准备文件名: {filename}")

            # 检查文件是否实际存在
            if not os.path.exists(filename):
                self.logger.warning(f"文件不存在: {filename}")
                # 尝试查找可能的文件名变体
                directory = os.path.dirname(filename) or '.'
                title = info.get('title', '')
                # 尝试匹配可能的文件
                for ext in ['.mp4', '.webm', '.mkv', '.m4a']:
                    possible_file = os.path.join(directory, f"{title}{ext}")
                    if os.path.exists(possible_file):
                        filename = possible_file
                        self.logger.info(f"找到实际文件: {filename}")
                        break
            else:
                self.logger.info(f"确认文件存在: {filename}")

            return {
                'success': True,
                'filename': filename,
                'title': info.get('title', '未知标题')
            }

    def _download_m3u8_video(self, m3u8_info, output_path, cookie=None):
        """使用M3U8下载器下载视频"""
        self.logger.info("使用M3U8下载器下载...")

        # 如果提供了Cookie，设置到M3U8下载器
        if cookie:
            self.m3u8_downloader.set_cookie(cookie)
            self.logger.info("已将Cookie设置到M3U8下载器（下载）")

        # 更新进度回调
        if self.progress_handler.progress_callback:
            self.m3u8_downloader.set_progress_callback(self._wrap_m3u8_callback())

        result = self.m3u8_downloader.download_m3u8_video(m3u8_info, output_path)

        if result.get('success'):
            return {
                'success': True,
                'filename': result.get('output_file'),
                'title': m3u8_info.get('title', 'M3U8视频')
            }
        else:
            failed_count = len(result.get('failed', []))
            error_msg = f"下载失败: {result['downloaded']}/{result['total']} 片段成功"
            if failed_count > 0:
                error_msg += f", {failed_count} 个片段失败"

            return {
                'success': False,
                'error': error_msg
            }

    def _is_direct_mp4_url(self, url):
        """
        检测是否为直接的MP4视频URL

        Args:
            url: 视频URL

        Returns:
            bool: 是否为直接MP4 URL
        """
        # 检查URL路径是否直接指向.mp4文件（而不是包含.mp4的页面URL）
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.lower()

        # 路径以.mp4结尾才是直接的MP4文件
        return path.endswith('.mp4')

    def _get_format_string(self, quality):
        """
        根据质量参数生成格式字符串
        使用 ffmpeg 合并视频和音频以获得最佳质量

        Args:
            quality: 质量参数

        Returns:
            str: yt-dlp格式字符串
        """
        format_map = {
            'best': 'bestvideo+bestaudio/best',  # 最佳视频+最佳音频合并
            'worst': 'worstvideo+worstaudio/worst',
            'best-mp4': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'best-audio': 'bestaudio/best',
        }

        return format_map.get(quality, 'bestvideo+bestaudio/best')

    def _create_cookie_file(self, cookie_string):
        """
        创建临时Cookie文件供yt-dlp使用

        Args:
            cookie_string: Cookie字符串 (Netscape格式或键值对格式)

        Returns:
            str: 临时Cookie文件路径
        """
        import tempfile
        import os

        # 创建临时文件
        fd, temp_path = tempfile.mkstemp(suffix='.txt', text=True)

        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                # 检查是否是Netscape格式
                if cookie_string.strip().startswith('# Netscape'):
                    # 已经是Netscape格式，直接写入
                    f.write(cookie_string)
                else:
                    # 尝试解析键值对格式
                    # 格式: name1=value1; name2=value2
                    f.write("# Netscape HTTP Cookie File\n")
                    f.write("# This file is generated by VideoDownloader\n\n")

                    cookies = cookie_string.split(';')
                    for cookie in cookies:
                        cookie = cookie.strip()
                        if '=' in cookie:
                            name, value = cookie.split('=', 1)
                            # Netscape格式: domain \t flag \t path \t secure \t expiration \t name \t value
                            f.write(f".\tTRUE\t/\tFALSE\t0\t{name.strip()}\t{value.strip()}\n")

            self.logger.info(f"已创建临时Cookie文件: {temp_path}")
            return temp_path

        except Exception as e:
            self.logger.error(f"创建Cookie文件失败: {str(e)}")
            # 如果创建失败，返回None，yt-dlp会忽略它
            try:
                os.unlink(temp_path)
            except:
                pass
            return None

    def cancel_download(self):
        """
        取消下载（待实现）
        """
        # yt-dlp的取消下载比较复杂，需要使用多线程和事件
        pass
