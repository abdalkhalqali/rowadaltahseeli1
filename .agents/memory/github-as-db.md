---
name: GitHub as database for Render persistence
description: نظام data_store لحفظ البيانات في GitHub لتبقى عند نشر Render
---

## المشاكل التي حُلّت

### مشكلة 1: questions.json يتجاوز حد GitHub API (1MB)
- GitHub Contents API لا تقبل ملفات أكبر من 1MB بعد Base64
- questions.json كان 3.57MB → 4.76MB base64 → يفشل صامتاً
- **الحل:** تقسيم حسب المادة والصف → 12 ملف كل منها < 500KB b64

### مشكلة 2: auto_sync يمسح ما رفعه Render
- auto_sync يعمل على Replit كل 2 دقيقة ويفعل force-push بملفات Replit
- لو سجّل مستخدم جديد على Render ورُفع users.json من Render → auto_sync يأتي بعدها ويمسحه بنسخة Replit القديمة
- **الحل:** استثناء data_store/ من auto_sync تماماً (السطر: `if item in ('.git', '.local', '.github', 'data_store'):`)

### مشكلة 3: race condition في رفع GitHub (409)
- threads متوازية تتعارض على SHA عند رفع ملفات متعددة في نفس الوقت
- **الحل:** `threading.Lock()` → الرفع sequential + retry حتى 3 مرات عند 409

## هيكل الملفات الحالي

```
data_store/
├── users.json                   # المستخدمون (~5KB)
├── lectures.json                # المحاضرات (~5KB)
├── config.json                  # مفتاح AI
├── questions_physics_g1.json    # فيزياء صف 10
├── questions_physics_g2.json    # فيزياء صف 11
├── questions_physics_g3.json    # فيزياء صف 12
├── questions_chemistry_g1.json  # كيمياء صف 10
├── questions_chemistry_g2.json  # كيمياء صف 11
├── questions_chemistry_g3.json  # كيمياء صف 12
├── questions_biology_g1.json    # أحياء صف 10
├── questions_biology_g2.json    # أحياء صف 11
├── questions_biology_g3.json    # أحياء صف 12
├── questions_math_g1.json       # رياضيات صف 10
├── questions_math_g2.json       # رياضيات صف 11
└── questions_math_g3.json       # رياضيات صف 12
```

## المبدأ الأساسي
- data_store/ مستثنى من auto_sync (يُدار فقط عبر GitHub API)
- JSON مضغوط (بدون indent) لتقليل الحجم
- عند startup: `_ensure_local()` يجلب من GitHub API إن غاب الملف محلياً
- عند كل تغيير: يُكتب محلياً + يُرفع لـ GitHub في thread خلفي مع lock

**Why:** auto_sync يعمل على Replit فقط. Render يُحدّث GitHub مباشرة. لو كلاهما يكتب نفس الملفات → race condition يمسح البيانات.

**How to apply:** قبل أي نشر Render → اضغط "تصدير كل البيانات" من لوحة المشرف → ينتظر GitHub API يرفع كل الملفات → ثم يُنشَر على Render.
