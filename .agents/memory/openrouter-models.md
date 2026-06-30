---
name: OpenRouter free models
description: النماذج المجانية تتغير — كيفية اختبارها وتحديثها
---

النماذج القديمة التي توقفت:
- `meta-llama/llama-3-8b-instruct:free` → 404
- `google/gemma-2-9b-it:free` → 404
- `mistralai/mistral-7b-instruct:free` → 404

النماذج الشغّالة (جرّبت في يونيو 2026):
- `google/gemma-4-31b-it:free` ✅
- `openai/gpt-oss-20b:free` ✅
- `openai/gpt-oss-120b:free` (احتياطي)

**Why:** النماذج المجانية على OpenRouter تتبدل كل بضعة أشهر دون إشعار.

**How to apply:** عند فشل AI، شغّل هذا السكريبت للتحقق:
```
python3 -c "import os,requests; r=requests.get('https://openrouter.ai/api/v1/models',headers={'Authorization':'token '+os.getenv('OPENROUTER_KEY','')},timeout=20); print([m['id'] for m in r.json().get('data',[]) if ':free' in m.get('id','')][:10])"
```

ملاحظة: X-Title header يجب أن يكون ASCII فقط (لا عربية في HTTP headers).
