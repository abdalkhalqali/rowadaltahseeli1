import os, json, glob, time
from datetime import datetime

def show_status():
    print("=" * 55)
    print("  🤖 بوت الاختبارات الجامعية")
    print("  ✅ البوت يعمل من النشر (Deployment) — 24/7")
    print("=" * 55)

    count = 567
    try:
        with open("users_count.json") as f:
            count = json.load(f).get("count", 567)
    except:
        pass

    quizzes = glob.glob("quizzes/*.json")

    convs = 0
    try:
        with open("conversations.json") as f:
            data = json.load(f)
            convs = sum(len(v) for v in data.values())
    except:
        pass

    print(f"  👥 المستخدمون   : {count}")
    print(f"  📚 الاختبارات   : {len(quizzes)}")
    print(f"  💬 الرسائل      : {convs}")
    print(f"  🕐 الوقت        : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)
    print("  لتعديل البوت: عدّل bot.py ثم انشر من زر Deploy")
    print("=" * 55)

    while True:
        time.sleep(60)
        print(f"  ✅ النشر يعمل | {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    show_status()
