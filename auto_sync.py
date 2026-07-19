#!/usr/bin/env python3
"""
مزامنة تلقائية مع GitHub — يعمل في الخلفية
يرفع النسخة المحلية (المصدر الرئيسي) إلى GitHub كل 30 دقيقة
"""
import subprocess, os, time, tempfile, shutil
from datetime import datetime

GITHUB_USER  = "abdalkhalqali"
GITHUB_REPO  = "rowadaltahseeli1"
BOT_REPO     = "rowadaltahseeli-bot"
INTERVAL     = 2 * 60   # كل دقيقتين — رفع شبه فوري
WORKTREE     = "/tmp/gh_push_worktree"
BOT_WORKTREE = "/tmp/gh_bot_worktree"

def get_repo_url(repo=None):
    token = os.environ.get('GITHUB_PERSONAL_ACCESS_TOKEN', '')
    r = repo or GITHUB_REPO
    return f"https://{GITHUB_USER}:{token}@github.com/{GITHUB_USER}/{r}.git"

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def run(cmd, cwd=None, **kwargs):
    env = os.environ.copy()
    env['GIT_TERMINAL_PROMPT'] = '0'
    return subprocess.run(cmd, capture_output=True, text=True,
                          timeout=180, env=env, cwd=cwd or '.', **kwargs)

def get_local_hash():
    r = run(['git', 'rev-parse', 'HEAD'])
    return r.stdout.strip()

def get_remote_hash(repo=None):
    r = run(['git', 'ls-remote', get_repo_url(repo), 'refs/heads/main'])
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip().split('\t')[0]
    return None

def last_commit():
    r = run(['git', 'log', '--oneline', '-1'])
    return r.stdout.strip()

def push_via_clean_repo():
    """
    إنشاء مستودع مؤقت نظيف من الملفات الحالية ورفعه إلى GitHub.
    يتجاوز مشاكل التاريخ المكسور في المستودع الأصلي.
    """
    token = os.environ.get('GITHUB_PERSONAL_ACCESS_TOKEN', '')
    url   = get_repo_url()
    ws    = os.getcwd()  # workspace root

    log("🧹 إنشاء مستودع نظيف مؤقت...")

    # حذف أي مستودع مؤقت قديم
    if os.path.exists(WORKTREE):
        shutil.rmtree(WORKTREE, ignore_errors=True)
    os.makedirs(WORKTREE, exist_ok=True)

    # نسخ الملفات (باستثناء .git وملفات مؤقتة)
    exclude = {'.git', '__pycache__', '*.pyc', WORKTREE, '/tmp'}
    log("📋 نسخ ملفات المشروع...")
    for item in os.listdir(ws):
        if item in ('.git', '.local', '.github', 'data_store'):
            # data_store يُدار عبر GitHub API مباشرة — لا يُلمَس هنا
            continue
        src = os.path.join(ws, item)
        dst = os.path.join(WORKTREE, item)
        try:
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.git'))
            else:
                shutil.copy2(src, dst)
        except Exception as e:
            log(f"  ⚠️ تعذّر نسخ {item}: {e}")

    # تهيئة مستودع git جديد نظيف
    r = run(['git', 'init', '-b', 'main'], cwd=WORKTREE)
    if r.returncode != 0:
        log(f"❌ فشل git init: {r.stderr[:100]}")
        return False

    # إعداد بيانات المستخدم
    run(['git', 'config', 'user.email', 'sync@rowadtahseeli.sa'], cwd=WORKTREE)
    run(['git', 'config', 'user.name', 'رواد التحصيلي — نظام المزامنة'], cwd=WORKTREE)

    # إعداد LFS إن وُجد
    run(['git', 'lfs', 'install', '--local'], cwd=WORKTREE)

    # نسخ .gitattributes إن وُجد
    gattr = os.path.join(ws, '.gitattributes')
    if os.path.exists(gattr):
        shutil.copy2(gattr, os.path.join(WORKTREE, '.gitattributes'))

    # إضافة الملفات وعمل commit
    log("📝 إضافة الملفات وعمل commit...")
    r_add = run(['git', 'add', '-A'], cwd=WORKTREE)
    if r_add.returncode != 0:
        log(f"⚠️ git add: {r_add.stderr[:100]}")

    commit_msg = last_commit() or "مزامنة تلقائية من رواد التحصيلي"
    r_commit = run(['git', 'commit', '-m', commit_msg, '--allow-empty'],
                   cwd=WORKTREE)
    if r_commit.returncode != 0:
        log(f"❌ فشل git commit: {r_commit.stderr[:100]}")
        return False

    new_hash = run(['git', 'rev-parse', '--short', 'HEAD'], cwd=WORKTREE).stdout.strip()
    log(f"✅ Commit جديد: {new_hash}")

    # رفع LFS أولاً
    r_lfs = run(['git', 'lfs', 'push', '--all', url], cwd=WORKTREE)
    if r_lfs.returncode == 0:
        log("📦 LFS: تم رفع الملفات الكبيرة")
    else:
        log(f"📦 LFS: {r_lfs.stderr[:80] or 'لا توجد ملفات كبيرة'}")

    # رفع الـ commits
    log("🚀 رفع إلى GitHub...")
    r_push = run(['git', 'push', url, 'main', '--force'], cwd=WORKTREE)
    if r_push.returncode == 0:
        log(f"✅ تم الرفع بنجاح!")
        return True
    else:
        err = r_push.stderr.replace(token, '***')
        log(f"❌ فشل الرفع: {err[:300]}")
        return False

