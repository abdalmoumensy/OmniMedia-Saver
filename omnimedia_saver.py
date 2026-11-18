import ctypes, os, queue, shutil, subprocess, sys, threading
import customtkinter as ctk
from tkinter import filedialog

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

APP_NAME = "OmniMedia Saver"
APP_VERSION = "2.0.0"
APP_ID = "omnimedia.saver.desktop.1"
ICON_FILE = "app_icon.ico"

if sys.platform == "win32":
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

BG_TOP, CARD, CARD_2, BORDER = "#05060b", "#0e1018", "#171a26", "#272b3d"
ACCENT, ACCENT_DEEP, TEXT, MUTED, GOOD, BAD = "#8b5cf6", "#6d4ce0", "#eceef6", "#8a90a6", "#34d399", "#fb7185"

QUALITIES = {
    "Best": {"format": "bestvideo+bestaudio/best"},
    "1080p": {"format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]"},
    "720p": {"format": "bestvideo[height<=720]+bestaudio/best[height<=720]"},
    "480p": {"format": "bestvideo[height<=480]+bestaudio/best[height<=480]"},
    "MP3": {
        "format": "bestaudio/best",
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
    },
}

def resource_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)

def find_ffmpeg():
    on_path = shutil.which("ffmpeg")
    if on_path:
        return on_path
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None

