"""
code_assistant.py — المساعد البرمجي للمشرف
يقرأ ويعدّل ملفات أي مستودع GitHub بمساعدة الذكاء الاصطناعي المجاني.
"""
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
import os, base64, logging, requests as rq, json as _json

code_assistant_bp = Blueprint('code_assistant', __name__)

MODELS = {
    'auto':       {'label': '🔄 تلقائي — كل النماذج بالترتيب',               'needs_key': False},
    'g4f-qwen3':  {'label': '🟢 Qwen3-235B   (مجاني بلا مفتاح)',              'needs_key': False},
    'g4f-qwen72': {'label': '🟢 Qwen2.5-72B  (مجاني بلا مفتاح)',              'needs_key': False},
    'g4f-only':   {'label': '🟢 g4f فقط      (كل نماذج g4f)',                 'needs_key': False},
    'or-gemma':   {'label': '🔵 Gemma-4-31B  (OpenRouter مجاني بمفتاح)',      'needs_key': True},
    'or-gpt20':   {'label': '🔵 GPT-OSS-20B  (OpenRouter مجاني بمفتاح)',      'needs_key': True},
    'or-gpt120':  {'label': '🔵 GPT-OSS-120B (OpenRouter مجاني بمفتاح)',      'needs_key': True},
    'or-only':    {'label': '🔵 OpenRouter فقط (كل نماذجه)',                   'needs_key': True},
}


def _super_admin_required(f):
    from functools import wraps
    from flask import abort
    from routes.admin import SUPER_ADMIN_EMAIL
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or \
           current_user.email.lower() != SUPER_ADMIN_EMAIL.lower():
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ─── AI call ────────────────────────────────────────────────────────────────

def _call_ai(messages: list, model_id: str = 'auto') -> str:
    try:
        from services.data_store import get_ai_key
        key = get_ai_key()
    except Exception:
        key = os.getenv('OPENROUTER_KEY', '')

    OR_MODELS = [
        'google/gemma-4-31b-it:free',
        'openai/gpt-oss-20b:free',
        'openai/gpt-oss-120b:free',
    ]

    def _or(model_name):
        if not key: return None
        try:
            r = rq.post(
                'https://openrouter.ai/api/v1/chat/completions',
                json={'model': model_name, 'messages': messages[-16:], 'max_tokens': 4000},
                headers={
                    'Authorization': f'Bearer {key}',
                    'Content-Type': 'application/json',
                    'HTTP-Referer': 'https://rowadtahseeli.sa',
                    'X-Title': 'Rowad Code Assistant',
                },
                timeout=90,
            )
            if r.status_code == 200:
                c = r.json()['choices'][0]['message']['content']
                if c and len(c.strip()) > 3:
                    return c.strip()
            else:
                logging.warning(f'OR {model_name}: {r.status_code} {r.text[:80]}')
        except Exception as e:
            logging.warning(f'OR {model_name}: {e}')
        return None

    def _g4f(prov_name=None, model_name=None):
        try:
            from g4f.client import Client as G4FClient
            import g4f.Provider as P
            if prov_name and model_name:
                pairs = [(getattr(P, prov_name, None), model_name)]
                pairs = [(p, m) for p, m in pairs if p]
            else:
                pairs = [
                    (P.Qwen_Qwen_3,    'qwen3-235b-a22b'),
                    (P.Qwen_Qwen_2_72B,'Qwen2.5-72B-Instruct'),
                    (P.HuggingSpace,   'Qwen/Qwen2.5-72B-Instruct'),
                ]
            for prov, mod in pairs:
                try:
                    c = G4FClient(provider=prov)
                    resp = c.chat.completions.create(model=mod, messages=messages[-8:], timeout=40)
                    text = (resp.choices[0].message.content or '').strip()
                    if len(text) > 5: return text
                except Exception: continue
        except Exception as e:
            logging.warning(f'g4f: {e}')
        return None

    dispatch = {
        'auto':      lambda: (any((_or(m) for m in OR_MODELS)) if key else None) or _g4f(),
        'g4f-qwen3': lambda: _g4f('Qwen_Qwen_3', 'qwen3-235b-a22b'),
        'g4f-qwen72':lambda: _g4f('Qwen_Qwen_2_72B', 'Qwen2.5-72B-Instruct'),
        'g4f-only':  lambda: _g4f(),
        'or-gemma':  lambda: _or('google/gemma-4-31b-it:free'),
        'or-gpt20':  lambda: _or('openai/gpt-oss-20b:free'),
        'or-gpt120': lambda: _or('openai/gpt-oss-120b:free'),
        'or-only':   lambda: next((_or(m) for m in OR_MODELS if _or(m)), None),
    }

    # auto needs special handling (try OR first then g4f)
    if model_id == 'auto':
        if key:
            for m in OR_MODELS:
                r = _or(m)
                if r: return r
        r = _g4f()
        return r or 'لم يتمكن الذكاء الاصطناعي من الإجابة حالياً.'

    fn = dispatch.get(model_id)
    if fn:
        r = fn()
        return r or f'فشل النموذج "{model_id}". جرّب نموذجاً آخر.'
    return 'نموذج غير معروف.'


