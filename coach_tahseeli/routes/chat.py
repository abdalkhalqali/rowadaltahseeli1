from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.chat_message import ChatMessage
from datetime import date, datetime
import json, logging

chat_bp = Blueprint('chat', __name__)

# ─── استدعاء الذكاء الاصطناعي ────────────────────────────────────────────────
def _ai_call(messages: list) -> str:
    import requests as rq, os

    # ① OpenRouter — الأولوية القصوى (موثوق، سريع، مجاني بمفتاح)
    try:
        from services.data_store import get_ai_key as _get_key
        key = _get_key()
    except Exception:
        key = os.getenv('OPENROUTER_KEY', '')
    if key:
        for model in [
            'google/gemma-4-31b-it:free',
            'openai/gpt-oss-20b:free',
            'openai/gpt-oss-120b:free',
        ]:
            try:
                r = rq.post(
                    'https://openrouter.ai/api/v1/chat/completions',
                    json={'model': model, 'messages': messages[-10:], 'max_tokens': 1200},
                    headers={
                        'Authorization': f'Bearer {key}',
                        'Content-Type': 'application/json',
                        'HTTP-Referer': 'https://rowadtahseeli.sa',
                        'X-Title': 'Rowad Tahseeli',
                    },
                    timeout=40,
                )
                if r.status_code == 200:
                    content = r.json()['choices'][0]['message']['content']
                    if content and len(content.strip()) > 3:
                        logging.info(f'AI: OpenRouter/{model} OK')
                        return content.strip()
                else:
                    logging.warning(f'OpenRouter {model}: {r.status_code} {r.text[:80]}')
            except Exception as e:
                logging.warning(f'OpenRouter {model}: {e}')
                continue

    # ② g4f — Qwen (Alibaba) كخيار ثانٍ لا يحجب IPs الخوادم
    try:
        from g4f.client import Client as G4FClient
        import g4f.Provider as P
        for prov, model in [
            (P.Qwen_Qwen_3, 'qwen3-235b-a22b'),
            (P.Qwen_Qwen_2_72B, 'Qwen2.5-72B-Instruct'),
            (P.HuggingSpace, 'Qwen/Qwen2.5-72B-Instruct'),
        ]:
            try:
                c = G4FClient(provider=prov)
                resp = c.chat.completions.create(model=model, messages=messages[-6:], timeout=25)
                text = (resp.choices[0].message.content or '').strip()
                if len(text) > 5:
                    logging.info(f'AI: g4f/{prov.__name__} OK')
                    return text
            except Exception as e:
                logging.warning(f'g4f {prov.__name__}: {e}')
                continue
    except Exception as e:
        logging.warning(f'g4f import error: {e}')

    # ③ Pollinations (من المتصفح يعمل بشكل أفضل — هذا للخادم فقط كملاذ أخير)
    try:
        import urllib.request, urllib.parse
        last_user = next((m['content'] for m in reversed(messages) if m['role'] == 'user'), '')
        system_msg = next((m['content'] for m in messages if m['role'] == 'system'), '')
        full_prompt = (system_msg[:200] + '\n\n' + last_user)[:700]
        encoded = urllib.parse.quote(full_prompt)
        url = f'https://text.pollinations.ai/{encoded}?model=openai&seed={hash(last_user) % 9999}'
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read().decode('utf-8').strip()
            if len(text) > 5:
                logging.info('AI: Pollinations OK')
                return text
    except Exception as e:
        logging.warning(f'Pollinations: {e}')

    return None

