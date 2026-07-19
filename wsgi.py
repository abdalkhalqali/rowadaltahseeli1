"""
نقطة دخول Render / Gunicorn
يشغّل المنصة + البوت معاً (البوت مرة واحدة فقط)
"""
import os, sys, threading, time, subprocess

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BOT_PID_FILE = '/tmp/rowad_bot.pid'

def is_bot_running():
    """تحقق هل البوت يعمل فعلاً"""
    if not os.path.exists(BOT_PID_FILE):
        return False
    try:
        with open(BOT_PID_FILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)  # إذا لم يطرح استثناء → العملية موجودة
        return True
    except (OSError, ValueError):
        return False

def start_bot():
    """تشغيل بوت تيليغرام في process منفصل — يتطلب RUN_BOT=true صريحة"""
    if os.environ.get('RUN_BOT', '').lower() != 'true':
        print("ℹ️ البوت معطّل — اضبط RUN_BOT=true لتفعيله")
        return

    if is_bot_running():
        print("🤖 البوت يعمل بالفعل — تخطي التشغيل المكرر")
        return

    bot_path = os.path.join(ROOT_DIR, 'bot.py')
    if not os.path.exists(bot_path):
        print("⚠️ bot.py غير موجود")
        return
    if not os.environ.get('BOT_TOKEN'):
        print("⚠️ BOT_TOKEN غير موجود في المتغيرات")
        return
    if not os.environ.get('OPENROUTER_KEY'):
        print("ℹ️ OPENROUTER_KEY غير موجود — سيعتمد البوت على g4f فقط")

    time.sleep(3)
    env = {**os.environ, 'PORT': '8080'}
    proc = subprocess.Popen(
        [sys.executable, bot_path],
        cwd=ROOT_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    with open(BOT_PID_FILE, 'w') as f:
        f.write(str(proc.pid))
    print(f"🤖 البوت يعمل في الخلفية (PID: {proc.pid})")

# ── تجهيز المنصة ──
sys.path.insert(0, os.path.join(ROOT_DIR, 'coach_tahseeli'))
os.chdir(os.path.join(ROOT_DIR, 'coach_tahseeli'))

from app import create_app
app = create_app()

# ── تشغيل البوت في الخلفية (مرة واحدة فقط) ──
threading.Thread(target=start_bot, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 رواد التحصيلي — المنفذ {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
