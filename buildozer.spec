[app]
title = OmniMedia Saver
package.name = omnimediasaver
package.domain = org.omnimedia
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ico
version = 2.0.0
icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/presplash.png
presplash.color = #05060b
requirements = python3,kivy==2.3.0,yt-dlp,certifi,urllib3,requests,charset-normalizer,idna
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 0