# ─── GitHub helpers ──────────────────────────────────────────────────────────

def _gh_token():
    try:
        from services.data_store import get_github_token
        return get_github_token()
    except Exception:
        return os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN', '')

def _gh_headers():
    t = _gh_token()
    h = {'User-Agent': 'RowadTahseeli-CodeAssistant',
         'Accept': 'application/vnd.github.v3+json'}
    if t:
        h['Authorization'] = f'token {t}'
    return h

def _parse_repo(repo_input: str) -> str:
    """يستخرج owner/repo من رابط GitHub أو من النص المباشر"""
    if not repo_input:
        return 'abdalkhalqali/rowadaltahseeli1'
    s = repo_input.strip().rstrip('/').replace('.git', '')
    if 'github.com/' in s:
        parts = s.split('github.com/')[-1].split('/')
        parts = [p for p in parts if p]  # إزالة الأجزاء الفارغة
        if len(parts) >= 2:
            return f'{parts[0]}/{parts[1]}'
    if '/' in s:
        parts = [p for p in s.split('/') if p]
        if len(parts) >= 2:
            return f'{parts[0]}/{parts[1]}'
    return s

def _gh_read(path, repo):
    url  = f'https://api.github.com/repos/{repo}/contents/{path}'
    resp = rq.get(url, headers=_gh_headers(), timeout=15)
    if resp.status_code == 404:
        return None, 'الملف غير موجود'
    if resp.status_code != 200:
        return None, f'HTTP {resp.status_code}'
    data    = resp.json()
    if isinstance(data, list):
        return None, 'هذا مجلد وليس ملفاً'
    content = base64.b64decode(data['content'].replace('\n', '')).decode('utf-8', errors='replace')
    return {'content': content, 'sha': data['sha'], 'path': path,
            'size': data.get('size', 0), 'repo': repo}, None

def _gh_write(path, content, sha, message, repo):
    url  = f'https://api.github.com/repos/{repo}/contents/{path}'
    body = {
        'message': message or f'code-assistant: edit {path}',
        'content': base64.b64encode(content.encode('utf-8')).decode('ascii'),
        'sha': sha,
    }
    resp = rq.put(url, json=body, headers=_gh_headers(), timeout=30)
    if resp.status_code in (200, 201):
        new_sha = resp.json().get('content', {}).get('sha', sha)
        return True, None, new_sha
    return False, f'HTTP {resp.status_code}: {resp.text[:200]}', sha

