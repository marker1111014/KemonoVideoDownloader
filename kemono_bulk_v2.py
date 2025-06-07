import sys
import os
import re
import requests
from urllib.parse import urljoin, urlparse, unquote
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit,
                               QPushButton, QTextEdit, QFileDialog, QProgressBar, QMessageBox,
                               QListWidget, QListWidgetItem, QAbstractItemView, QHBoxLayout)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QTextCursor
from bs4 import BeautifulSoup

# ------------ 工具方法區 ------------
def clean_filename(s):
    return re.sub(r'[<>:"/\\|?*]', '_', s)

def parse_published_date(soup):
    tag = soup.find(class_='post__published')
    if tag and tag.text:
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})', tag.text)
        if match:
            y, m, d = match.groups()
            y = y[-2:]
            return f"{y}.{int(m)}.{int(d)}"
    return "unknown_date"

def find_chromium_path():
    base = getattr(sys, '_MEIPASS', os.path.dirname(__file__))
    ms_path = os.path.join(base, 'ms-playwright')
    if os.path.exists(ms_path):
        for root, dirs, files in os.walk(ms_path):
            if 'chrome.exe' in files:
                return os.path.join(root, 'chrome.exe')
    return None

def get_video_links_and_names_with_date(url, extensions=('.mp4', '.mov')):
    from playwright.sync_api import sync_playwright
    chromium_path = find_chromium_path()
    if not chromium_path or not os.path.exists(chromium_path):
        raise Exception("未能自動找到chromium內核！請檢查打包時--add-data是否包含ms-playwright完整資料夾。")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, executable_path=chromium_path)
        page = browser.new_page()
        page.goto(url, timeout=60000)
        page.wait_for_timeout(5000)
        html = page.content()
        browser.close()
    soup = BeautifulSoup(html, 'html.parser')
    date_prefix = parse_published_date(soup)
    links_names = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if any(href.lower().endswith(ext) for ext in extensions):
            full_url = urljoin(url, href)
            filename = a.get('download', '').strip()
            if not filename:
                filename = a.get('title', '').strip()
            if not filename and "?" in href and "f=" in href:
                m = re.search(r'[?&]f=([^&]+)', href)
                if m:
                    filename = unquote(m.group(1))
            if not filename:
                name_span = a.find(['span', 'div'], class_='post__attachment-name')
                if name_span and name_span.text.strip():
                    filename = name_span.text.strip()
            if not filename:
                filename = os.path.basename(urlparse(full_url).path)
            full_file_name = f"{date_prefix} {filename}"
            links_names.append((full_url, full_file_name))
    return links_names

# ------------ 子線程區 ------------
class AnalyzeThread(QThread):
    finished = Signal(list, str)  # (links_and_names, error_msg)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            links_and_names = get_video_links_and_names_with_date(self.url)
            self.finished.emit(links_and_names, "")
        except Exception as e:
            self.finished.emit([], str(e))

class DownloadThread(QThread):
    progress = Signal(int)
    log = Signal(str)
    finished = Signal(str)

    def __init__(self, links, save_dir):
        super().__init__()
        self.links = links  # List of (url, filename)
        self.save_dir = save_dir

    def run(self):
        if not self.links:
            self.log.emit("未選中任何影片！")
            self.finished.emit("未選中任何影片！")
            return
        self.log.emit(f"預備下載 {len(self.links)} 個影片...")
        try:
            for i, (down_url, fn) in enumerate(self.links, 1):
                fn = clean_filename(fn)
                save_path = os.path.join(self.save_dir, fn)
                self.log.emit(f"正在下載({i}/{len(self.links)})：{fn}")
                headers = {'User-Agent': 'Mozilla/5.0'}
                with requests.get(down_url, headers=headers, stream=True) as r:
                    r.raise_for_status()
                    total = int(r.headers.get('content-length', 0))
                    with open(save_path, 'wb') as f:
                        downloaded = 0
                        for chunk in r.iter_content(chunk_size=1024 * 64):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total > 0:
                                    percent = int(downloaded / total * 100)
                                    self.progress.emit(percent)
                self.log.emit(f"{fn} 下載完成。\n")
            self.finished.emit("全部下載完成！")
        except Exception as e:
            self.log.emit(f"出錯：{e}")
            self.finished.emit("任務異常終止")

