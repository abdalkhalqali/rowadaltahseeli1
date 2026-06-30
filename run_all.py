"""
نقطة تشغيل موحدة عند النشر:
  - منصة رواد التحصيلي (Flask على بورت 5000)
  - بوت تيليجرام (في process منفصل)
"""
import os, sys, threading, time, subprocess

# احفظ مسار الجذر قبل أي تغيير
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BOT_PATH = os.path.join(ROOT_DIR, "bot.py")

# ── تشغيل البوت في process منفصل ──
def start_bot():
    time.sleep(4)  # انتظر حتى تجهز المنصة
    proc = subprocess.Popen(
        [sys.executable, BOT_PATH],
        cwd=ROOT_DIR,
        env={**os.environ, "PORT": "8443"}
    )
    print(f"🤖 البوت يعمل في الخلفية (PID: {proc.pid})")

# ── تشغيل المنصة ──
sys.path.insert(0, os.path.join(ROOT_DIR, 'coach_tahseeli'))
os.chdir(os.path.join(ROOT_DIR, 'coach_tahseeli'))

from app import create_app

app = create_app()

if __name__ == '__main__':
    print("🚀 منصة رواد التحصيلي — تشغيل على المنفذ 5000")
    threading.Thread(target=start_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=False)