def _gh_list(path, repo):
    url  = f'https://api.github.com/repos/{repo}/contents/{path}'
    resp = rq.get(url, headers=_gh_headers(), timeout=15)
    if resp.status_code != 200:
        return None, f'HTTP {resp.status_code}: {resp.text[:100]}'
    data  = resp.json()
    if not isinstance(data, list):
        return None, 'المسار ليس مجلداً'
    items = []
    for item in data:
        items.append({
            'name': item['name'],
            'path': item['path'],
            'type': item['type'],
            'size': item.get('size', 0),
        })
    items.sort(key=lambda x: (0 if x['type'] == 'dir' else 1, x['name'].lower()))
    return items, None

def _gh_default_branch(repo):
    """جلب اسم الفرع الافتراضي للمستودع"""
    resp = rq.get(f'https://api.github.com/repos/{repo}',
                  headers=_gh_headers(), timeout=10)
    if resp.status_code == 200:
        return resp.json().get('default_branch', 'main')
    return 'main'

def _gh_tree(repo):
    """جلب شجرة الملفات الكاملة للمستودع"""
    # أولاً: نجلب الفرع الافتراضي حتى لا نعتمد على HEAD
    branch = _gh_default_branch(repo)
    url  = f'https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1'
    resp = rq.get(url, headers=_gh_headers(), timeout=20)
    if resp.status_code != 200:
        logging.warning(f'_gh_tree {repo}: {resp.status_code} {resp.text[:120]}')
        return None
    tree = resp.json().get('tree', [])
    return [t['path'] for t in tree if t['type'] == 'blob']


# ─── Routes ──────────────────────────────────────────────────────────────────

@code_assistant_bp.route('/admin/code-assistant')
@login_required
@_super_admin_required
def index():
    return render_template('admin_code_assistant.html', models=MODELS)


@code_assistant_bp.route('/admin/code-assistant/chat', methods=['POST'])
@login_required
@_super_admin_required
def chat():
    data         = request.get_json(silent=True) or {}
    messages     = data.get('messages', [])
    model_id     = data.get('model', 'auto')
    repo         = _parse_repo(data.get('repo', ''))
    open_files   = data.get('open_files', [])   # [{path, content}]
    project_map  = data.get('project_map', '')  # نص خريطة المشروع

    if not messages:
        return jsonify({'error': 'لا توجد رسائل'}), 400

    sys_parts = [
        f'أنت مساعد برمجي متقدم لمستودع GitHub: {repo}',
        'قدراتك:',
        '  • قراءة وتعديل ملفات المستودع',
        '  • تحليل الكود وشرحه بالعربية',
        '  • اقتراح تعديلات وإصلاح أخطاء',
        '  • إنشاء ملفات جديدة',
        '',
        'قواعد مهمة:',
        '  • اشرح باللغة العربية، اكتب الكود بالإنجليزية',
        '  • عندما تعدّل ملفاً اذكر اسمه بوضوح في بداية كتلة الكود',
        '  • إذا احتجت فتح ملف اكتب في نهاية ردك: [OPEN_FILE: path/to/file]',
        '  • إذا احتجت فتح عدة ملفات: [OPEN_FILES: file1, file2, file3]',
        '  • إذا كان الكود تعديلاً لملف مفتوح اكتب: [APPLY_TO: filename]',
        '',
    ]

    if project_map:
        sys_parts.append('── خريطة المشروع ──')
        sys_parts.append(project_map[:3000])
        sys_parts.append('')

    if open_files:
        sys_parts.append('── الملفات المفتوحة حالياً ──')
        for f in open_files[:4]:
            sys_parts.append(f'📄 {f["path"]}:')
            sys_parts.append('```')
            sys_parts.append(str(f.get('content', ''))[:3000])
            sys_parts.append('```')
            sys_parts.append('')

    system = '\n'.join(sys_parts)
    ai_messages = [{'role': 'system', 'content': system}] + messages[-20:]
    reply = _call_ai(ai_messages, model_id)
    return jsonify({'reply': reply})


