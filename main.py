import math
import os
import queue
import shutil
import threading

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
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

try:
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
except Exception:
    pass

if platform not in ("android", "ios"):
    Window.size = (400, 780)
APP_NAME = "OmniMedia Saver"
APP_VERSION = "2.0.1"

BG_TOP = "#05060b"
CARD = "#0e1018"
CARD_2 = "#171a26"
CARD_3 = "#1f2333"
BORDER = "#272b3d"
TRACK = "#1a1d2a"
ACCENT = "#8b5cf6"
ACCENT_SOFT = "#c4b5fd"
TEXT = "#eceef6"
MUTED = "#8a90a6"
GOOD = "#34d399"
BAD = "#fb7185"
WARN = "#fbbf24"

QUALITIES = {
    "Best": {"f": "best[ext=mp4]/best"},
    "1080p": {"f": "best[height<=1080][ext=mp4]/best[height<=1080]/best"},
    "720p": {"f": "best[height<=720][ext=mp4]/best[height<=720]/best"},
    "480p": {"f": "best[height<=480][ext=mp4]/best[height<=480]/best"},
    "Audio": {"f": "bestaudio[ext=m4a]/bestaudio/best"},
}
CHIPS = ["Best", "1080p", "720p", "480p", "Audio"]

SAVE_PRESETS = [
    ("Downloads / OmniMediaSaver", "Download/OmniMediaSaver"),
    ("Movies / OmniMediaSaver", "Movies/OmniMediaSaver"),
    ("Music / OmniMediaSaver", "Music/OmniMediaSaver"),
    ("App Storage (Private)", "APP_PRIVATE"),
]


def rgba(hex_code, alpha=1.0):
    c = get_color_from_hex(hex_code)
    return (c[0], c[1], c[2], alpha)


def clip(text, limit=44):
    text = text or ""
    return text if len(text) <= limit else text[: limit - 1] + "..."


def get_app_private_dir():
    if platform == "android":
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            ctx = PythonActivity.mActivity
            ext = ctx.getExternalFilesDir(None)
            if ext is not None:
                p = os.path.join(ext.getAbsolutePath(), "OmniMediaSaver")
                os.makedirs(p, exist_ok=True)
                return p
            p = os.path.join(ctx.getFilesDir().getAbsolutePath(), "OmniMediaSaver")
            os.makedirs(p, exist_ok=True)
            return p
        except Exception:
            pass
        try:
            from android.storage import app_storage_path
            p = os.path.join(app_storage_path(), "OmniMediaSaver")
            os.makedirs(p, exist_ok=True)
            return p
        except Exception:
            pass
    p = os.path.join(os.path.expanduser("~"), "Downloads", "OmniMediaSaver")
    os.makedirs(p, exist_ok=True)
    return p


def export_to_android_mediastore(src_path, rel_dir):
    from jnius import autoclass

    BuildVersion = autoclass("android.os.Build$VERSION")
    sdk = int(BuildVersion.SDK_INT)
    filename = os.path.basename(src_path)
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    mime_map = {
        "mp4": "video/mp4",
        "mkv": "video/x-matroska",
        "webm": "video/webm",
        "m4a": "audio/mp4",
        "mp3": "audio/mpeg",
        "ogg": "audio/ogg",
        "opus": "audio/opus",
    }
    mime = mime_map.get(ext, "application/octet-stream")

    if sdk >= 29:
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        ContentValues = autoclass("android.content.ContentValues")
        MediaStoreDownloads = autoclass("android.provider.MediaStore$Downloads")
        MediaStoreVideo = autoclass("android.provider.MediaStore$Video$Media")
        MediaStoreAudio = autoclass("android.provider.MediaStore$Audio$Media")
        MediaColumns = autoclass("android.provider.MediaStore$MediaColumns")

        resolver = PythonActivity.mActivity.getContentResolver()
        values = ContentValues()
        values.put(MediaColumns.DISPLAY_NAME, filename)
        values.put(MediaColumns.MIME_TYPE, mime)
        values.put(MediaColumns.RELATIVE_PATH, rel_dir.rstrip("/") + "/")

        if rel_dir.startswith("Movies"):
            collection = MediaStoreVideo.EXTERNAL_CONTENT_URI
        elif rel_dir.startswith("Music"):
            collection = MediaStoreAudio.EXTERNAL_CONTENT_URI
        else:
            collection = MediaStoreDownloads.EXTERNAL_CONTENT_URI

        uri = resolver.insert(collection, values)
        if uri is None:
            raise OSError("MediaStore insert returned null URI")

        out_stream = resolver.openOutputStream(uri)
        try:
            with open(src_path, "rb") as f_in:
                while True:
                    chunk = f_in.read(262144)
                    if not chunk:
                        break
                    out_stream.write(chunk)
            out_stream.flush()
        finally:
            out_stream.close()
        return f"/{rel_dir}/{filename}"

    from android.storage import primary_external_storage_path
    dest_dir = os.path.join(primary_external_storage_path(), rel_dir)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, filename)
    shutil.copy2(src_path, dest_path)
    return dest_path

