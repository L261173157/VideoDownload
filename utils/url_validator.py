"""URL验证工具模块"""

import re


class URLValidator:
    """URL验证器"""

    def __init__(self):
        # 基本的URL正则表达式
        self.url_pattern = re.compile(
            r'^https?://'  # http:// 或 https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # 域名
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP地址
            r'(?::\d+)?'  # 端口
            r'(?:/?|[/?]\S+)$', re.IGNORECASE
        )

    def is_valid_url(self, url):
        """
        验证URL格式是否合法

        Args:
            url: 要验证的URL字符串

        Returns:
            bool: URL是否合法
        """
        if not url or not isinstance(url, str):
            return False

        url = url.strip()
        return bool(self.url_pattern.match(url))

    def normalize_url(self, url):
        """
        规范化URL（移除多余空格，确保http/https前缀）

        Args:
            url: 要规范化的URL字符串

        Returns:
            str: 规范化后的URL
        """
        if not url or not isinstance(url, str):
            return ""

        url = url.strip()

        # 如果没有协议前缀，添加 https://
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        return url

    def is_m3u8_url(self, url):
        """
        检测URL是否为M3U8链接

        Args:
            url: 要检测的URL字符串

        Returns:
            bool: 是否为M3U8链接
        """
        if not url or not isinstance(url, str):
            return False

        url = url.lower()
        return '.m3u8' in url or url.endswith('.m3u8')

    def is_m3u8_page(self, url):
        """
        检测URL是否可能是包含M3U8视频的页面
        (例如某些成人网站、视频网站)

        Args:
            url: 要检测的URL字符串

        Returns:
            bool: 是否可能是M3U8页面
        """
        if not url or not isinstance(url, str):
            return False

        # 已知的M3U8视频站点域名模式
        m3u8_domains = [
            '91porn',
            'killcovid2021'
        ]

        url_lower = url.lower()
        return any(domain in url_lower for domain in m3u8_domains)
