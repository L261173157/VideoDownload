"""M3U8视频下载器模块

支持M3U8视频流解析和下载
参考实现：91porn视频下载器
"""

import requests
import os
import re
import time
import random
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from .progress_handler import ProgressHandler
from utils.logger import get_logger


class DirectMP4UrlException(Exception):
    """直接MP4 URL异常 - 当找到直接的MP4视频URL时抛出"""
    def __init__(self, mp4_url):
        self.mp4_url = mp4_url
        super().__init__(f"找到直接MP4 URL: {mp4_url}")


class M3U8Downloader:
    """M3U8视频下载器类"""

    def __init__(self):
        self.progress_handler = ProgressHandler()
        self.logger = get_logger()
        self.session = requests.Session()
        self.proxy = None  # 代理设置

        # 设置默认超时（从20增加到30秒）
        self.timeout = 30

        # 设置下载延迟范围（秒）- 降低延迟提升下载速度
        self.delay_min = 0.1  # 最小延迟
        self.delay_max = 0.3  # 最大延迟

        # 设置默认M3U8 CDN基础URL（可配置）
        self.m3u8_cdn_base = "https://la3.killcovid2021.com"

        # 设置请求头（模拟真实浏览器）
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://91porn.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }

        self.session.headers.update(self.headers)
        self.custom_cookie = None  # 自定义Cookie
        self.logger.info("M3U8Downloader 初始化 (超时: 30s, 延迟: 0.1-0.3s)")

    def set_progress_callback(self, callback):
        """
        设置下载进度回调函数

        Args:
            callback: 回调函数
        """
        self.progress_handler.set_callback(callback)

    def set_cookie(self, cookie_string):
        """
        设置自定义Cookie

        Args:
            cookie_string: Cookie字符串 (格式: name1=value1; name2=value2)
        """
        self.custom_cookie = cookie_string

        # 解析Cookie并添加到session
        if cookie_string:
            # 从字符串解析Cookie
            cookie_dict = {}
            for item in cookie_string.split(';'):
                item = item.strip()
                if '=' in item:
                    name, value = item.split('=', 1)
                    cookie_dict[name.strip()] = value.strip()

            # 更新session的cookies
            self.session.cookies.update(cookie_dict)
            self.logger.info(f"已设置自定义Cookie: {len(cookie_dict)} 个cookie")
        else:
            self.logger.info("清空自定义Cookie")

    def set_proxy(self, proxy_url):
        """
        设置代理服务器

        Args:
            proxy_url: 代理URL，格式如 'http://127.0.0.1:7890'
                      留空或None表示不使用代理
        """
        self.proxy = proxy_url.strip() if proxy_url else None
        
        if self.proxy:
            # 设置代理到session
            self.session.proxies = {
                'http': self.proxy,
                'https': self.proxy
            }
            self.logger.info(f"已设置代理: {self.proxy}")
        else:
            # 清除代理
            self.session.proxies = None
            self.logger.info("已禁用代理")

    def set_download_delay(self, min_delay=0.1, max_delay=0.3):
        """
        设置下载片段之间的延迟时间

        Args:
            min_delay: 最小延迟（秒），默认0.1
            max_delay: 最大延迟（秒），默认0.3
        """
        self.delay_min = max(0, min_delay)  # 确保不为负数
        self.delay_max = max(self.delay_min, max_delay)  # 确保max >= min
        self.logger.info(f"已设置下载延迟: {self.delay_min}-{self.delay_max}秒")

    def set_m3u8_cdn_base(self, cdn_base_url):
        """
        设置M3U8 CDN基础URL

        Args:
            cdn_base_url: CDN基础URL（例如：https://la3.killcovid2021.com）
        """
        # 移除末尾的斜杠
        self.m3u8_cdn_base = cdn_base_url.rstrip('/')
        self.logger.info(f"已设置M3U8 CDN基础URL: {self.m3u8_cdn_base}")

    def _extract_viewkey_from_url(self, page_url):
        """
        从URL中提取viewkey参数（91porn等站点使用）

        Args:
            page_url: 页面URL

        Returns:
            str: viewkey字符串，失败返回None
        """
        try:
            parsed = urlparse(page_url)
            params = parse_qs(parsed.query)

            if 'viewkey' in params:
                viewkey = params['viewkey'][0]
                self.logger.info(f"从URL参数提取到viewkey: {viewkey}")
                return viewkey

            return None
        except Exception as e:
            self.logger.warning(f"提取viewkey失败: {str(e)}")
            return None

    def parse_m3u8_from_url(self, page_url, video_id=None):
        """
        从页面URL解析M3U8视频信息（增强错误处理）

        Args:
            page_url: 视频页面URL
            video_id: 可选的视频ID

        Returns:
            dict: 包含M3U8信息的字典
            {
                'm3u8_url': M3U8文件URL,
                'video_id': 视频ID,
                'ts_count': TS文件数量,
                'title': 视频标题
            }
        """
        self.logger.info(f"开始解析M3U8页面: {page_url}")

        try:
            # 策略1: 如果提供了video_id，直接构造M3U8 URL
            if video_id:
                self.logger.info(f"使用提供的video_id: {video_id}")
                return self._fetch_m3u8_by_id(video_id)

            # 策略2: 尝试从页面HTML中提取直接的MP4 URL（优先级最高）
            self.logger.info("尝试从页面HTML提取直接MP4 URL...")
            direct_mp4_url = self._extract_direct_mp4_url(page_url)

            if direct_mp4_url:
                # 返回特殊的标记，表示这是一个直接的MP4 URL
                self.logger.info(f"找到直接MP4 URL，将使用直接下载模式")
                raise DirectMP4UrlException(direct_mp4_url)

            # 策略3: 尝试从URL参数中提取viewkey（91porn等站点）
            self.logger.info("尝试从URL参数提取viewkey...")
            viewkey = self._extract_viewkey_from_url(page_url)

            if viewkey:
                self.logger.info(f"成功提取viewkey: {viewkey}")
                return self._fetch_m3u8_by_id(viewkey)

            # 策略4: 尝试从URL路径中提取数字ID
            self.logger.info("尝试从URL路径提取数字ID...")
            id_match = re.search(r'/(\d{6,})', page_url)
            if id_match:
                numeric_id = id_match.group(1)
                self.logger.info(f"从URL路径提取到数字ID: {numeric_id}")
                return self._fetch_m3u8_by_id(numeric_id)

            # 策略5: 从页面HTML提取video_id
            self.logger.info("尝试从页面HTML提取video_id...")
            extracted_id = self._extract_video_id_from_page(page_url)

            if extracted_id:
                self.logger.info(f"成功提取video_id: {extracted_id}")
                return self._fetch_m3u8_by_id(extracted_id)

            # 策略6: 尝试直接M3U8 URL作为fallback
            if '.m3u8' in page_url.lower():
                self.logger.info("尝试直接解析M3U8 URL...")
                return self.parse_m3u8_direct(page_url)

            raise Exception(f"无法从URL提取M3U8信息: {page_url}")

        except Exception as e:
            self.logger.error(f"M3U8解析失败: {str(e)}", exc_info=True)
            raise

    def _extract_video_id_from_page(self, page_url):
        """
        从页面HTML提取视频ID

        Args:
            page_url: 页面URL

        Returns:
            str: 视频ID，失败返回None
        """
        try:
            self.logger.info(f"正在获取页面: {page_url}")
            response = self.session.get(page_url, timeout=self.timeout)

            # 记录响应状态
            self.logger.info(f"页面响应: status={response.status_code}, size={len(response.content)} bytes")

            if response.status_code == 403:
                self.logger.error("403 Forbidden - 页面拒绝访问，可能需要登录或Cookie")
                return None
            elif response.status_code == 404:
                self.logger.error(f"404 Not Found - 页面不存在: {page_url}")
                return None

            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")
            video_elements = soup.find_all("div", class_="thumb-overlay")

            self.logger.info(f"找到 {len(video_elements)} 个视频元素")

            if not video_elements:
                # 尝试备用选择器
                self.logger.info("尝试备用选择器...")
                video_elements = soup.select("[id*=video]")
                self.logger.info(f"备用选择器找到 {len(video_elements)} 个元素")

            for elem in video_elements:
                elem_id = elem.get("id")
                if elem_id:
                    # 查找6位以上的数字ID
                    match = re.search(r"\d{6,}", elem_id)
                    if match:
                        video_id = match.group(0)
                        self.logger.info(f"提取到video_id: {video_id}")
                        return video_id

            self.logger.warning("未能从页面提取到video_id")
            return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"获取页面失败: {type(e).__name__}: {e}")
            return None
        except Exception as e:
            self.logger.warning(f"提取video_id失败: {str(e)}")
            return None

    def _extract_direct_mp4_url(self, page_url):
        """
        从页面HTML中提取直接的MP4视频URL

        Args:
            page_url: 页面URL

        Returns:
            str: MP4视频URL，失败返回None
        """
        try:
            self.logger.info(f"正在获取页面以提取MP4 URL: {page_url}")
            response = self.session.get(page_url, timeout=self.timeout)

            # 记录响应状态
            self.logger.info(f"页面响应: status={response.status_code}, size={len(response.content)} bytes")

            if response.status_code == 403:
                self.logger.error("403 Forbidden - 页面拒绝访问，可能需要登录或Cookie")
                return None
            elif response.status_code == 404:
                self.logger.error(f"404 Not Found - 页面不存在: {page_url}")
                return None

            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")

            # 方法1: 查找<video>标签的src属性
            video_tags = soup.find_all("video")
            self.logger.info(f"找到 {len(video_tags)} 个video标签")

            for video in video_tags:
                src = video.get("src")
                if src and ".mp4" in src.lower():
                    self.logger.info(f"从video标签提取到MP4 URL: {src}")
                    return src

            # 方法2: 查找<source>标签的src属性
            source_tags = soup.find_all("source")
            self.logger.info(f"找到 {len(source_tags)} 个source标签")

            for source in source_tags:
                src = source.get("src")
                if src and ".mp4" in src.lower():
                    self.logger.info(f"从source标签提取到MP4 URL: {src}")
                    return src

            # 方法3: 使用正则表达式搜索HTML中的MP4 URL
            mp4_pattern = re.compile(r'https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*')
            mp4_matches = mp4_pattern.findall(response.text)

            if mp4_matches:
                self.logger.info(f"通过正则表达式找到 {len(mp4_matches)} 个MP4 URL")
                # 返回第一个找到的MP4 URL
                self.logger.info(f"使用第一个MP4 URL: {mp4_matches[0]}")
                return mp4_matches[0]

            self.logger.warning("未能从页面提取到MP4 URL")
            return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"获取页面失败: {type(e).__name__}: {e}")
            return None
        except Exception as e:
            self.logger.warning(f"提取MP4 URL失败: {str(e)}")
            return None

    def _fetch_m3u8_by_id(self, video_id):
        """
        使用video_id获取M3U8信息

        Args:
            video_id: 视频ID

        Returns:
            dict: M3U8信息
        """
        m3u8_url = f"{self.m3u8_cdn_base}/m3u8/{video_id}/{video_id}.m3u8"
        self.logger.info(f"正在获取M3U8文件: {m3u8_url}")

        m3u8_text = self._request_content(m3u8_url, is_text=True, max_retries=3)

        if not m3u8_text:
            raise Exception(f"无法获取M3U8文件内容 (可能已被删除或URL不正确)")

        # 解析TS片段
        ts_list = re.findall(r"(.+?\.ts)", m3u8_text)

        if not ts_list:
            self.logger.warning("未找到.ts片段，尝试.m4s格式...")
            ts_list = re.findall(r"(.*?\.m4s)", m3u8_text)

        if not ts_list:
            self.logger.error("M3U8文件中未找到任何视频片段")
            # 记录M3U8文件前500字符用于调试
            self.logger.debug(f"M3U8预览: {m3u8_text[:500]}")
            raise Exception("M3U8文件格式无效或为空")

        self.logger.info(f"成功解析M3U8: video_id={video_id}, 片段数={len(ts_list)}")

        return {
            'm3u8_url': m3u8_url,
            'video_id': video_id,
            'ts_count': len(ts_list),
            'title': f'Video_{video_id}',
            'ts_list': ts_list
        }

    def parse_m3u8_direct(self, m3u8_url):
        """
        直接解析M3U8文件URL

        Args:
            m3u8_url: M3U8文件URL

        Returns:
            dict: 包含M3U8信息的字典
        """
        self.logger.info(f"开始解析M3U8文件: {m3u8_url}")

        try:
            m3u8_text = self._request_content(m3u8_url, is_text=True)

            if not m3u8_text:
                raise Exception("无法获取M3U8文件内容")

            # 解析TS文件列表
            ts_list = re.findall(r"(.+?\.ts)", m3u8_text)

            if not ts_list:
                # 尝试匹配其他格式的片段
                ts_list = re.findall(r"(.*?\.m4s)", m3u8_text)

            self.logger.info(f"成功解析M3U8: TS片段数={len(ts_list)}")

            # 提取基础URL
            base_url = m3u8_url.rsplit('/', 1)[0] + '/'

            return {
                'm3u8_url': m3u8_url,
                'base_url': base_url,
                'ts_count': len(ts_list),
                'title': f'M3U8_{int(time.time())}',
                'ts_list': ts_list
            }

        except Exception as e:
            self.logger.error(f"解析M3U8失败: {str(e)}", exc_info=True)
            raise Exception(f"解析M3U8失败: {str(e)}")

    def download_m3u8_video(self, m3u8_info, output_path='.', merge=True):
        """
        下载M3U8视频

        Args:
            m3u8_info: M3U8信息字典（从parse方法返回）
            output_path: 保存路径
            merge: 是否合并TS文件为MP4

        Returns:
            dict: 下载结果
        """
        video_id = m3u8_info.get('video_id', 'unknown')
        ts_list = m3u8_info.get('ts_list', [])
        m3u8_url = m3u8_info.get('m3u8_url', '')
        base_url = m3u8_info.get('base_url', '')

        self.logger.info(f"开始下载M3U8视频: {video_id}")
        self.logger.info(f"保存路径: {output_path}")
        self.logger.info(f"TS片段数: {len(ts_list)}")

        # 确保输出路径存在
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        # 创建临时文件夹存放TS文件
        temp_folder = os.path.join(output_path, f"{video_id}_temp")
        if not os.path.exists(temp_folder):
            os.makedirs(temp_folder)

        total_ts = len(ts_list)
        downloaded_ts = 0
        failed_ts = []
        output_file = None

        try:
            # 下载所有TS片段
            for index, ts_file in enumerate(ts_list, 1):
                ts_filename = os.path.join(temp_folder, f"{ts_file}")

                # 构造TS文件URL
                if base_url:
                    ts_url = base_url + ts_file
                else:
                    # 使用CDN基础URL（可配置）
                    ts_url = f"{self.m3u8_cdn_base}/m3u8/{video_id}/{ts_file}"

                try:
                    self.logger.info(f"正在下载 [{index}/{total_ts}]: {ts_file}")

                    # 更新进度
                    progress_percentage = (index - 1) / total_ts * 100
                    self.progress_handler.progress_hook({
                        'downloaded_bytes': index - 1,
                        'total_bytes': total_ts,
                        'status': 'downloading',
                        'speed': 'N/A',
                        'eta': 'N/A'
                    })

                    content = self._request_content(ts_url)

                    if content:
                        # 保存TS文件
                        with open(ts_filename, "wb") as f:
                            f.write(content)

                        downloaded_ts += 1
                        self.logger.info(f"下载完成 [{index}/{total_ts}]: {ts_file}")

                        # 随机延迟，避免请求过快被封（使用配置的延迟时间）
                        sleep_time = random.uniform(self.delay_min, self.delay_max)
                        time.sleep(sleep_time)
                    else:
                        failed_ts.append(ts_file)
                        self.logger.warning(f"下载失败: {ts_file}")

                except Exception as e:
                    failed_ts.append(ts_file)
                    self.logger.error(f"下载TS文件失败 [{ts_file}]: {str(e)}")

            # 更新完成进度
            self.progress_handler.progress_hook({
                'downloaded_bytes': total_ts,
                'total_bytes': total_ts,
                'status': 'finished',
                'speed': 'N/A',
                'eta': 'N/A'
            })

            # 合并TS文件
            if merge and downloaded_ts > 0:
                output_file = os.path.join(output_path, f"{video_id}.mp4")
                self._merge_ts_files(temp_folder, output_file, ts_list)

        finally:
            # 无论成功失败，都清理临时文件（仅在merge=True时）
            if merge and os.path.exists(temp_folder):
                try:
                    import shutil
                    shutil.rmtree(temp_folder)
                    self.logger.info(f"已清理临时文件夹: {temp_folder}")
                except Exception as e:
                    self.logger.warning(f"清理临时文件夹失败: {str(e)}")

        return {
            'success': len(failed_ts) == 0,
            'video_id': video_id,
            'downloaded': downloaded_ts,
            'total': total_ts,
            'failed': failed_ts,
            'output_file': output_file if merge else temp_folder
        }

    def _request_content(self, url, is_text=False, max_retries=3):
        """
        请求URL内容（带增强重试机制和详细日志）

        Args:
            url: 请求的URL
            is_text: 是否返回文本内容
            max_retries: 最大重试次数（默认3次）

        Returns:
            内容或None
        """
        for attempt in range(max_retries + 1):
            try:
                self.logger.info(f"请求 {url} (尝试 {attempt + 1}/{max_retries + 1})")

                # 如果设置了自定义Cookie，在请求头中添加
                headers = {}
                if self.custom_cookie:
                    headers['Cookie'] = self.custom_cookie
                    self.logger.debug("使用自定义Cookie")

                response = self.session.get(url, timeout=self.timeout, headers=headers)

                # 详细记录响应信息
                self.logger.info(
                    f"响应: status={response.status_code}, "
                    f"size={len(response.content)} bytes, "
                    f"encoding={response.encoding}"
                )

                # 根据状态码提供详细诊断
                if response.status_code == 403:
                    self.logger.error("403 Forbidden - 网站可能需要特定的请求头或Cookie")
                    self.logger.debug(f"响应头: {dict(response.headers)}")
                elif response.status_code == 404:
                    self.logger.error(f"404 Not Found - URL可能无效: {url}")
                elif response.status_code >= 500:
                    self.logger.warning(f"服务器错误 {response.status_code} - 将重试")

                if response.status_code == 200:
                    return response.text if is_text else response.content

                # 非200状态码，判断是否应该重试
                if response.status_code in (429, 500, 502, 503, 504):
                    if attempt < max_retries:
                        delay = min(2 ** attempt, 30)  # 指数退避，最大30秒
                        self.logger.info(f"等待 {delay:.1f}秒后重试...")
                        time.sleep(delay)
                        continue

                response.raise_for_status()

            except requests.exceptions.Timeout:
                self.logger.warning(f"请求超时 ({self.timeout}s) - 尝试 {attempt + 1}/{max_retries + 1}")
            except requests.exceptions.ConnectionError as e:
                self.logger.warning(f"连接错误: {e}")
            except Exception as e:
                self.logger.error(f"请求失败: {type(e).__name__}: {e}")

            # 使用指数退避进行重试
            if attempt < max_retries:
                delay = min(2 ** attempt, 30)  # 2s, 4s, 8s, 16s, 30s...
                self.logger.info(f"等待 {delay:.1f}秒后重试...")
                time.sleep(delay)

        self.logger.error(f"请求失败，已尝试 {max_retries + 1} 次: {url}")
        return None

    def _merge_ts_files(self, temp_folder, output_file, ts_list):
        """
        合并TS文件为MP4

        Args:
            temp_folder: 临时文件夹路径
            output_file: 输出文件路径
            ts_list: TS文件列表
        """
        self.logger.info(f"开始合并TS文件到: {output_file}")

        try:
            # 方式1: 使用二进制合并
            with open(output_file, "wb") as merged:
                for ts_file in ts_list:
                    ts_path = os.path.join(temp_folder, ts_file)
                    if os.path.exists(ts_path):
                        with open(ts_path, "rb") as ts:
                            merged.write(ts.read())

            self.logger.info(f"TS文件合并完成: {output_file}")

            # 尝试使用ffmpeg转换为标准MP4格式
            self._convert_to_mp4(output_file)

        except Exception as e:
            self.logger.error(f"合并TS文件失败: {str(e)}", exc_info=True)
            raise

    def _convert_to_mp4(self, ts_file):
        """
        使用ffmpeg将TS文件转换为MP4

        Args:
            ts_file: TS文件路径
        """
        try:
            import subprocess

            mp4_file = ts_file.rsplit('.', 1)[0] + '_converted.mp4'

            # 检查ffmpeg是否可用
            try:
                subprocess.run(
                    ['ffmpeg', '-version'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True
                )

                # 使用ffmpeg转换
                cmd = [
                    'ffmpeg', '-i', ts_file,
                    '-c', 'copy',
                    '-bsf:a', 'aac_adtstoasc',
                    mp4_file,
                    '-y'  # 覆盖输出文件
                ]

                self.logger.info(f"使用ffmpeg转换视频: {' '.join(cmd)}")

                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True
                )

                # 如果转换成功，替换原文件
                if os.path.exists(mp4_file):
                    import shutil
                    shutil.move(mp4_file, ts_file)
                    self.logger.info(f"ffmpeg转换成功")

            except (subprocess.CalledProcessError, FileNotFoundError):
                self.logger.warning("ffmpeg不可用或转换失败，保持原始TS格式")

        except Exception as e:
            self.logger.warning(f"视频转换失败: {str(e)}")

    def get_video_ids_from_page(self, page_url):
        """
        从页面获取所有视频ID列表

        Args:
            page_url: 页面URL

        Returns:
            list: 视频ID列表
        """
        self.logger.info(f"开始获取页面视频ID列表: {page_url}")

        try:
            response = self.session.get(page_url, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")
            video_id_list = soup.find_all("div", class_="thumb-overlay")

            result = []
            for video_id_element in video_id_list:
                id_attr = video_id_element.get("id")
                if id_attr:
                    match = re.findall(r"\d+", id_attr)
                    if match:
                        result.append(match[0])

            self.logger.info(f"找到 {len(result)} 个视频ID")
            return result

        except Exception as e:
            self.logger.error(f"获取视频ID列表失败: {str(e)}", exc_info=True)
            raise Exception(f"获取视频ID列表失败: {str(e)}")