class Cancelled(Exception):
    pass


class UILogger:
    def __init__(self, write_fn):
        self.write = write_fn

    def debug(self, msg):
        if not msg.startswith("[debug]"):
            self.write(msg)

    def info(self, msg):
        self.write(msg)

    def warning(self, msg):
        self.write("Warning: " + msg)

    def error(self, msg):
        self.write("Error: " + msg)


class CardBox(BoxLayout):
    def __init__(self, bg_hex=CARD, radius=16, **kw):
        super().__init__(**kw)
        self.r = dp(radius)
        with self.canvas.before:
            Color(*rgba(bg_hex))
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.r])
            Color(*rgba(BORDER))
            self._line = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, self.r),
                width=dp(1),
            )
        self.bind(pos=self._upd, size=self._upd)

    def _upd(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, self.r)


class RingWidget(Widget):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.value = 0.0
        self.target = 0.0
        self.indeterminate = False
        self.t = 0.0
        self.ring_color = ACCENT
        self.sub_text = "READY"
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
        self.bind(
            pos=lambda *_: setattr(self._bg, "pos", self.pos),
            size=lambda *_: setattr(self._bg, "size", self.size),
        )

        self.q = queue.Queue()
        self.downloading = False
        self.cancel_flag = False
        self.saved_count = 0
        self.quality_key = "Best"
        self.save_rel_dir = "Download/OmniMediaSaver"
        self.private_dir = get_app_private_dir()

        self._request_legacy_permissions()
        self._build_ui()
        Clock.schedule_interval(self._tick, 1.0 / 30.0)

    def _request_legacy_permissions(self):
        if platform == "android":
            try:
                from android.permissions import Permission, request_permissions
                request_permissions([
                    Permission.INTERNET,
                    Permission.WRITE_EXTERNAL_STORAGE,
                    Permission.READ_EXTERNAL_STORAGE,
                ])
            except Exception:
                pass

    def _build_ui(self):
        hdr = BoxLayout(size_hint_y=None, height=dp(46))
        t_lbl = Label(
            text=f"{APP_NAME}  v{APP_VERSION}",
            font_size=sp(19),
            bold=True,
            color=rgba(TEXT),
            halign="left",
            valign="middle",
        )
        t_lbl.bind(size=t_lbl.setter("text_size"))
        hdr.add_widget(t_lbl)
        self.add_widget(hdr)

        c_url = CardBox(orientation="vertical", size_hint_y=None, height=dp(88), padding=dp(10), spacing=dp(6))
        u_cap = Label(text="PASTE MEDIA LINK", font_size=sp(10), bold=True, color=rgba(MUTED), size_hint_y=None, height=dp(16), halign="left", valign="middle")
        u_cap.bind(size=u_cap.setter("text_size"))
        c_url.add_widget(u_cap)
        row = BoxLayout(spacing=dp(6), size_hint_y=None, height=dp(42))
        self.url_in = TextInput(
            hint_text="https:// video or audio link...",
            multiline=False,
            background_normal="",
            background_active="",
            background_color=rgba(CARD_2),
            foreground_color=rgba(TEXT),
            hint_text_color=rgba(MUTED),
            cursor_color=rgba(ACCENT_SOFT),
            font_size=sp(13),
            padding=[dp(10), dp(10), dp(10), dp(10)],
        )
        b_paste = Button(text="Paste", size_hint_x=None, width=dp(64), background_normal="", background_color=rgba(ACCENT), bold=True)
        b_paste.bind(on_release=lambda *_: self._paste_url())
        b_clear = Button(text="Clear", size_hint_x=None, width=dp(54), background_normal="", background_color=rgba(CARD_3))
        b_clear.bind(on_release=lambda *_: setattr(self.url_in, "text", ""))
        row.add_widget(self.url_in)
        row.add_widget(b_paste)
        row.add_widget(b_clear)
        c_url.add_widget(row)
        self.add_widget(c_url)

        c_qual = CardBox(orientation="vertical", size_hint_y=None, height=dp(122), padding=dp(10), spacing=dp(6))
        q_cap = Label(text="QUALITY & SAVE LOCATION", font_size=sp(10), bold=True, color=rgba(MUTED), size_hint_y=None, height=dp(16), halign="left", valign="middle")
        q_cap.bind(size=q_cap.setter("text_size"))
        c_qual.add_widget(q_cap)

        chips_row = BoxLayout(spacing=dp(6), size_hint_y=None, height=dp(36))
        self.chips = {}
        for k in CHIPS:
            b = Button(text=k, background_normal="", background_color=rgba(CARD_2), bold=True, font_size=sp(12))
            b.bind(on_release=lambda _b, key=k: self.sel_q(key))
            chips_row.add_widget(b)
            self.chips[k] = b
        c_qual.add_widget(chips_row)
        self.sel_q("Best")

        loc_row = BoxLayout(spacing=dp(6), size_hint_y=None, height=dp(38))
        self.folder_btn = Button(
            text=self._format_folder_label(),
            background_normal="",
            background_color=rgba(CARD_2),
            color=rgba(ACCENT_SOFT),
            font_size=sp(12),
            halign="left",
            valign="middle",
        )
        self.folder_btn.bind(size=lambda inst, *_: setattr(inst, "text_size", (inst.width - dp(16), None)))
        self.folder_btn.bind(on_release=lambda *_: self.open_folder_picker())
        btn_change = Button(
            text="Change",
            size_hint_x=None,
            width=dp(72),
            background_normal="",
            background_color=rgba(CARD_3),
            color=rgba(TEXT),
            font_size=sp(12),
            bold=True,
        )
        btn_change.bind(on_release=lambda *_: self.open_folder_picker())
        loc_row.add_widget(self.folder_btn)
        loc_row.add_widget(btn_change)
        c_qual.add_widget(loc_row)
        self.add_widget(c_qual)

        c_prog = CardBox(orientation="horizontal", size_hint_y=None, height=dp(136), padding=dp(10), spacing=dp(10))
        self.ring = RingWidget(size_hint_x=None, width=dp(114))
        c_prog.add_widget(self.ring)
        info_box = BoxLayout(orientation="vertical", spacing=dp(4))
        self.st_lbl = Label(text="Ready", font_size=sp(16), bold=True, color=rgba(TEXT), halign="left", valign="middle")
        self.st_lbl.bind(size=self.st_lbl.setter("text_size"))
        self.dt_lbl = Label(text="Paste a link and tap Download", font_size=sp(11), color=rgba(MUTED), halign="left", valign="middle")
        self.dt_lbl.bind(size=self.dt_lbl.setter("text_size"))
        self.saved_lbl = Label(text="Saved this session: 0", font_size=sp(10), color=rgba(ACCENT_SOFT), halign="left", valign="middle")
        self.saved_lbl.bind(size=self.saved_lbl.setter("text_size"))
        info_box.add_widget(self.st_lbl)
        info_box.add_widget(self.dt_lbl)
        info_box.add_widget(self.saved_lbl)
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
        sc = ScrollView(do_scroll_x=False)
        self.log_lbl = Label(
            text=f"{APP_NAME} Mobile ready.\nSave folder: {self.save_rel_dir}\n",
            font_size=sp(11),
            color=rgba(MUTED),
            size_hint_y=None,
            halign="left",
            valign="top",
        )
        self.log_lbl.bind(
            width=lambda *_: setattr(self.log_lbl, "text_size", (self.log_lbl.width, None)),
            texture_size=lambda *_: setattr(self.log_lbl, "height", max(sc.height, self.log_lbl.texture_size[1])),
        )
        sc.add_widget(self.log_lbl)
        c_log.add_widget(sc)
        self.add_widget(c_log)

    def _format_folder_label(self):
        if self.save_rel_dir == "APP_PRIVATE":
            return "Save to: App Storage (Private)"
        return f"Save to: {clip(self.save_rel_dir, 32)}"

    def _paste_url(self):
        try:
            txt = Clipboard.paste()
            if txt:
                self.url_in.text = txt.strip()
        except Exception as exc:
            self.log(f"Clipboard error: {exc}")

    def open_folder_picker(self):
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))

        for title, rel_val in SAVE_PRESETS:
            is_cur = self.save_rel_dir == rel_val
            btn = Button(
                text=title,
                size_hint_y=None,
                height=dp(42),
                background_normal="",
                background_color=rgba(ACCENT if is_cur else CARD_2),
                color=rgba("#ffffff" if is_cur else TEXT),
                bold=is_cur,
                font_size=sp(13),
            )
            btn.bind(on_release=lambda _b, val=rel_val: self._apply_folder(val, popup))
            content.add_widget(btn)

        custom_lbl = Label(
            text="Or enter custom folder under Download/:",
            size_hint_y=None,
            height=dp(22),
            font_size=sp(11),
            color=rgba(MUTED),
            halign="left",
            valign="middle",
        )
        custom_lbl.bind(size=custom_lbl.setter("text_size"))
        content.add_widget(custom_lbl)

        custom_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
        custom_in = TextInput(
            hint_text="e.g. MyVideos",
            multiline=False,
            background_normal="",
            background_active="",
            background_color=rgba(CARD_2),
            foreground_color=rgba(TEXT),
            hint_text_color=rgba(MUTED),
            font_size=sp(13),
            padding=[dp(10), dp(10), dp(10), dp(10)],
        )
        save_btn = Button(
            text="Apply",
            size_hint_x=None,
            width=dp(74),
            background_normal="",
            background_color=rgba(ACCENT),
            bold=True,
        )

        def _apply_custom(*_):
            raw = custom_in.text.strip().strip("/\\")
            if raw:
                safe = "".join(ch for ch in raw if ch.isalnum() or ch in (" ", "_", "-", "/")).strip("/")
                if safe:
                    target = safe if safe.startswith(("Download/", "Movies/", "Music/")) else f"Download/{safe}"
                    self._apply_folder(target, popup)

        save_btn.bind(on_release=_apply_custom)
        custom_row.add_widget(custom_in)
        custom_row.add_widget(save_btn)
        content.add_widget(custom_row)

        popup = Popup(
            title="Choose Download Location",
            content=content,
            size_hint=(0.92, None),
            height=dp(340),
            background_color=rgba(CARD),
            separator_color=rgba(ACCENT),
        )
        popup.open()

    def _apply_folder(self, rel_val, popup):
        self.save_rel_dir = rel_val
        self.folder_btn.text = self._format_folder_label()
        self.log(f"Download location set to: {rel_val}")
        popup.dismiss()

    def _tick(self, dt):
        try:
            while True:
                fn = self.q.get_nowait()
                try:
                    fn()
                except Exception as cb_err:
                    self._append_log_now(f"UI update error: {cb_err}")
        except queue.Empty:
            pass
        try:
            self.ring.step(dt)
        except Exception:
            pass

    def _append_log_now(self, msg):
        lines = (self.log_lbl.text + str(msg).strip() + "\n").splitlines()[-50:]
        self.log_lbl.text = "\n".join(lines) + "\n"

    def log(self, msg):
        text = str(msg)
        self.q.put(lambda t=text: self._append_log_now(t))

    def sel_q(self, key):
        self.quality_key = key
        for k, b in self.chips.items():
            b.background_color = rgba(ACCENT if k == key else CARD_2)
            b.color = rgba("#ffffff" if k == key else MUTED)

    def start(self):
        url = self.url_in.text.strip()
        if not url:
            self.st_lbl.text = "Enter a link first"
            self.st_lbl.color = rgba(BAD)
            self.ring.ring_color = BAD
            self.ring.sub_text = "NO LINK"
            return
        if self.downloading:
            return
        self.downloading = True
        self.cancel_flag = False
        self.dl_btn.disabled = True
        self.dl_btn.text = "Downloading..."
        self.cn_btn.disabled = False
        self.ring.indeterminate = False
        self.ring.value = 0.0
        self.ring.target = 0.0
        self.ring.ring_color = ACCENT
        self.ring.sub_text = "ACTIVE"
        self.st_lbl.text = "Starting..."
        self.st_lbl.color = rgba(TEXT)
        self.dt_lbl.text = "Connecting to server..."
        threading.Thread(target=self._worker, args=(url,), daemon=True).start()

    def _hook(self, d):
        if self.cancel_flag:
            raise Cancelled()
        status = d.get("status")
        if status == "downloading":
            tot = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes", 0)
            frac = (done / tot) if tot else 0.0
            spd = d.get("speed")
            txt = f"{done / 1048576:.1f} MB ({spd / 1048576:.1f} MB/s)" if spd else f"{done / 1048576:.1f} MB"
            self.q.put(lambda f=frac, t=txt: self._update_progress(f, t))
        elif status == "finished":
            self.q.put(lambda: self._set_saving_state())

    def _update_progress(self, frac, txt):
        self.ring.indeterminate = False
        self.ring.target = max(0.0, min(1.0, frac))
        self.st_lbl.text = "Downloading..."
        self.dt_lbl.text = txt

    def _set_saving_state(self):
        self.ring.indeterminate = True
        self.ring.sub_text = "SAVING"
        self.st_lbl.text = "Saving file..."

    def _worker(self, url):
        stage_dir = os.path.join(self.private_dir, "staging")
        os.makedirs(stage_dir, exist_ok=True)
        for old_f in os.listdir(stage_dir):
            try:
                os.remove(os.path.join(stage_dir, old_f))
            except Exception:
                pass

        try:
            import yt_dlp

            opts = {
                "format": QUALITIES[self.quality_key]["f"],
                "outtmpl": os.path.join(stage_dir, "%(title).80s.%(ext)s"),
                "noplaylist": True,
                "cachedir": False,
                "restrictfilenames": True,
                "nocheckcertificate": False,
                "progress_hooks": [self._hook],
                "logger": UILogger(self.log),
                "noprogress": True,
                "quiet": True,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_path = ydl.prepare_filename(info)

            if not os.path.isfile(downloaded_path):
                staged = [os.path.join(stage_dir, x) for x in os.listdir(stage_dir) if os.path.isfile(os.path.join(stage_dir, x))]
                if not staged:
                    raise FileNotFoundError("Downloaded file not found in staging folder")
                downloaded_path = max(staged, key=os.path.getmtime)

            title = (info or {}).get("title") or os.path.basename(downloaded_path)
            saved_display = self._move_to_destination(downloaded_path)
            self.log(f"Saved: {saved_display}")
            t_cap = clip(title, 40)
            self.q.put(lambda t=t_cap, d=saved_display: self._done("Saved!", GOOD, "DONE", 1.0, t, count_inc=True))

        except Exception as exc:
            err_text = str(exc)
            was_cancelled = self.cancel_flag or isinstance(exc, Cancelled)
            self.log("Download cancelled." if was_cancelled else f"Error: {err_text}")
            status_txt = "Cancelled" if was_cancelled else "Failed"
            color_hex = MUTED if was_cancelled else BAD
            sub_txt = "STOPPED" if was_cancelled else "ERROR"
            detail_txt = "Cancelled by user." if was_cancelled else clip(err_text, 44)
            self.q.put(lambda st=status_txt, c=color_hex, sb=sub_txt, dt=detail_txt: self._done(st, c, sb, 0.0, dt))

    def _move_to_destination(self, src_path):
        filename = os.path.basename(src_path)
        if self.save_rel_dir == "APP_PRIVATE":
            dest = os.path.join(self.private_dir, filename)
            shutil.move(src_path, dest)
            return dest

        if platform == "android":
            try:
                saved_loc = export_to_android_mediastore(src_path, self.save_rel_dir)
                try:
                    os.remove(src_path)
                except Exception:
                    pass
                return saved_loc
            except Exception as ms_err:
                self.log(f"Public storage fallback ({ms_err}); saving in app folder.")
                dest = os.path.join(self.private_dir, filename)
                shutil.move(src_path, dest)
                return dest

        dest_dir = os.path.join(os.path.expanduser("~"), self.save_rel_dir)
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, filename)
        shutil.move(src_path, dest)
        return dest

    def _done(self, status_txt, color_hex, sub_txt, target_val, detail_txt, count_inc=False):
        self.downloading = False
        self.dl_btn.disabled = False
        self.dl_btn.text = "Download"
        self.cn_btn.disabled = True
        self.ring.indeterminate = False
        self.ring.target = target_val
        self.ring.ring_color = color_hex
        self.ring.sub_text = sub_txt
        self.st_lbl.text = status_txt
        self.st_lbl.color = rgba(color_hex)
        self.dt_lbl.text = detail_txt
        if count_inc:
            self.saved_count += 1
            self.saved_lbl.text = f"Saved this session: {self.saved_count}"


class OmniMediaMobileApp(App):
    def build(self):
        self.title = APP_NAME
        if os.path.isfile("icon.png"):
            self.icon = "icon.png"
        return MobileUI()


if __name__ == "__main__":
    OmniMediaMobileApp().run()
