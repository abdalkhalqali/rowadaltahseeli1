#!/bin/bash
# ====================================================
# سكريبت المزامنة التلقائية مع GitHub
# ====================================================

REPO_URL="https://${GITHUB_PERSONAL_ACCESS_TOKEN}@github.com/abdalkhalqali/rowadaltahseeli1.git"

if [ -z "$GITHUB_PERSONAL_ACCESS_TOKEN" ]; then
    echo "⚠️  لم يتم العثور على GITHUB_PERSONAL_ACCESS_TOKEN"
    exit 1
fi

LOCAL=$(git rev-parse HEAD 2>/dev/null)
REMOTE=$(git ls-remote "$REPO_URL" refs/heads/main 2>/dev/null | cut -f1)

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "✅ المستودع محدّث — لا توجد تغييرات جديدة ($(date '+%H:%M:%S'))"
    exit 0
fi

echo "🚀 جاري رفع التحديثات إلى GitHub... ($(date '+%H:%M:%S'))"
git push "$REPO_URL" main --quiet 2>&1

if [ $? -eq 0 ]; then
    echo "✅ تم الرفع بنجاح | آخر commit: $(git log --oneline -1)"
else
    echo "❌ فشل الرفع — تحقق من الرمز (GITHUB_PERSONAL_ACCESS_TOKEN)"
fi
