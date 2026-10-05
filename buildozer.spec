[app]
title = Attendance Tracker
package.name = attendancetracker
package.domain = org.aniket
source.dir = .
source.include_exts = py,kv,db,png,jpg,jpeg
version = 1.0
requirements = python3,kivy==2.3.1
orientation = portrait
fullscreen = 0

android.api = 33
android.minapi = 23
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.permissions =

[buildozer]
log_level = 2
warn_on_root = 1
