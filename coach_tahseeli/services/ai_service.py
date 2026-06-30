import os, json, requests, logging

def _load_key():
    try:
        from services.data_store import get_ai_key
        return get_ai_key()
    except Exception:
        return os.getenv('OPENROUTER_KEY', '')

OPENROUTER_KEY = os.getenv('OPENROUTER_KEY', '')
OR_URL         = 'https://openrouter.ai/api/v1/chat/completions'

# نماذج مجانية بالترتيب — يُجرَّب الأول فإن فشل يُجرَّب التالي
FREE_MODELS = [
    'google/gemma-4-31b-it:free',
    'openai/gpt-oss-20b:free',
    'openai/gpt-oss-120b:free',
]

# نموذج للتوليد المتقدم (مجاني أيضاً)
CHAT_MODEL = FREE_MODELS[0]
GEN_MODEL  = FREE_MODELS[0]

def _call_ai(messages, model=None, max_tokens=2000):
    import os as _os
    key = _load_key() or _os.getenv('OPENROUTER_KEY', OPENROUTER_KEY)
    models_to_try = [model] if model and ':free' in model else FREE_MODELS

    # ① OpenRouter إن وُجد المفتاح
    if key:
        for m in models_to_try:
            try:
                r = requests.post(OR_URL, json={
                    'model': m,
                    'messages': messages,
                    'max_tokens': max_tokens,
                    'temperature': 0.7
                }, headers={
                    'Authorization': f'Bearer {key}',
                    'Content-Type': 'application/json',
                    'HTTP-Referer': 'https://rowadtahseeli.sa',
                    'X-Title': 'Rowad Tahseeli',
                }, timeout=45)
                data = r.json()
                if r.status_code == 200:
                    content = data['choices'][0]['message']['content']
                    if content and len(content.strip()) > 3:
                        return content.strip()
                logging.warning(f'AI model {m}: {r.status_code} {data.get("error",{}).get("message","")}')
            except Exception as e:
                logging.warning(f'AI model {m} error: {e}')
                continue

    # ② g4f Qwen كبديل مجاني
    try:
        from g4f.client import Client as G4FClient
        import g4f.Provider as P
        for prov, gmodel in [(P.Qwen_Qwen_3, 'qwen3-235b-a22b'), (P.HuggingSpace, 'Qwen/Qwen2.5-72B-Instruct')]:
            try:
                last_user = next((m['content'] for m in reversed(messages) if m['role'] == 'user'), '')
                sys_msg   = next((m['content'] for m in messages if m['role'] == 'system'), '')
                simple = [{'role': 'system', 'content': sys_msg[:300]}, {'role': 'user', 'content': last_user}]
                c    = G4FClient(provider=prov)
                resp = c.chat.completions.create(model=gmodel, messages=simple, timeout=25)
                text = (resp.choices[0].message.content or '').strip()
                if len(text) > 5:
                    return text
            except Exception:
                continue
    except Exception:
        pass

    logging.error('All AI models failed')
    return None

def evaluate_level_with_ai(subject, answers: dict) -> dict:
    subject_ar = {'physics': 'الفيزياء', 'chemistry': 'الكيمياء',
                  'biology': 'الأحياء', 'math': 'الرياضيات'}.get(subject, subject)
    correct = sum(1 for v in answers.values() if v.get('is_correct'))
    total   = len(answers)
    pct     = round((correct / total) * 100) if total else 0

    if pct >= 85:
        level = 'advanced'
        level_ar = 'متقدم'
    elif pct >= 60:
        level = 'intermediate'
        level_ar = 'متوسط'
    else:
        level = 'beginner'
        level_ar = 'مبتدئ'

    prompt = f"""أنت مساعد تعليمي للطلاب السعوديين. أجب باللغة العربية فقط.
الطالب أجرى اختبار تقييم في مادة {subject_ar}.
النتيجة: {correct} من {total} ({pct}%).
المستوى: {level_ar}.

قدّم:
1. تحليل موجز للأداء (3 جمل)
2. نقاط القوة
3. نقاط الضعف
4. توصيات للتحسين (3 نقاط)

أجب بصيغة JSON فقط:
{{"analysis":"...", "strengths":"...", "weaknesses":"...", "recommendations":["...","...","..."]}}"""

    reply = _call_ai([{'role': 'user', 'content': prompt}], model=GEN_MODEL)
    try:
        start = reply.index('{')
        end   = reply.rindex('}') + 1
        result = json.loads(reply[start:end])
    except Exception:
        result = {
            'analysis': f'حصلت على {pct}% في مادة {subject_ar}.',
            'strengths': 'استمر في التدريب',
            'weaknesses': 'راجع الوحدات التي أخفقت فيها',
            'recommendations': ['راجع الكتاب المدرسي', 'حل تمارين إضافية', 'اسأل معلمك']
        }
    result['level'] = level
    result['level_ar'] = level_ar
    result['score_pct'] = pct
    return result