# ------------ 主窗體 ------------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kemono 視頻下載器")
        self.setFixedWidth(600)
        self.setFixedHeight(600)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("請輸入Kemono貼文連結："))
        hl_url = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("貼上連結後點擊「分析」")
        hl_url.addWidget(self.input)
        self.btn_analyze = QPushButton("分析")
        hl_url.addWidget(self.btn_analyze)
        layout.addLayout(hl_url)
        self.loading_label = QLabel("", self)
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setFixedHeight(30)
        layout.addWidget(self.loading_label)
        self.list_label = QLabel("可勾選要下載的影片：")
        self.list_label.setVisible(False)
        layout.addWidget(self.list_label)
        self.video_list = QListWidget()
        self.video_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.video_list.setVisible(False)
        layout.addWidget(self.video_list, stretch=1)
        btn_layout = QHBoxLayout()
        self.path_label = QLabel(f"保存位置：{os.getcwd()}")
        self.path_label.setStyleSheet('font-size:13px;color:gray')
        self.btn_chgdir = QPushButton("更改保存文件夾")
        btn_layout.addWidget(self.btn_chgdir)
        btn_layout.addWidget(self.path_label)
        layout.addLayout(btn_layout)
        self.btn_start = QPushButton("開始下載")
        self.btn_start.setEnabled(False)
        layout.addWidget(self.btn_start)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        layout.addWidget(QLabel("下載日誌："))
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        layout.addWidget(self.text)

        self.save_dir = os.getcwd()
        self.all_links = []
        self.btn_chgdir.clicked.connect(self.choose_dir)
        self.btn_analyze.clicked.connect(self.start_analyze)
        self.input.returnPressed.connect(self.start_analyze)
        self.btn_start.clicked.connect(self.download_selected)
        self.down_thread = None
        self.analyze_thread = None

    def log(self, msg):
        self.text.append(msg)
        self.text.moveCursor(QTextCursor.End)

    def choose_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "選擇下載目錄", self.save_dir)
        if directory:
            self.save_dir = directory
            self.path_label.setText(f"保存位置：{directory}")

    def start_analyze(self):
        url = self.input.text().strip()
        if not url:
            QMessageBox.warning(self, "提示", "請填寫 Kemono 貼文連結")
            return
        self.log(f"正在分析：{url}")
        self.list_label.setVisible(False)
        self.video_list.setVisible(False)
        self.loading_label.setText("<b><font color='#69aaff'>分析中...請稍候</font></b>")
        self.btn_analyze.setEnabled(False)
        self.analyze_thread = AnalyzeThread(url)
        self.analyze_thread.finished.connect(self.on_analyze_done)
        self.analyze_thread.start()

    def on_analyze_done(self, links_and_names, err):
        self.loading_label.setText("")
        self.btn_analyze.setEnabled(True)
        self.video_list.clear()
        if err:
            self.btn_start.setEnabled(False)
            self.log(f"分析發生錯誤：{err}")
            return
        self.all_links = links_and_names
        if not links_and_names:
            self.btn_start.setEnabled(False)
            self.log('未找到任何可下載視頻。')
            return
        self.list_label.setVisible(True)
        self.video_list.setVisible(True)
        for v_url, v_name in links_and_names:
            item = QListWidgetItem(v_name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            item.setData(Qt.UserRole, v_url)
            self.video_list.addItem(item)
        self.btn_start.setEnabled(True)
        self.log(f"共找到 {len(links_and_names)} 部影片，請勾選要下載的。")

    def download_selected(self):
        selected = []
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            if item.checkState() == Qt.Checked:
                v_url = item.data(Qt.UserRole)
                v_name = item.text()
                selected.append((v_url, v_name))
        if not selected:
            QMessageBox.warning(self, "提示", "未勾選任何影片！")
            return
        self.btn_start.setEnabled(False)
        self.progress_bar.setValue(0)
        self.text.clear()
        self.down_thread = DownloadThread(selected, self.save_dir)
        self.down_thread.progress.connect(self.progress_bar.setValue)
        self.down_thread.log.connect(self.log)
        self.down_thread.finished.connect(self.end_download)
        self.down_thread.start()

    def end_download(self, final_msg):
        self.btn_start.setEnabled(True)
        self.progress_bar.setValue(100)
        self.log(final_msg)

# --- 暗色現代風格表 ---
DARK_STYLE = """
QWidget {
    background: #22242b;
    font-family: 'Segoe UI', 'Arial', sans-serif;
    color: #ddd;
}
QLabel {
    color: #cfcfcf;
}
QLineEdit, QTextEdit {
    background: #31323b;
    border: 1.2px solid #474860;
    border-radius: 7px;
    padding: 6px;
    color: #eee;
    font-size: 14px;
}
QLineEdit::placeholder {
    color: #69697a;
}
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3e4452, stop:1 #262936);
    border: 0.5px solid #2d2f3a;
    border-radius: 9px;
    padding: 7px 0;
    font-size: 14px;
    font-weight: 500;
    color: #baccfa;
    min-width: 90px;
    margin: 2px;
    letter-spacing: 0.2px;
}
QPushButton:hover {
    background: #455073;
    color: #69aaff;
}
QPushButton:pressed {
    background: #21354a;
}
QProgressBar {
    background: #22242b;
    border-radius: 6px;
    height: 18px;
    font-size: 12px;
}
QProgressBar::chunk {
    border-radius: 6px;
    background-color: #2471f2;
}
"""

if __name__ == '__main__':
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLE)
    wnd = MainWindow()
    wnd.show()
    app.exec()