@code_assistant_bp.route('/admin/code-assistant/analyze', methods=['POST'])
@login_required
@_super_admin_required
def analyze():
    data  = request.get_json(silent=True) or {}
    repo  = _parse_repo(data.get('repo', ''))
    model = data.get('model', 'auto')

    files = _gh_tree(repo)
    if not files:
        return jsonify({'error': 'تعذّر جلب شجرة المستودع — تحقق من اسم المستودع والتوكن'}), 400

    tree_text = '\n'.join(files[:300])

    prompt = f"""لديك مستودع GitHub: {repo}
شجرة الملفات:
{tree_text}

قم بتحليل سريع للمشروع وأجب بالعربية بـ:
1. **نوع المشروع وتقنياته الرئيسية**
2. **الملفات الرئيسية** (اذكر كل ملف مهم ووظيفته)
3. **هيكل المجلدات** (شرح كل مجلد رئيسي)
4. **نقاط الدخول** (ملفات البدء والتشغيل)

أجب باختصار ووضوح."""

    summary = _call_ai([{'role': 'user', 'content': prompt}], model)
    return jsonify({
        'repo': repo,
        'files': files,
        'file_count': len(files),
        'summary': summary,
        'tree_text': tree_text[:2000],
    })


@code_assistant_bp.route('/admin/code-assistant/files')
@login_required
@_super_admin_required
def list_files():
    path  = request.args.get('path', '')
    repo  = _parse_repo(request.args.get('repo', ''))
    items, err = _gh_list(path, repo)
    if err:
        return jsonify({'error': err}), 400
    return jsonify({'items': items, 'path': path, 'repo': repo})


@code_assistant_bp.route('/admin/code-assistant/file')
@login_required
@_super_admin_required
def read_file():
    path = request.args.get('path', '')
    repo = _parse_repo(request.args.get('repo', ''))
    if not path:
        return jsonify({'error': 'path مطلوب'}), 400
    result, err = _gh_read(path, repo)
    if err:
        return jsonify({'error': err}), 400
    return jsonify(result)


@code_assistant_bp.route('/admin/code-assistant/file', methods=['POST'])
@login_required
@_super_admin_required
def write_file():
    data    = request.get_json(silent=True) or {}
    path    = data.get('path', '')
    content = data.get('content', '')
    sha     = data.get('sha', '')
    message = data.get('message', '')
    repo    = _parse_repo(data.get('repo', ''))
    if not path or not content or not sha:
        return jsonify({'error': 'path + content + sha مطلوبة'}), 400
    ok, err, new_sha = _gh_write(path, content, sha, message, repo)
    if not ok:
        return jsonify({'error': err}), 400
    return jsonify({'success': True, 'msg': f'✅ تم حفظ {path} في GitHub', 'new_sha': new_sha})


@code_assistant_bp.route('/admin/code-assistant/create', methods=['POST'])
@login_required
@_super_admin_required
def create_file():
    data    = request.get_json(silent=True) or {}
    path    = data.get('path', '')
    content = data.get('content', '')
    message = data.get('message', f'feat: create {data.get("path","")}')
    repo    = _parse_repo(data.get('repo', ''))
    if not path or content is None:
        return jsonify({'error': 'path + content مطلوبان'}), 400
    url  = f'https://api.github.com/repos/{repo}/contents/{path}'
    body = {
        'message': message,
        'content': base64.b64encode(content.encode('utf-8')).decode('ascii'),
    }
    resp = rq.put(url, json=body, headers=_gh_headers(), timeout=30)
    if resp.status_code in (200, 201):
        new_sha = resp.json().get('content', {}).get('sha', '')
        return jsonify({'success': True, 'msg': f'✅ تم إنشاء {path}', 'sha': new_sha})
    return jsonify({'error': f'HTTP {resp.status_code}: {resp.text[:150]}'}), 400


@code_assistant_bp.route('/admin/code-assistant/models')
@login_required
@_super_admin_required
def get_models():
    try:
        from services.data_store import get_ai_key
        has_key = bool(get_ai_key())
    except Exception:
        has_key = bool(os.getenv('OPENROUTER_KEY', ''))
    return jsonify({'models': MODELS, 'has_key': has_key})
