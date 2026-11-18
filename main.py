import math, os, queue, shutil, threading
from kivy.app import App
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.utils import get_color_from_hex, platform
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

if platform not in ("android", "ios"):
    Window.size = (400, 780)

APP_NAME = "OmniMedia Saver"
BG_TOP, CARD, CARD_2, CARD_3 = "#05060b", "#0e1018", "#171a26", "#1f2333"
BORDER, TRACK, ACCENT, ACCENT_SOFT = "#272b3d", "#1a1d2a", "#8b5cf6", "#c4b5fd"
TEXT, MUTED, GOOD, BAD, WARN = "#eceef6", "#8a90a6", "#34d399", "#fb7185", "#fbbf24"

QUALITIES = {
    "Best": {"f": "best[ext=mp4]/best"},
    "1080p": {"f": "best[height<=1080][ext=mp4]/best[height<=1080]/best"},
    "720p": {"f": "best[height<=720][ext=mp4]/best[height<=720]/best"},
    "480p": {"f": "best[height<=480][ext=mp4]/best[height<=480]/best"},
    "Audio": {"f": "bestaudio[ext=m4a]/bestaudio/best"},
}
CHIPS = ["Best", "1080p", "720p", "480p", "Audio"]

def rgba(h, a=1.0):
    c = get_color_from_hex(h)
    return (c[0], c[1], c[2], a)

def resolve_folder():
    if platform == "android":
        try:
            from android.permissions import Permission, request_permissions
            request_permissions([Permission.INTERNET, Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])
            from android.storage import primary_external_storage_path
            p = os.path.join(primary_external_storage_path(), "Download", "OmniMediaSaver")
            os.makedirs(p, exist_ok=True)
            return p
        except Exception:
            if os.path.isdir("/storage/emulated/0/Download"):
                return "/storage/emulated/0/Download"
    p = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(p, exist_ok=True)
    return p

class Cancelled(Exception):
    pass

class CardBox(BoxLayout):
    def __init__(self, bg_hex=CARD, radius=16, **kw):
        super().__init__(**kw)
        self.r = dp(radius)
        with self.canvas.before:
            Color(*rgba(bg_hex))
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.r])
            Color(*rgba(BORDER))
            self._line = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, self.r), width=dp(1))
        self.bind(pos=self._upd, size=self._upd)

    def _upd(self, *_):
        self._rect.pos, self._rect.size = self.pos, self.size
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, self.r)

class RingWidget(Widget):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.value, self.target, self.indeterminate, self.t = 0.0, 0.0, False, 0.0
        self.ring_color, self.sub_text = ACCENT, "READY"
        self.pct = Label(text="0%", font_size=sp(20), bold=True, color=rgba(TEXT))
        self.sub = Label(text="READY", font_size=sp(9), bold=True, color=rgba(MUTED))
        self.add_widget(self.pct)
        self.add_widget(self.sub)
        self.bind(pos=self._draw, size=self._draw)

    def step(self, dt):
        self.t += dt
        if not self.indeterminate:
            self.value += (self.target - self.value) * min(1.0, dt * 8.0)
            self.pct.text = f"{int(self.value * 100 + 0.5)}%"
        else:
            self.pct.text = "..."
        self.sub.text = self.sub_text
        self._draw()

    def _draw(self, *_):
        self.canvas.before.clear()
        cx, cy = self.center_x, self.center_y
        rad = (min(self.width, self.height) - dp(16)) / 2.0
        if rad <= 0:
            return
        self.pct.center = (cx, cy + dp(6))
        self.sub.center = (cx, cy - dp(15))
        with self.canvas.before:
            Color(*rgba(TRACK))
            Line(circle=(cx, cy, rad), width=dp(5))
            Color(*rgba(self.ring_color))
            s = (self.t * 220.0) % 360.0 if self.indeterminate else 0.0
            e = s + 110.0 if self.indeterminate else max(0.1, min(360.0, self.value * 360.0))
            Line(circle=(cx, cy, rad, s, e), width=dp(5), cap="round")