def push_bot_repo():
    """رفع ملفات البوت إلى المستودع المستقل"""
    token = os.environ.get('GITHUB_PERSONAL_ACCESS_TOKEN', '')
    url   = get_repo_url(BOT_REPO)
    ws    = os.getcwd()

    # الملفات المخصصة للبوت
    BOT_FILES = {
        'bot.py':             'bot.py',
        'bot_requirements.txt': 'requirements.txt',
        'run_bot.py':         'run_bot.py',
        'bot_env_example.txt': '.env.example',
    }

    log(f"🤖 تجهيز مستودع البوت ({BOT_REPO})...")

    if os.path.exists(BOT_WORKTREE):
        shutil.rmtree(BOT_WORKTREE, ignore_errors=True)
    os.makedirs(BOT_WORKTREE, exist_ok=True)

    for src_name, dst_name in BOT_FILES.items():
        src = os.path.join(ws, src_name)
        dst = os.path.join(BOT_WORKTREE, dst_name)
        if os.path.exists(src):
            shutil.copy2(src, dst)
        else:
            log(f"  ⚠️ ملف غير موجود: {src_name}")

    # تهيئة مستودع git
    run(['git', 'init', '-b', 'main'], cwd=BOT_WORKTREE)
    run(['git', 'config', 'user.email', 'sync@rowadtahseeli.sa'], cwd=BOT_WORKTREE)
    run(['git', 'config', 'user.name', 'رواد التحصيلي — نظام المزامنة'], cwd=BOT_WORKTREE)

    run(['git', 'add', '-A'], cwd=BOT_WORKTREE)
    commit_msg = last_commit() or "مزامنة تلقائية — بوت رواد التحصيلي"
    r_commit = run(['git', 'commit', '-m', commit_msg, '--allow-empty'], cwd=BOT_WORKTREE)
    if r_commit.returncode != 0:
        log(f"❌ Bot commit فشل: {r_commit.stderr[:100]}")
        return False

    r_push = run(['git', 'push', url, 'main', '--force'], cwd=BOT_WORKTREE)
    if r_push.returncode == 0:
        log(f"✅ تم رفع البوت إلى {BOT_REPO}!")
        return True
    else:
        err = r_push.stderr.replace(token, '***')
        log(f"❌ فشل رفع البوت: {err[:200]}")
        return False


def sync():
    """مزامنة مع GitHub — المنصة والبوت معاً"""
    if not os.environ.get('GITHUB_PERSONAL_ACCESS_TOKEN'):
        log("❌ GITHUB_PERSONAL_ACCESS_TOKEN غير موجود")
        return False

    local  = get_local_hash()
    remote = get_remote_hash()

    if not local:
        log("⚠️ لا يوجد commit محلي")
        return False

    if not remote:
        log("⚠️ تعذّر الاتصال بـ GitHub")
        return False

    if local == remote:
        log(f"✅ المنصة محدّثة | {last_commit()}")
    else:
        log(f"📊 Local: {local[:8]} | Remote: {remote[:8]}")
        push_via_clean_repo()

    # مزامنة البوت دائماً (ملفاته قد تتغير مع المنصة)
    push_bot_repo()
    return True

def setup_post_commit_hook():
    """رفع فوري بعد كل commit"""
    hook_path = '.git/hooks/post-commit'
    script    = os.path.abspath(__file__)
    hook_content = f'''#!/bin/bash
echo "🔄 رفع تلقائي إلى GitHub بعد الـ commit..."
python3 "{script}" --once &
'''
    try:
        with open(hook_path, 'w') as f:
            f.write(hook_content)
        os.chmod(hook_path, 0o755)
        log("✅ خطاف post-commit مفعّل")
    except Exception as e:
        log(f"⚠️ لم يتم إعداد الخطاف: {e}")

def main():
    import sys
    once_mode = '--once' in sys.argv

    if not once_mode:
        log("=" * 55)
        log("🚀 نظام المزامنة التلقائية مع GitHub")
        log(f"📦 github.com/{GITHUB_USER}/{GITHUB_REPO}  ← المنصة")
        log(f"🤖 github.com/{GITHUB_USER}/{BOT_REPO}  ← البوت")
        log(f"⏱  فحص كل {INTERVAL//60} دقيقة + رفع فوري بعد كل commit")
        log("=" * 55)

    if not os.environ.get('GITHUB_PERSONAL_ACCESS_TOKEN'):
        log("❌ GITHUB_PERSONAL_ACCESS_TOKEN غير موجود — توقف")
        return

    if not once_mode:
        setup_post_commit_hook()

    sync()

    if once_mode:
        return

    while True:
        time.sleep(INTERVAL)
        log("🔍 فحص دوري...")
        try:
            sync()
        except Exception as e:
            log(f"⚠️ خطأ: {e}")

if __name__ == '__main__':
    main()