class Cancelled(Exception):
    pass

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("760x540")
        self.configure(fg_color=BG_TOP)
        self.resizable(False, False)
        ico = resource_path(ICON_FILE)
        if os.path.isfile(ico):
            try:
                self.iconbitmap(ico)
            except Exception:
                pass

        self.folder = os.path.join(os.path.expanduser("~"), "Downloads")
        self.quality = "Best"
        self.downloading = False
        self.cancel_flag = False
        self.q = queue.Queue()

        hdr = ctk.CTkLabel(self, text=APP_NAME, font=ctk.CTkFont(size=24, weight="bold"), text_color=TEXT)
        hdr.pack(pady=(18, 4))
        sub = ctk.CTkLabel(self, text="Paste a link, pick your quality, and download.", text_color=MUTED)
        sub.pack(pady=(0, 12))

        url_card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
        url_card.pack(fill="x", padx=24, pady=6)
        self.url_entry = ctk.CTkEntry(url_card, placeholder_text="https:// video or audio link...", height=40, fg_color=CARD_2, text_color=TEXT)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(12, 6), pady=12)
        ctk.CTkButton(url_card, text="Paste", width=72, height=40, fg_color=ACCENT, hover_color=ACCENT_DEEP, command=self.paste).pack(side="left", padx=4)
        ctk.CTkButton(url_card, text="Clear", width=64, height=40, fg_color=CARD_2, command=lambda: self.url_entry.delete(0, "end")).pack(side="left", padx=(4, 12))

        opts_card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
        opts_card.pack(fill="x", padx=24, pady=6)
        q_row = ctk.CTkFrame(opts_card, fg_color="transparent")
        q_row.pack(fill="x", padx=12, pady=(12, 6))
        self.q_btns = {}
        for k in QUALITIES:
            b = ctk.CTkButton(q_row, text=k, width=120, height=34, command=lambda key=k: self.set_q(key))
            b.pack(side="left", padx=4, expand=True)
            self.q_btns[k] = b
        self.set_q("Best")

        self.folder_btn = ctk.CTkButton(opts_card, text=f"Save to: {self.folder}", fg_color=CARD_2, text_color=TEXT, anchor="w", command=self.pick_folder)
        self.folder_btn.pack(fill="x", padx=12, pady=(4, 12))

        prog_card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
        prog_card.pack(fill="x", padx=24, pady=6)
        self.status_lbl = ctk.CTkLabel(prog_card, text="Ready", font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT)
        self.status_lbl.pack(pady=(12, 4))
        self.pbar = ctk.CTkProgressBar(prog_card, progress_color=ACCENT)
        self.pbar.pack(fill="x", padx=20, pady=8)
        self.pbar.set(0)
        self.detail_lbl = ctk.CTkLabel(prog_card, text="Waiting for link...", text_color=MUTED)
        self.detail_lbl.pack(pady=(0, 12))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=12)
        self.dl_btn = ctk.CTkButton(btn_row, text="Download", height=46, fg_color=ACCENT, hover_color=ACCENT_DEEP, font=ctk.CTkFont(size=16, weight="bold"), command=self.start)
        self.dl_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.cn_btn = ctk.CTkButton(btn_row, text="Cancel", width=110, height=46, fg_color=CARD_2, state="disabled", command=self.cancel)
        self.cn_btn.pack(side="left")

        self.after(50, self._poll)

    def _poll(self):
        try:
            while True:
                self.q.get_nowait()()
        except queue.Empty:
            pass
        self.after(50, self._poll)

    def paste(self):
        try:
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, self.clipboard_get().strip())
        except Exception:
            pass

    def set_q(self, key):
        self.quality = key
        for k, b in self.q_btns.items():
            b.configure(fg_color=ACCENT if k == key else CARD_2)

    def pick_folder(self):
        d = filedialog.askdirectory(initialdir=self.folder)
        if d:
            self.folder = d
            self.folder_btn.configure(text=f"Save to: {self.folder}")

    def start(self):
        url = self.url_entry.get().strip()
        if not url or self.downloading:
            return
        self.downloading, self.cancel_flag = True, False
        self.dl_btn.configure(state="disabled", text="Downloading...")
        self.cn_btn.configure(state="normal")
        self.pbar.set(0)
        self.status_lbl.configure(text="Starting...", text_color=TEXT)
        threading.Thread(target=self._run, args=(url,), daemon=True).start()

    def cancel(self):
        self.cancel_flag = True

    def _hook(self, d):
        if self.cancel_flag:
            raise Cancelled()
        if d.get("status") == "downloading":
            tot = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes", 0)
            frac = (done / tot) if tot else 0.0
            spd = d.get("speed")
            txt = f"{done/1048576:.1f} MB ({spd/1048576:.2f} MB/s)" if spd else f"{done/1048576:.1f} MB"
            self.q.put(lambda: (self.pbar.set(frac), self.status_lbl.configure(text=f"Downloading ({int(frac*100)}%)"), self.detail_lbl.configure(text=txt)))

    def _run(self, url):
        try:
            import yt_dlp
            choice = QUALITIES[self.quality]
            opts = {
                "format": choice["format"],
                "outtmpl": os.path.join(self.folder, "%(title)s.%(ext)s"),
                "noplaylist": True,
                "merge_output_format": "mp4",
                "progress_hooks": [self._hook],
                "quiet": True,
            }
            ff = find_ffmpeg()
            if ff:
                opts["ffmpeg_location"] = ff
                if "postprocessors" in choice:
                    opts["postprocessors"] = choice["postprocessors"]
                    opts.pop("merge_output_format", None)
            else:
                opts.pop("merge_output_format", None)
                opts["format"] = "bestaudio/best" if "postprocessors" in choice else "best[ext=mp4]/best"
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
            title = (info or {}).get("title") or "Saved media"
            self.q.put(lambda: self._finish("Done!", GOOD, 1.0, f"Saved: {title[:55]}"))
        except Exception as e:
            msg = "Cancelled" if self.cancel_flag or isinstance(e, Cancelled) else "Failed"
            self.q.put(lambda: self._finish(msg, BAD, 0.0, str(e)[:65]))

    def _finish(self, st, col, prog, det):
        self.downloading = False
        self.dl_btn.configure(state="normal", text="Download")
        self.cn_btn.configure(state="disabled")
        self.pbar.set(prog)
        self.status_lbl.configure(text=st, text_color=col)
        self.detail_lbl.configure(text=det)

if __name__ == "__main__":
    App().mainloop()