# ─── بناء سياق الطالب ──────────────────────────────────────────────────────
def _build_context(user, lecture_id=None) -> str:
    # مستوى الطالب ودرجته
    level_ar = {
        'beginner': 'مبتدئ',
        'intermediate': 'متوسط',
        'advanced': 'متقدم',
    }
    user_level = level_ar.get(getattr(user, 'level', ''), getattr(user, 'level', 'غير محدد'))

    lines = [
        f'أنت مساعد تعليمي ذكي لمنصة "رواد التحصيلي" السعودية.',
        f'اسم الطالب: {user.name}.',
        f'مستوى الطالب الحالي: {user_level}.',
        'أجب دائماً بالعربية بأسلوب واضح، مشجّع، وتعليمي.',
        'عندما تشرح مفاهيم علمية اضرب أمثلة عملية.',
        'خاطب الطالب بشكل شخصي وقدّم نصائح مبنية على بياناته الفعلية.',
        '',
    ]

    # حالة التدريب اليومي
    try:
        from models.pro_license_question import DailyTrainingSession
        today_s = DailyTrainingSession.query.filter_by(
            user_id=user.id, exam_date=date.today()
        ).first()
        last_s = DailyTrainingSession.query.filter_by(
            user_id=user.id
        ).order_by(DailyTrainingSession.created_at.desc()).first()

        if today_s and today_s.completed:
            lines.append(f'✅ الطالب أكمل تدريب اليوم (اليوم {today_s.day_num}) بنتيجة {today_s.score_pct}%.')
        elif today_s:
            lines.append(f'⏳ الطالب بدأ تدريب اليوم {today_s.day_num} لكن لم يكمله بعد.')
        elif last_s:
            lines.append(f'ℹ️ آخر تدريب للطالب كان اليوم {last_s.day_num} بتاريخ {last_s.exam_date} بنتيجة {last_s.score_pct}%.')
            wrong = json.loads(last_s.wrong_ids or '[]')
            if wrong:
                lines.append(f'أخطأ في {len(wrong)} سؤال في آخر جلسة.')
        else:
            lines.append('الطالب لم يبدأ التدريب اليومي بعد.')
    except Exception:
        pass

    # نقاط الضعف من الرخصة المهنية
    try:
        from models.pro_license_question import ProLicenseResult, PRO_STANDARDS
        results = ProLicenseResult.query.filter_by(
            user_id=user.id, exam_type='standard'
        ).order_by(ProLicenseResult.created_at.desc()).limit(20).all()

        weak = {}
        for r in results:
            if r.total and r.standard_num:
                pct = r.score_pct
                sname = PRO_STANDARDS.get(r.standard_num, {}).get('name', f'معيار {r.standard_num}')
                if r.standard_num not in weak or weak[r.standard_num]['pct'] > pct:
                    weak[r.standard_num] = {'name': sname, 'pct': pct}

        strong = [(v['name'], v['pct']) for v in weak.values() if v['pct'] >= 70]
        real_weak = [(v['name'], v['pct']) for v in weak.values() if v['pct'] < 70]
        real_weak.sort(key=lambda x: x[1])
        if real_weak:
            ws = ', '.join(f'{n} ({p}%)' for n, p in real_weak[:4])
            lines.append(f'نقاط ضعف الطالب في الرخصة المهنية: {ws}.')
        if strong:
            ss = ', '.join(f'{n} ({p}%)' for n, p in strong[:3])
            lines.append(f'نقاط قوة الطالب في الرخصة المهنية: {ss}.')
    except Exception:
        pass

    # آخر نتائج اختبارات التحصيلي
    try:
        from models.evaluation import Evaluation
        subj_ar = {'physics': 'الفيزياء', 'chemistry': 'الكيمياء',
                   'biology': 'الأحياء', 'math': 'الرياضيات'}
        recent_evals = (Evaluation.query
            .filter_by(user_id=user.id)
            .order_by(Evaluation.created_at.desc())
            .limit(8).all())
        if recent_evals:
            lines.append('\n📊 آخر نتائج اختبارات التحصيلي للطالب:')
            for ev in recent_evals:
                s = subj_ar.get(ev.subject, ev.subject)
                etype = {'daily_train': 'تدريب يومي', 'level_test': 'تقييم مستوى',
                         'smart_daily': 'ذكي يومي'}.get(ev.exam_type, ev.exam_type)
                lines.append(f'   • {s} ({etype}): {ev.score_pct}% ({ev.correct}/{ev.total_q} صحيح)')
            avg = sum(ev.score_pct for ev in recent_evals) / len(recent_evals)
            lines.append(f'   متوسط أداء التحصيلي: {avg:.1f}%')
            if avg < 50:
                lines.append('   ⚠️ الطالب بحاجة ماسّة للتدريب المكثّف في التحصيلي — ركّز على نقاط ضعفه.')
            elif avg < 70:
                lines.append('   📈 مستوى الطالب متوسط في التحصيلي — شجّعه على الاستمرار والتدريب اليومي.')
            else:
                lines.append('   ✅ الطالب بمستوى جيد في التحصيلي — حثّه على رفع مستواه للمستوى المتقدم.')
    except Exception:
        pass

    # سياق المحاضرة المفتوحة حالياً
    if lecture_id:
        try:
            from models.lecture import Lecture
            lec = Lecture.query.get(int(lecture_id))
            if lec:
                lines.append(f'\n📺 الطالب يشاهد الآن محاضرة: "{lec.title}"')
                if lec.subject:
                    subj_ar = {'physics':'فيزياء','chemistry':'كيمياء','biology':'أحياء','math':'رياضيات'}.get(lec.subject, lec.subject)
                    lines.append(f'   المادة: {subj_ar}')
                if lec.standard:
                    lines.append(f'   المعيار: {lec.standard}')
                if lec.transcript and lec.transcript.strip():
                    lines.append('   نص المحاضرة المفرَّغ صوتياً:')
                    lines.append(lec.transcript[:4000])
                    lines.append('   → أجب على أسئلة الطالب بالاستناد لهذا النص أولاً.')
        except Exception:
            pass

    # تاريخ المحاضرات التي شاهدها الطالب (آخر 5)
    try:
        from models.lecture import Lecture, LectureView
        recent_views = (LectureView.query
            .filter_by(user_id=user.id)
            .order_by(LectureView.last_seen.desc())
            .limit(5).all())
        if recent_views:
            lines.append('\n📚 آخر محاضرات شاهدها الطالب:')
            for v in recent_views:
                lec_obj = Lecture.query.get(v.lecture_id)
                if lec_obj:
                    mins = v.watch_secs // 60
                    status = '✅ أكمل' if v.completed else f'⏱ شاهد {mins} دقيقة من'
                    lines.append(f'   • {status} "{lec_obj.title}"')
    except Exception:
        pass

    return '\n'.join(lines)

