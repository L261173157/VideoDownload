"""进度处理模块"""


class ProgressHandler:
    """下载进度处理器"""

    def __init__(self):
        self.progress_callback = None

    def set_callback(self, callback):
        """
        设置进度回调函数

        Args:
            callback: 回调函数，接收参数 (downloaded_bytes, total_bytes, percentage, speed, eta)
        """
        self.progress_callback = callback

    def progress_hook(self, d):
        """
        yt-dlp进度钩子函数

        Args:
            d: yt-dlp进度字典
        """
        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)

            # 计算进度百分比
            if total > 0:
                percentage = (downloaded / total) * 100
            else:
                percentage = 0

            # 获取下载速度和ETA
            speed = d.get('speed', 0)
            eta = d.get('eta', 0)

            # 格式化信息
            speed_str = self._format_speed(speed)
            eta_str = self._format_time(eta)
            size_str = self._format_bytes(downloaded, total)

            # 调用回调函数
            if self.progress_callback:
                self.progress_callback(downloaded, total, percentage, speed_str, eta_str, size_str)

        elif d['status'] == 'finished':
            # 下载完成
            if self.progress_callback:
                self.progress_callback(0, 0, 100, '完成', '完成', '完成')

    def _format_bytes(self, downloaded, total):
        """格式化字节数"""
        def format_size(bytes):
            for unit in ['B', 'KB', 'MB', 'GB']:
                if bytes < 1024.0:
                    return f"{bytes:.2f} {unit}"
                bytes /= 1024.0
            return f"{bytes:.2f} TB"

        if total > 0:
            return f"{format_size(downloaded)} / {format_size(total)}"
        return format_size(downloaded)

    def _format_speed(self, speed):
        """格式化下载速度"""
        if speed is None or speed == 0:
            return "N/A"

        for unit in ['B/s', 'KB/s', 'MB/s', 'GB/s']:
            if speed < 1024.0:
                return f"{speed:.2f} {unit}"
            speed /= 1024.0
        return f"{speed:.2f} TB/s"

    def _format_time(self, seconds):
        """格式化时间（ETA）"""
        if seconds == 0 or seconds is None:
            return "N/A"

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