def generate_questions_from_text(text: str, subject: str, count: int = 10) -> list:
    subject_ar = {'physics': 'الفيزياء', 'chemistry': 'الكيمياء',
                  'biology': 'الأحياء', 'math': 'الرياضيات'}.get(subject, subject)

    prompt = f"""أنت خبير في إعداد أسئلة اختبار التحصيلي السعودي.
المادة: {subject_ar}
المحتوى التعليمي:
{text[:3000]}

أنشئ {count} أسئلة اختيار من متعدد (4 خيارات) باللغة العربية.
كل سؤال يجب أن يكون في صيغة JSON:
[{{"text":"نص السؤال","option_a":"...","option_b":"...","option_c":"...","option_d":"...","answer":"A","explanation":"..."}}]
أجب بمصفوفة JSON فقط بدون أي نص إضافي."""

    reply = _call_ai([{'role': 'user', 'content': prompt}], model=GEN_MODEL, max_tokens=4000)
    try:
        start = reply.index('[')
        end   = reply.rindex(']') + 1
        return json.loads(reply[start:end])
    except Exception:
        return []

def get_study_recommendations(level: str, weak_subjects: list) -> list:
    if not weak_subjects:
        return [
            'واصل تمرينك اليومي للحفاظ على مستواك',
            'جرّب اختبارات المسابقات لاختبار نفسك',
            'راجع الأخطاء الشائعة في كل مادة'
        ]

    weak_ar = [{'physics': 'الفيزياء', 'chemistry': 'الكيمياء',
                 'biology': 'الأحياء', 'math': 'الرياضيات'}.get(s, s) for s in weak_subjects]

    prompt = f"""أنت مدرب تحصيلي سعودي خبير.
مستوى الطالب: {level}
نقاط الضعف: {', '.join(weak_ar)}

قدم 5 توصيات دراسية محددة وعملية باللغة العربية.
أجب بمصفوفة JSON فقط: ["توصية 1", "توصية 2", ...]"""

    reply = _call_ai([{'role': 'user', 'content': prompt}])
    try:
        start = reply.index('[')
        end   = reply.rindex(']') + 1
        return json.loads(reply[start:end])
    except Exception:
        return [
            f'ركّز على مراجعة {weak_ar[0]} يومياً لمدة 30 دقيقة',
            'حل 10 أسئلة تحصيلي يومية',
            'استخدم تقنية التكرار المتباعد',
            'راجع الأخطاء فور الانتهاء من كل اختبار',
            'اشترك في مسابقات المنصة لقياس تقدمك'
        ]

def fix_import_code(code: str) -> dict:
    """يصحّح كود JSON/Python يحتوي على قائمة أسئلة."""
    prompt = f"""أنت مساعد برمجي متخصص في تصحيح بيانات الأسئلة التعليمية.

المستخدم لديه كود يحتوي على قائمة أسئلة اختيار من متعدد بصيغة JSON أو Python.

الكود المُدخَل:
{code[:8000]}

مطلوب منك:
1. تصحيح أي أخطاء في صيغة JSON أو Python
2. التأكد من وجود الحقول المطلوبة لكل سؤال: text, option_a, option_b, option_c, option_d, answer
3. إصلاح قيم answer لتكون A أو B أو C أو D فقط (حرف كبير)
4. الحقول الاختيارية: explanation, difficulty (easy/medium/hard), lesson, chapter
5. إزالة أي حقول غير صالحة

أجب بهذا التنسيق JSON فقط بدون أي نص إضافي:
{{"fixed_code": "[...مصفوفة JSON مصحّحة...]", "errors_found": ["خطأ 1", "خطأ 2"], "questions_count": 0, "summary": "ملخص قصير"}}"""

    reply = _call_ai([{'role': 'user', 'content': prompt}], max_tokens=8000)
    if not reply:
        return {'fixed_code': code, 'errors_found': [], 'questions_count': 0, 'summary': 'لم يتمكن المساعد من التحليل حالياً'}
    try:
        start = reply.index('{')
        end   = reply.rindex('}') + 1
        return json.loads(reply[start:end])
    except Exception:
        return {'fixed_code': reply, 'errors_found': [], 'questions_count': 0, 'summary': 'تم التصحيح'}

def ai_chat(message: str, subject: str, student_name: str) -> str:
    subject_ar = {'physics': 'الفيزياء', 'chemistry': 'الكيمياء',
                  'biology': 'الأحياء', 'math': 'الرياضيات',
                  'general': 'عام'}.get(subject, subject)

    system = f"""أنت مساعد تعليمي ذكي لمنصة رواد التحصيلي الاحترافية.
تتحدث مع الطالب {student_name} وتساعده في {subject_ar}.
أجب دائماً باللغة العربية الفصحى بأسلوب واضح ومشجع.
قدّم شرحاً علمياً دقيقاً مع أمثلة توضيحية عند الحاجة."""

    reply = _call_ai([
        {'role': 'system', 'content': system},
        {'role': 'user',   'content': message}
    ])
    return reply or 'عذراً، حدث خطأ. حاول مرة أخرى.'
