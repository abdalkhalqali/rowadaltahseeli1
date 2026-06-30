#!/usr/bin/env python3
"""
نقطة تشغيل بوت رواد التحصيلي
"""
import os, sys

required = ['BOT_TOKEN']
missing  = [k for k in required if not os.environ.get(k)]
if missing:
    print(f"❌ متغيرات بيئة مفقودة: {', '.join(missing)}")
    sys.exit(1)

print("🤖 بدء تشغيل بوت رواد التحصيلي...")
import bot