# ─── endpoint وكيل الذكاء الاصطناعي على الخادم (الأفضل أداءً) ─────────────
@chat_bp.route('/api/chat/ai', methods=['POST'])
@login_required
def ai_proxy():
    """وكيل AI على الخادم — يستدعي Pollinations أو OpenRouter مباشرة"""
    data     = request.get_json(silent=True) or {}
    messages = data.get('messages', [])
    if not messages:
        return jsonify({'error': 'لا توجد رسائل'}), 400

    reply = _ai_call(messages)
    if reply:
        return jsonify({'reply': reply})
    return jsonify({'error': 'فشل AI'}), 503


# ─── جلب السياق + التاريخ (يُستخدم من المتصفح لاستدعاء AI مباشرة) ──────────
@chat_bp.route('/api/chat/context', methods=['POST'])
@login_required
def get_context():
    data       = request.get_json(silent=True) or {}
    message    = (data.get('message') or '').strip()
    lecture_id = data.get('lecture_id')
    if not message:
        return jsonify({'error': 'رسالة فارغة'}), 400

    # أوامر سريعة (تُعالَج على الخادم فوراً)
    if message.startswith('/'):
        cmd = message.strip().lower()
        if cmd == '/help':
            reply = (
                '**الأوامر المتاحة:**\n'
                '• `/status` — حالة تدريبك اليومي\n'
                '• `/help` — قائمة المساعدة\n\n'
                'يمكنك أيضاً سؤالي عن:\n'
                '• شرح مفاهيم الفيزياء أو الرياضيات\n'
                '• تفسير أسئلة الرخصة المهنية\n'
                '• خطة مراجعة ونقاط الضعف\n'
                '• أي شيء يخص المحاضرة التي تشاهدها'
            )
        elif cmd == '/status':
            try:
                from models.pro_license_question import DailyTrainingSession
                today_s = DailyTrainingSession.query.filter_by(
                    user_id=current_user.id, exam_date=date.today()
                ).first()
                last_s = DailyTrainingSession.query.filter_by(
                    user_id=current_user.id
                ).order_by(DailyTrainingSession.created_at.desc()).first()
                if today_s and today_s.completed:
                    reply = f'✅ أكملت تدريب اليوم! اليوم {today_s.day_num} · النتيجة: {today_s.score_pct}%'
                elif today_s:
                    reply = f'⏳ بدأت تدريب اليوم {today_s.day_num} لكنه غير مكتمل.'
                elif last_s:
                    reply = f'📅 آخر تدريب: اليوم {last_s.day_num} — {last_s.score_pct}%\n🔔 لم تتدرب اليوم بعد!'
                else:
                    reply = '📚 لم تبدأ أي تدريب يومي. اذهب إلى الرخصة المهنية!'
            except Exception:
                reply = 'تعذّر جلب بيانات التدريب.'
        else:
            reply = f'الأمر "{cmd}" غير معروف. اكتب `/help` لرؤية الأوامر.'
        _save(current_user.id, message, reply, lecture_id)
        return jsonify({'quick_reply': reply})

    # حفظ رسالة المستخدم
    db.session.add(ChatMessage(user_id=current_user.id, role='user',
                               content=message, lecture_id=lecture_id))
    db.session.commit()

    # بناء السياق
    system_ctx = _build_context(current_user, lecture_id)

    # تاريخ المحادثة (آخر 12 رسالة)
    history = ChatMessage.query.filter_by(
        user_id=current_user.id
    ).order_by(ChatMessage.created_at.desc()).limit(14).all()

    ai_messages = [{'role': 'system', 'content': system_ctx}]
    for h in reversed(history[1:]):
        if h.role in ('user', 'assistant'):
            ai_messages.append({'role': h.role, 'content': h.content[:600]})
    ai_messages.append({'role': 'user', 'content': message})

    return jsonify({'messages': ai_messages, 'lecture_id': lecture_id})


