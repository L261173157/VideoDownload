"""视频下载器 - 主程序入口

这是一个基于 yt-dlp 的桌面视频下载应用程序
支持 YouTube, B站, 抖音等 1000+ 视频网站
"""

import tkinter as tk
from gui.main_window import MainWindow


def main():
    """主函数"""
    # 创建主窗口
    root = tk.Tk()

    # 设置窗口图标（可选）
    # root.iconbitmap('icon.ico')

    # 创建应用实例
    app = MainWindow(root)

    # 设置窗口居中
    center_window(root, 700, 650)

    # 启动主事件循环
    root.mainloop()


def center_window(window, width, height):
    """
    将窗口居中显示

    Args:
        window: 窗口对象
        width: 窗口宽度
        height: 窗口高度
    """
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    x = (screen_width - width) // 2
    y = (screen_height - height) // 2

    window.geometry(f'{width}x{height}+{x}+{y}')


if __name__ == '__main__':
    main()