class MobileUI(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", padding=dp(14), spacing=dp(10), **kw)
        with self.canvas.before:
            Color(*rgba(BG_TOP))
            self._bg = RoundedRectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._bg, "pos", self.pos), size=lambda *_: setattr(self._bg, "size", self.size))
        self.q = queue.Queue()
        self.downloading, self.cancel_flag = False, False
        self.quality_key, self.folder = "Best", resolve_folder()

        hdr = BoxLayout(size_hint_y=None, height=dp(48))
        hdr.add_widget(Label(text=APP_NAME, font_size=sp(20), bold=True, color=rgba(TEXT), halign="left"))
        self.add_widget(hdr)

        c_url = CardBox(orientation="vertical", size_hint_y=None, height=dp(88), padding=dp(10), spacing=dp(6))
        c_url.add_widget(Label(text="PASTE MEDIA LINK", font_size=sp(10), bold=True, color=rgba(MUTED), size_hint_y=None, height=dp(16)))
        row = BoxLayout(spacing=dp(6), size_hint_y=None, height=dp(42))
        self.url_in = TextInput(hint_text="https://...", multiline=False, background_color=rgba(CARD_2), foreground_color=rgba(TEXT))
        b_paste = Button(text="Paste", size_hint_x=None, width=dp(64), background_normal="", background_color=rgba(ACCENT))
        b_paste.bind(on_release=lambda *_: setattr(self.url_in, "text", (Clipboard.paste() or "").strip()))
        b_clear = Button(text="Clear", size_hint_x=None, width=dp(54), background_normal="", background_color=rgba(CARD_3))
        b_clear.bind(on_release=lambda *_: setattr(self.url_in, "text", ""))
        row.add_widget(self.url_in)
        row.add_widget(b_paste)
        row.add_widget(b_clear)
        c_url.add_widget(row)
        self.add_widget(c_url)

        c_qual = CardBox(orientation="vertical", size_hint_y=None, height=dp(80), padding=dp(10), spacing=dp(6))
        chips_row = BoxLayout(spacing=dp(6), size_hint_y=None, height=dp(36))
        self.chips = {}
        for k in CHIPS:
            b = Button(text=k, background_normal="", background_color=rgba(CARD_2), bold=True)
            b.bind(on_release=lambda _b, key=k: self.sel_q(key))
            chips_row.add_widget(b)
            self.chips[k] = b
        c_qual.add_widget(chips_row)
        self.sel_q("Best")
        self.add_widget(c_qual)

        c_prog = CardBox(orientation="horizontal", size_hint_y=None, height=dp(140), padding=dp(10), spacing=dp(10))
        self.ring = RingWidget(size_hint_x=None, width=dp(116))
        c_prog.add_widget(self.ring)
        info_box = BoxLayout(orientation="vertical", spacing=dp(4))
        self.st_lbl = Label(text="Ready", font_size=sp(16), bold=True, color=rgba(TEXT))
        self.dt_lbl = Label(text="Paste a link and tap Download", font_size=sp(11), color=rgba(MUTED))
        info_box.add_widget(self.st_lbl)
        info_box.add_widget(self.dt_lbl)
        c_prog.add_widget(info_box)
        self.add_widget(c_prog)

        act = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        self.dl_btn = Button(text="Download", background_normal="", background_color=rgba(ACCENT), bold=True, font_size=sp(15))
        self.dl_btn.bind(on_release=lambda *_: self.start())
        self.cn_btn = Button(text="Cancel", size_hint_x=None, width=dp(92), background_normal="", background_color=rgba(CARD_3), disabled=True)
        self.cn_btn.bind(on_release=lambda *_: setattr(self, "cancel_flag", True))
        act.add_widget(self.dl_btn)
        act.add_widget(self.cn_btn)
        self.add_widget(act)

        c_log = CardBox(orientation="vertical", padding=dp(10))
        sc = ScrollView()
        self.log_lbl = Label(text="OmniMedia Saver Mobile ready.\n", font_size=sp(11), color=rgba(MUTED), size_hint_y=None, halign="left", valign="top")
        self.log_lbl.bind(width=lambda *_: setattr(self.log_lbl, "text_size", (self.log_lbl.width, None)), texture_size=lambda *_: setattr(self.log_lbl, "height", max(sc.height, self.log_lbl.texture_size[1])))
        sc.add_widget(self.log_lbl)
        c_log.add_widget(sc)
        self.add_widget(c_log)
        Clock.schedule_interval(self._tick, 1.0 / 30.0)

    def _tick(self, dt):
        try:
            while True:
                self.q.get_nowait()()
        except queue.Empty:
            pass
        self.ring.step(dt)

    def sel_q(self, key):
        self.quality_key = key
        for k, b in self.chips.items():
            b.background_color = rgba(ACCENT if k == key else CARD_2)
            b.color = rgba("#ffffff" if k == key else MUTED)

    def log(self, msg):
        self.q.put(lambda: setattr(self.log_lbl, "text", "\n".join((self.log_lbl.text + msg + "\n").splitlines()[-40:]) + "\n"))

    def start(self):
        url = self.url_in.text.strip()
        if not url or self.downloading:
            return
        self.downloading, self.cancel_flag = True, False
        self.dl_btn.disabled, self.cn_btn.disabled = True, False
        self.ring.value, self.ring.target, self.ring.ring_color, self.ring.sub_text = 0.0, 0.0, ACCENT, "ACTIVE"
        self.st_lbl.text = "Downloading..."
        threading.Thread(target=self._worker, args=(url,), daemon=True).start()

    def _hook(self, d):
        if self.cancel_flag:
            raise Cancelled()
        if d.get("status") == "downloading":
            tot = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes", 0)
            frac = (done / tot) if tot else 0.0
            spd = d.get("speed")
            txt = f"{done/1048576:.1f} MB ({spd/1048576:.1f} MB/s)" if spd else f"{done/1048576:.1f} MB"
            self.q.put(lambda: (setattr(self.ring, "target", frac), setattr(self.dt_lbl, "text", txt)))

    def _worker(self, url):
        try:
            import yt_dlp
            opts = {
                "format": QUALITIES[self.quality_key]["f"],
                "outtmpl": os.path.join(self.folder, "%(title)s.%(ext)s"),
                "noplaylist": True,
                "progress_hooks": [self._hook],
                "quiet": True,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
            title = (info or {}).get("title") or "Media"
            self.log(f"Saved: {title}")
            self.q.put(lambda: self._done("Saved!", GOOD, "DONE", 1.0, title[:40]))
        except Exception as e:
            self.log(f"Stopped: {e}")
            self.q.put(lambda: self._done("Cancelled" if self.cancel_flag else "Failed", BAD, "STOP", 0.0, str(e)[:40]))

    def _done(self, st, col, sub, targ, det):
        self.downloading = False
        self.dl_btn.disabled, self.cn_btn.disabled = False, True
        self.ring.target, self.ring.ring_color, self.ring.sub_text = targ, col, sub
        self.st_lbl.text, self.st_lbl.color = st, rgba(col)
        self.dt_lbl.text = det

class OmniMediaMobileApp(App):
    def build(self):
        if os.path.isfile("icon.png"):
            self.icon = "icon.png"
        return MobileUI()

if __name__ == "__main__":
    OmniMediaMobileApp().run()