# ─── حفظ رد AI بعد إرساله من المتصفح ───────────────────────────────────────
@chat_bp.route('/api/chat/save', methods=['POST'])
@login_required
def save_reply():
    data       = request.get_json(silent=True) or {}
    reply      = (data.get('reply') or '').strip()
    lecture_id = data.get('lecture_id')
    if not reply:
        return jsonify({'ok': False}), 400
    db.session.add(ChatMessage(user_id=current_user.id, role='assistant',
                               content=reply, lecture_id=lecture_id))
    db.session.commit()
    return jsonify({'ok': True})


# ─── إرسال رسالة (احتياطي على الخادم) ────────────────────────────────────
@chat_bp.route('/api/chat/send', methods=['POST'])
@login_required
def send_message():
    data       = request.get_json(silent=True) or {}
    message    = (data.get('message') or '').strip()
    lecture_id = data.get('lecture_id')
    if not message:
        return jsonify({'error': 'رسالة فارغة'}), 400

    # احصل على السياق بنفس منطق /context
    ctx_resp = get_context.__wrapped__ if hasattr(get_context, '__wrapped__') else None
    db.session.add(ChatMessage(user_id=current_user.id, role='user',
                               content=message, lecture_id=lecture_id))
    db.session.commit()

    system_ctx = _build_context(current_user, lecture_id)
    history = ChatMessage.query.filter_by(
        user_id=current_user.id
    ).order_by(ChatMessage.created_at.desc()).limit(14).all()
    ai_messages = [{'role': 'system', 'content': system_ctx}]
    for h in reversed(history[1:]):
        if h.role in ('user', 'assistant'):
            ai_messages.append({'role': h.role, 'content': h.content[:600]})
    ai_messages.append({'role': 'user', 'content': message})

    reply = _ai_call(ai_messages) or 'عذراً، المساعد الذكي مشغول حالياً. حاول مرة أخرى.'
    db.session.add(ChatMessage(user_id=current_user.id, role='assistant',
                               content=reply, lecture_id=lecture_id))
    db.session.commit()
    return jsonify({'reply': reply})

# ─── جلب آخر الرسائل ───────────────────────────────────────────────────────
@chat_bp.route('/api/chat/history')
@login_required
def get_history():
    msgs = ChatMessage.query.filter_by(
        user_id=current_user.id
    ).order_by(ChatMessage.created_at.desc()).limit(30).all()

    return jsonify([{
        'role'      : m.role,
        'content'   : m.content,
        'created_at': m.created_at.strftime('%H:%M'),
    } for m in reversed(msgs)])

# ─── حالة التذكير ──────────────────────────────────────────────────────────
@chat_bp.route('/api/chat/status-check')
@login_required
def status_check():
    try:
        from models.pro_license_question import DailyTrainingSession
        today_s = DailyTrainingSession.query.filter_by(
            user_id=current_user.id, exam_date=date.today()
        ).first()
        done = today_s is not None and today_s.completed
        return jsonify({'daily_done': done})
    except Exception:
        return jsonify({'daily_done': True})

# ─── helper ────────────────────────────────────────────────────────────────
def _save(user_id, user_text, bot_text, lecture_id=None):
    db.session.add(ChatMessage(user_id=user_id, role='user', content=user_text, lecture_id=lecture_id))
    db.session.add(ChatMessage(user_id=user_id, role='assistant', content=bot_text, lecture_id=lecture_id))
    db.session.commit()
