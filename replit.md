# منصة رواد التحصيلي الاحترافية

## نظرة عامة
مشروع مدمج من مكوّنَين:
1. **بوت تيليجرام** — اختبارات بالذكاء الاصطناعي، يقرأ أسئلة المنصة، اختبار مباشر في المجموعات
2. **منصة رواد التحصيلي** — تطبيق Flask متكامل لطلاب التحصيل الدراسي السعودي مع AI مجاني

**الشعار:** كُن رائداً لا تابعاً

## الذكاء الاصطناعي المجاني
- النماذج: `meta-llama/llama-3-8b-instruct:free` → `google/gemma-2-9b-it:free` → `mistralai/mistral-7b-instruct:free`
- يستخدم مفتاح OPENROUTER_KEY الموجود بدون أي مفتاح إضافي
- النموذج يُجرَّب بالترتيب — إن فشل الأول يُجرَّب التالي تلقائياً
- **g4f أولاً، OpenRouter احتياطي** — البوت يعمل حتى بدون OPENROUTER_KEY

## ميزات مكتملة حديثاً
- **ردود الإيموجي على الحالات** — نموذج StoryReaction + route `/stories/<sid>/react` + واجهة تفاعلية
- **ترقية المستخدمين إلى مشرفين** — route `/admin/users/<uid>/promote` مع 5 صلاحيات + نافذة modal في صفحة المستخدمين
- **إصلاح البوت** — لا يتوقف إن غاب OPENROUTER_KEY، يعتمد على g4f كبديل وحيد
- **بانر PWA محسّن** — تصميم جديد بتدرج أرجواني + أيقونة هدف + توهج للزر الذهبي

## أوامر البوت الجديدة (للمالك فقط)
| الأمر | الوظيفة |
|-------|---------|
| `/platform` | قائمة منصة رواد التحصيلي وإحصائياتها |
| `/daily physics\|chemistry\|biology\|math` | تدريب يومي من أسئلة المنصة |
| `/assessment physics\|...` | اختبار تقييم المستوى |
| `/ch1 physics\|...` | أسئلة الفصل الأول |
| `/ch2 physics\|...` | أسئلة الفصل الثاني |
| `/live physics 10` | بدء اختبار مباشر في المجموعة |
| `/next` | السؤال التالي في الاختبار المباشر |
| `/leaderboard` | الترتيب الحالي أثناء الاختبار |
| `/endlive` | إنهاء الاختبار وعرض النتائج النهائية |

---

## بنية الملفات

```
├── run_platform.py          # نقطة تشغيل المنصة (المنفذ 5000)
├── bot.py                   # بوت تيليجرام (للنشر فقط)
├── status.py                # مراقبة البوت (workflow)
├── coach_tahseeli/
│   ├── app.py               # مصنع التطبيق Flask
│   ├── extensions.py        # db, login_manager, mail
│   ├── models/
│   │   ├── user.py          # نموذج المستخدم
│   │   ├── question.py      # نموذج السؤال
│   │   ├── evaluation.py    # نموذج التقييم
│   │   └── competition.py   # نموذج المسابقة
│   ├── routes/
│   │   ├── auth.py          # تسجيل/دخول/OTP
│   │   ├── student.py       # لوحة الطالب/اختبارات
│   │   ├── admin.py         # لوحة المشرف
│   │   ├── ai.py            # خدمات الذكاء الاصطناعي
│   │   └── competition.py   # المسابقات
│   ├── services/
│   │   ├── ai_service.py    # OpenRouter API
│   │   ├── email_service.py # Gmail SMTP
│   │   ├── question_service.py
│   │   ├── assessment_service.py
│   │   └── competition_service.py
│   ├── data/
│   │   ├── level_assessment/ # 40 سؤال تحديد مستوى
│   │   └── exams/            # 80 سؤال اختبارات (4 مواد × 2 فصول × 10)
│   ├── templates/           # 20+ قالب HTML عربي RTL
│   └── static/css/style.css # تصميم داكن احترافي
```

---

## إعدادات البيئة

| المتغير | القيمة |
|---------|--------|
| BOT_TOKEN | مفتاح بوت تيليجرام (secret) |
| OPENROUTER_KEY | مفتاح OpenRouter AI (secret) |
| MAIL_SERVER | smtp.gmail.com |
| MAIL_PORT | 587 |
| MAIL_USERNAME | abdualkhaliqali115@gmail.com |
| MAIL_PASSWORD | كلمة مرور التطبيق (secret) |

---

## الـ Workflows

| الاسم | الأمر | الغرض |
|-------|-------|--------|
| Start application | python run_platform.py | المنصة (المنفذ 5000) |
| Bot Status | python status.py | مراقبة البوت فقط |

---

## بيانات المشرف
- **البريد:** admin@rowadtahseeli.sa
- **كلمة المرور:** Admin@2025

---

## التقنيات المستخدمة
- **Backend:** Flask + SQLAlchemy + Flask-Login + Flask-Mail
- **قاعدة البيانات:** SQLite (tahseeli.db)
- **الذكاء الاصطناعي:** OpenRouter (Llama 3.8B + Claude 3 Haiku)
- **البريد:** Gmail SMTP (App Password)
- **التصميم:** Dark Theme, Tajawal Font, RTL, CSS Custom

## نظام الألوان
- خلفية: `#080B14`
- بطاقات: `#111827`
- ذهبي: `#FFB800`
- سماوي: `#00E5FF`
- بنفسجي: `#7C3AED`
- أخضر: `#10B981`

---

## حالة المنصة
- ✅ البريد الإلكتروني يعمل (OTP + نتائج)
- ✅ لوحة المشرف تعمل
- ✅ نظام التسجيل والتحقق يعمل
- ✅ نظام الاختبارات يعمل
- ✅ المسابقات محضّرة

## بنك الأسئلة (الحالة الحالية)
| المادة | الصف | عدد الأسئلة | التفاصيل |
|--------|------|-------------|----------|
| أحياء | الصف 10 (grade='1') | 177 | easy=49, medium=64, hard=64 |
| أحياء | الصف 11 (grade='2') | 576 | easy=146, medium=154, hard=276 |
| أحياء | الصف 12 (grade='3') | 428 | easy=118, medium=113, hard=197 — 5 نماذج |
| **أحياء — الإجمالي** | | **1181** | |
| فيزياء | صف 10+11+12 | ~1213 | مستورد |
| كيمياء | الصف 10 (grade='1') — نماذج 1-4 | 383 | easy=44, medium=69, hard=270 |
| كيمياء | الصف 11 (grade='2') — نماذج 1-6 | 626 | easy=74, medium=100, hard=452 |
| كيمياء | الصف 12 (grade='3') — نماذج 1-5 | 455 | easy=50, medium=66, hard=339 |
| رياضيات | الصف 10 (grade='1') — فصل1 نماذج1-3 + فصل2 نماذج1-3 | 696 | easy=117, medium=117, hard=462 |
| رياضيات | الصف 11 (grade='2') — فصل1 نماذج1-3 + فصل2 نماذج1-3 | 594 | easy=97, medium=103, hard=394 |
| رياضيات | الصف 12 (grade='3') — فصل1 نماذج1-4 + فصل2 نماذج1-3 | 719 | easy=131, medium=136, hard=452 |
- تعيين grade: '1'=صف10، '2'=صف11، '3'=صف12
