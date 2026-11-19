[app]
title = OmniMedia Saver
package.name = omnimediasaver
package.domain = org.omnimedia
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ico
version = 2.0.0

# Custom app icon & loading splash screen matching Desktop LogoCanvas
icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/presplash.png
presplash.color = #05060b

# Core Python requirements (openssl is required for HTTPS in yt-dlp on Android)
requirements = python3,kivy==2.3.0,openssl,yt-dlp,certifi,urllib3,requests,charset-normalizer==3.4.5,idna

orientation = portrait
fullscreen = 0

# Android specific configuration
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a
android.allow_backup = True
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 0
