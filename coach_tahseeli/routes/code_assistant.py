"""
code_assistant.py — المساعد البرمجي للمشرف (وكيل برمجي متكامل)

• دعم كل مزوّدي الذكاء الاصطناعي:
  OpenAI · Anthropic · Gemini · DeepSeek · Mistral · Groq · xAI · Together · OpenRouter · g4f
• Streaming (SSE) لكل المزوّدين
• وكيل برمجي مستقل: يقرأ الملفات، يحللها، يعدّلها، يرفعها إلى GitHub
• مفاتيح API: تُقرأ من Replit Secrets (env) أولاً ثم ملف محلي آمن
"""
from flask import Blueprint, request, jsonify, render_template, Response, stream_with_context
from flask_login import login_required, current_user
import os, base64, logging, threading, json as _json
import requests as rq

code_assistant_bp = Blueprint('code_assistant', __name__)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# مزودو الذكاء الاصطناعي
# المفتاح يُقرأ من Replit Secrets ويُوضَع في Authorization Header فقط
# لا يُرسَل المفتاح أبداً ضمن نص الرسائل — النماذج لا تراه
# ═══════════════════════════════════════════════════════════════════════════════

PROVIDERS = {
    'openai': {
        'name': 'OpenAI', 'icon': '⚫',
        'env_var': 'OPENAI_KEY',
        'url': 'https://api.openai.com/v1/chat/completions',
        'api_type': 'openai',
        'default_model': 'gpt-4o-mini',
        'models': ['gpt-4o-mini', 'gpt-4o', 'o1-mini', 'o1'],
        'hint': 'platform.openai.com/api-keys',
        'supports_tools': True,
    },
    'anthropic': {
        'name': 'Anthropic Claude', 'icon': '🟤',
        'env_var': 'ANTHROPIC_KEY',
        'url': 'https://api.anthropic.com/v1/messages',
        'api_type': 'anthropic',
        'default_model': 'claude-3-5-haiku-20241022',
        'models': ['claude-3-5-haiku-20241022', 'claude-3-5-sonnet-20241022', 'claude-3-opus-20240229'],
        'hint': 'console.anthropic.com/settings/keys',
        'supports_tools': True,
    },
    'gemini': {
        'name': 'Google Gemini', 'icon': '🔴',
        'env_var': 'GEMINI_API_KEY',
        'api_type': 'gemini',
        'default_model': 'gemini-2.0-flash',
        'models': ['gemini-2.0-flash', 'gemini-2.0-flash-lite', 'gemini-2.5-flash-preview-05-20', 'gemini-1.5-pro'],
        'hint': 'aistudio.google.com/app/apikey',
        'supports_tools': False,
    },
    'deepseek': {
        'name': 'DeepSeek', 'icon': '🟡',
        'env_var': 'DEEPSEEK_API_KEY',
        'url': 'https://api.deepseek.com/v1/chat/completions',
        'balance_url': 'https://api.deepseek.com/user/balance',
        'api_type': 'openai',
        'default_model': 'deepseek-chat',
        'models': ['deepseek-chat', 'deepseek-reasoner'],
        'hint': 'platform.deepseek.com/api_keys',
        'supports_tools': True,
    },
    'mistral': {
        'name': 'Mistral AI', 'icon': '🟣',
        'env_var': 'MISTRAL_KEY',
        'url': 'https://api.mistral.ai/v1/chat/completions',
        'api_type': 'openai',
        'default_model': 'mistral-small-latest',
        'models': ['mistral-small-latest', 'mistral-large-latest', 'codestral-latest'],
        'hint': 'console.mistral.ai/api-keys',
        'supports_tools': True,
    },
    'groq': {
        'name': 'Groq', 'icon': '🟠',
        'env_var': 'GROQ_API_KEY',
        'url': 'https://api.groq.com/openai/v1/chat/completions',
        'api_type': 'openai',
        'default_model': 'llama-3.3-70b-versatile',
        'models': ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant', 'mixtral-8x7b-32768', 'gemma2-9b-it'],
        'hint': 'console.groq.com/keys',
        'supports_tools': True,
    },
    'xai': {
        'name': 'xAI Grok', 'icon': '⬛',
        'env_var': 'XAI_KEY',
        'url': 'https://api.x.ai/v1/chat/completions',
        'api_type': 'openai',
        'default_model': 'grok-2-1212',
        'models': ['grok-2-1212', 'grok-2-vision-1212', 'grok-beta'],
        'hint': 'console.x.ai — X Premium required',
        'supports_tools': True,
    },
    'together': {
        'name': 'Together AI', 'icon': '🔷',
        'env_var': 'TOGETHER_KEY',
        'url': 'https://api.together.xyz/v1/chat/completions',
        'api_type': 'openai',
        'default_model': 'meta-llama/Llama-3.3-70B-Instruct-Turbo',
        'models': [
            'meta-llama/Llama-3.3-70B-Instruct-Turbo',
            'deepseek-ai/DeepSeek-R1',
            'Qwen/Qwen2.5-72B-Instruct-Turbo',
        ],
        'hint': 'api.together.ai/settings/api-keys',
        'supports_tools': False,
    },
    'openrouter': {
        'name': 'OpenRouter', 'icon': '🔵',
        'env_var': 'OPENROUTER_KEY',
        'url': 'https://openrouter.ai/api/v1/chat/completions',
        'balance_url': 'https://openrouter.ai/api/v1/auth/key',
        'api_type': 'openai',
        'default_model': 'google/gemma-4-31b-it:free',
        'models': [
            'google/gemma-4-31b-it:free',
            'openai/gpt-oss-20b:free',
            'openai/gpt-oss-120b:free',
            'deepseek/deepseek-r1:free',
            'meta-llama/llama-3.3-70b-instruct:free',
            'google/gemini-2.5-flash-preview:free',
        ],
        'extra_headers': {
            'HTTP-Referer': 'https://rowadtahseeli.sa',
            'X-Title': 'Rowad Code Assistant',
        },
        'hint': 'openrouter.ai/keys — نماذج مجانية كثيرة',
        'supports_tools': False,
    },
}

MODELS = {
    'auto':           {'label': '🔄 تلقائي — كل المزودين بالترتيب',               'needs_key': False},
    'g4f-free':       {'label': '🟢 مجاني — Qwen/Llama (بلا مفتاح)',              'needs_key': False},
    # ─── OpenAI ───────────────────────────────────────────────────────────────
    'openai-mini':    {'label': '⚫ GPT-4o Mini (OpenAI)',                          'needs_key': True, 'provider': 'openai',    'model': 'gpt-4o-mini'},
    'openai-4o':      {'label': '⚫ GPT-4o (OpenAI)',                               'needs_key': True, 'provider': 'openai',    'model': 'gpt-4o'},
    # ─── Anthropic ────────────────────────────────────────────────────────────
    'claude-haiku':   {'label': '🟤 Claude 3.5 Haiku (Anthropic)',                 'needs_key': True, 'provider': 'anthropic', 'model': 'claude-3-5-haiku-20241022'},
    'claude-sonnet':  {'label': '🟤 Claude 3.5 Sonnet (Anthropic)',                'needs_key': True, 'provider': 'anthropic', 'model': 'claude-3-5-sonnet-20241022'},
    # ─── DeepSeek ─────────────────────────────────────────────────────────────
    'ds-chat':        {'label': '🟡 DeepSeek Chat V3 (مباشر)',                     'needs_key': True, 'provider': 'deepseek',  'model': 'deepseek-chat'},
    'ds-r1':          {'label': '🟡 DeepSeek Reasoner R1 (مباشر)',                 'needs_key': True, 'provider': 'deepseek',  'model': 'deepseek-reasoner'},
    # ─── Gemini ───────────────────────────────────────────────────────────────
    'gem-flash':      {'label': '🔴 Gemini 2.0 Flash (Google)',                    'needs_key': True, 'provider': 'gemini',    'model': 'gemini-2.0-flash'},
    'gem-25flash':    {'label': '🔴 Gemini 2.5 Flash Preview (Google)',            'needs_key': True, 'provider': 'gemini',    'model': 'gemini-2.5-flash-preview-05-20'},
    'gem-pro':        {'label': '🔴 Gemini 1.5 Pro (Google)',                      'needs_key': True, 'provider': 'gemini',    'model': 'gemini-1.5-pro'},
    # ─── Mistral ──────────────────────────────────────────────────────────────
    'mistral-sm':     {'label': '🟣 Mistral Small (Mistral AI)',                   'needs_key': True, 'provider': 'mistral',   'model': 'mistral-small-latest'},
    'mistral-cd':     {'label': '🟣 Codestral (Mistral — للكود)',                  'needs_key': True, 'provider': 'mistral',   'model': 'codestral-latest'},
    # ─── Groq ─────────────────────────────────────────────────────────────────
    'groq-llama':     {'label': '🟠 Llama 3.3 70B (Groq — سريع)',                 'needs_key': True, 'provider': 'groq',      'model': 'llama-3.3-70b-versatile'},
    'groq-fast':      {'label': '🟠 Llama 3.1 8B (Groq — سريع جداً)',             'needs_key': True, 'provider': 'groq',      'model': 'llama-3.1-8b-instant'},
    # ─── xAI ──────────────────────────────────────────────────────────────────
    'grok-2':         {'label': '⬛ Grok-2 (xAI)',                                'needs_key': True, 'provider': 'xai',       'model': 'grok-2-1212'},
    # ─── Together AI ──────────────────────────────────────────────────────────
    'together-llama': {'label': '🔷 Llama 3.3 70B (Together AI)',                  'needs_key': True, 'provider': 'together',  'model': 'meta-llama/Llama-3.3-70B-Instruct-Turbo'},
    'together-ds':    {'label': '🔷 DeepSeek R1 (Together AI)',                    'needs_key': True, 'provider': 'together',  'model': 'deepseek-ai/DeepSeek-R1'},
    # ─── OpenRouter ───────────────────────────────────────────────────────────
    'or-gemma':       {'label': '🔵 Gemma 4 31B (OpenRouter مجاني)',               'needs_key': True, 'provider': 'openrouter','model': 'google/gemma-4-31b-it:free'},
    'or-gpt120':      {'label': '🔵 GPT-OSS 120B (OpenRouter مجاني)',              'needs_key': True, 'provider': 'openrouter','model': 'openai/gpt-oss-120b:free'},
    'or-ds-r1':       {'label': '🔵 DeepSeek R1 (OpenRouter مجاني)',               'needs_key': True, 'provider': 'openrouter','model': 'deepseek/deepseek-r1:free'},
    'or-llama70':     {'label': '🔵 Llama 3.3 70B (OpenRouter مجاني)',             'needs_key': True, 'provider': 'openrouter','model': 'meta-llama/llama-3.3-70b-instruct:free'},
    'or-gemini25':    {'label': '🔵 Gemini 2.5 Flash (OpenRouter مجاني)',          'needs_key': True, 'provider': 'openrouter','model': 'google/gemini-2.5-flash-preview:free'},
}

# للتوافق مع الكود القديم
OR_MODELS = PROVIDERS['openrouter']['models'][:3]


# ═══════════════════════════════════════════════════════════════════════════════
# الحماية
# ═══════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════
# تخزين الأسرار المحلي (لا يُرفع إلى GitHub أبداً)
# ═══════════════════════════════════════════════════════════════════════════════

_LOCAL_SECRETS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'data_store', '.ca_secrets.json')
)

def _load_local_secrets() -> dict:
    try:
        if os.path.exists(_LOCAL_SECRETS_PATH):
            with open(_LOCAL_SECRETS_PATH, 'r', encoding='utf-8') as f:
                return _json.load(f)
    except Exception:
        pass
    return {}

def _save_local_secret(key: str, value: str):
    """يحفظ السر محلياً فقط — لا يُرفع إلى GitHub أبداً."""
    os.makedirs(os.path.dirname(_LOCAL_SECRETS_PATH), exist_ok=True)
    data = _load_local_secrets()
    data[key] = value
    with open(_LOCAL_SECRETS_PATH, 'w', encoding='utf-8') as f:
        _json.dump(data, f)


# ═══════════════════════════════════════════════════════════════════════════════
# قراءة المفاتيح — الأولوية: Replit Secrets (env) ثم الملف المحلي
# ═══════════════════════════════════════════════════════════════════════════════

def _provider_key(pid: str) -> str:
    """
    يقرأ مفتاح المزود من env vars (Replit Secrets) أولاً.
    المفتاح يُوضَع في Authorization Header فقط — لا يُرسَل أبداً في نص الرسائل.
    """
    prov = PROVIDERS.get(pid, {})
    env_key = os.getenv(prov.get('env_var', ''), '').strip()
    if env_key:
        return env_key
    return _load_local_secrets().get(pid + '_key', '')

def _get_key() -> str:
    """للتوافق مع الكود القديم — يُعيد مفتاح OpenRouter."""
    return _provider_key('openrouter')

def _gh_token() -> str:
    env = os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN', '').strip()
    if env:
        return env
    return _load_local_secrets().get('github_token', '')

def _gh_headers():
    t = _gh_token()
    h = {'User-Agent': 'RowadTahseeli-CodeAssistant',
         'Accept': 'application/vnd.github.v3+json'}
    if t:
        h['Authorization'] = f'token {t}'
    return h


# ═══════════════════════════════════════════════════════════════════════════════
# دوال البث (Streaming) لكل المزودين
# ═══════════════════════════════════════════════════════════════════════════════

def _openai_compat_stream(messages, model_name, url, key, extra_headers=None, max_tokens=4096):
    """مولِّد عام لكل API متوافقة مع OpenAI — المفتاح في Header فقط."""
    headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    if extra_headers:
        headers.update(extra_headers)
    try:
        r = rq.post(
            url,
            json={'model': model_name, 'messages': messages[-20:],
                  'max_tokens': max_tokens, 'stream': True},
            headers=headers, stream=True, timeout=120,
        )
        if r.status_code != 200:
            logger.warning(f'openai-stream {url}/{model_name}: HTTP {r.status_code} {r.text[:100]}')
            return
        for line in r.iter_lines():
            if not line: continue
            if isinstance(line, bytes): line = line.decode('utf-8', errors='replace')
            if not line.startswith('data: '): continue
            raw = line[6:].strip()
            if raw == '[DONE]': break
            try:
                delta = _json.loads(raw)['choices'][0]['delta'].get('content', '')
                if delta: yield delta
            except Exception: pass
    except Exception as e:
        logger.warning(f'openai-stream {url}: {e}')


def _anthropic_stream(messages, model_name, key, max_tokens=4096):
    """مولِّد لـ Anthropic API — المفتاح في x-api-key Header فقط."""
    system_content = ''
    chat_msgs = []
    for m in messages:
        if m['role'] == 'system':
            system_content = m['content']
        else:
            chat_msgs.append(m)
    body = {
        'model': model_name,
        'max_tokens': max_tokens,
        'messages': chat_msgs[-20:],
        'stream': True,
    }
    if system_content:
        body['system'] = system_content
    try:
        r = rq.post(
            'https://api.anthropic.com/v1/messages',
            json=body,
            headers={
                'x-api-key': key,
                'anthropic-version': '2023-06-01',
                'Content-Type': 'application/json',
            },
            stream=True, timeout=120,
        )
        if r.status_code != 200:
            logger.warning(f'anthropic-stream {model_name}: HTTP {r.status_code} {r.text[:100]}')
            return
        for line in r.iter_lines():
            if not line: continue
            if isinstance(line, bytes): line = line.decode('utf-8', errors='replace')
            if not line.startswith('data: '): continue
            raw = line[6:].strip()
            if not raw: continue
            try:
                obj = _json.loads(raw)
                if obj.get('type') == 'content_block_delta':
                    text = obj.get('delta', {}).get('text', '')
                    if text: yield text
            except Exception: pass
    except Exception as e:
        logger.warning(f'anthropic-stream: {e}')


def _gemini_stream(messages, model_name, key, max_tokens=4096):
    """مولِّد لـ Gemini API — المفتاح في URL parameter فقط، لا في الرسائل."""
    url = (f'https://generativelanguage.googleapis.com/v1beta/models/'
           f'{model_name}:streamGenerateContent?alt=sse&key={key}')
    system_text = ''
    contents = []
    for m in messages:
        if m['role'] == 'system':
            system_text = m['content']
        else:
            role = 'user' if m['role'] == 'user' else 'model'
            contents.append({'role': role, 'parts': [{'text': m['content']}]})
    if not contents:
        return
    body = {'contents': contents[-20:], 'generationConfig': {'maxOutputTokens': max_tokens}}
    if system_text:
        body['systemInstruction'] = {'parts': [{'text': system_text}]}
    try:
        r = rq.post(url, json=body, stream=True, timeout=120,
                    headers={'Content-Type': 'application/json'})
        if r.status_code != 200:
            logger.warning(f'gemini-stream {model_name}: HTTP {r.status_code} {r.text[:100]}')
            return
        for line in r.iter_lines():
            if not line: continue
            if isinstance(line, bytes): line = line.decode('utf-8', errors='replace')
            if not line.startswith('data: '): continue
            raw = line[6:].strip()
            if not raw or raw == '[DONE]': continue
            try:
                obj = _json.loads(raw)
                text = obj['candidates'][0]['content']['parts'][0].get('text', '')
                if text: yield text
            except Exception: pass
    except Exception as e:
        logger.warning(f'gemini-stream: {e}')


def _g4f_sync(messages):
    """استدعاء g4f بشكل متزامن في thread منفصل."""
    try:
        from g4f.client import Client as G4FClient
        import g4f.Provider as P
        pairs = [
            (P.Qwen_Qwen_3,     'qwen3-235b-a22b'),
            (P.Qwen_Qwen_2_72B, 'Qwen2.5-72B-Instruct'),
            (P.HuggingSpace,    'Qwen/Qwen2.5-72B-Instruct'),
        ]
        for prov, mod in pairs:
            try:
                c = G4FClient(provider=prov)
                resp = c.chat.completions.create(model=mod, messages=messages[-8:], timeout=60)
                text = (resp.choices[0].message.content or '').strip()
                if len(text) > 5:
                    return text
            except Exception:
                continue
    except Exception as e:
        logger.warning(f'g4f: {e}')
    return None


def _stream_chunks_from_g4f(ai_messages):
    """يشغّل g4f في thread مع heartbeat ثم يُعيد النص على شُرَح."""
    result_box = [None]
    done_ev    = threading.Event()
    def _run(): result_box[0] = _g4f_sync(ai_messages); done_ev.set()
    threading.Thread(target=_run, daemon=True).start()
    while not done_ev.wait(timeout=2):
        yield ': ping\n\n'
    text = result_box[0] or 'لم يتمكن الذكاء الاصطناعي من الإجابة حالياً.'
    step = 40
    for i in range(0, len(text), step):
        yield f"data: {_json.dumps({'chunk': text[i:i+step]})}\n\n"
    yield "data: [DONE]\n\n"


# ═══════════════════════════════════════════════════════════════════════════════
# استدعاء غير متدفق (للتحليل)
# ═══════════════════════════════════════════════════════════════════════════════

def _call_ai_provider(messages, pid, model_name=None):
    """استدعاء مزوّد واحد بشكل غير متدفق."""
    prov = PROVIDERS.get(pid, {})
    key  = _provider_key(pid)
    if not key: return None
    mn = model_name or prov.get('default_model', '')
    try:
        if prov['api_type'] == 'openai':
            hdrs = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
            if prov.get('extra_headers'): hdrs.update(prov['extra_headers'])
            r = rq.post(prov['url'],
                       json={'model': mn, 'messages': messages[-16:], 'max_tokens': 4000},
                       headers=hdrs, timeout=90)
            if r.status_code == 200:
                c = r.json()['choices'][0]['message']['content']
                return c.strip() if c else None
        elif prov['api_type'] == 'anthropic':
            sys_c = ''; chat = []
            for m in messages:
                if m['role'] == 'system': sys_c = m['content']
                else: chat.append(m)
            body = {'model': mn, 'max_tokens': 4000, 'messages': chat[-16:]}
            if sys_c: body['system'] = sys_c
            r = rq.post('https://api.anthropic.com/v1/messages', json=body,
                       headers={'x-api-key': key, 'anthropic-version': '2023-06-01',
                                'Content-Type': 'application/json'}, timeout=90)
            if r.status_code == 200:
                return r.json()['content'][0]['text'].strip()
        elif prov['api_type'] == 'gemini':
            sys_t = ''; cnts = []
            for m in messages:
                if m['role'] == 'system': sys_t = m['content']
                else:
                    role = 'user' if m['role'] == 'user' else 'model'
                    cnts.append({'role': role, 'parts': [{'text': m['content']}]})
            url  = (f'https://generativelanguage.googleapis.com/v1beta/models/'
                    f'{mn}:generateContent?key={key}')
            body = {'contents': cnts[-16:], 'generationConfig': {'maxOutputTokens': 4000}}
            if sys_t: body['systemInstruction'] = {'parts': [{'text': sys_t}]}
            r = rq.post(url, json=body, headers={'Content-Type': 'application/json'}, timeout=90)
            if r.status_code == 200:
                return r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception as e:
        logger.warning(f'call_ai_provider {pid}/{mn}: {e}')
    return None


def _call_ai(messages: list, model_id: str = 'auto') -> str:
    """استدعاء غير متدفق — يُستخدم في /analyze."""
    meta = MODELS.get(model_id, {})
    pid  = meta.get('provider', '')
    mn   = meta.get('model', '')

    if model_id == 'auto':
        priority = ['deepseek', 'openrouter', 'gemini', 'groq', 'openai', 'anthropic', 'mistral', 'xai', 'together']
        for p in priority:
            if not _provider_key(p): continue
            result = _call_ai_provider(messages, p, PROVIDERS[p]['default_model'])
            if result: return result
        r = _g4f_sync(messages)
        return r or 'لم يتمكن الذكاء الاصطناعي من الإجابة حالياً.'

    if pid and mn:
        result = _call_ai_provider(messages, pid, mn)
        return result or f'فشل النموذج "{model_id}". جرّب نموذجاً آخر.'

    r = _g4f_sync(messages)
    return r or 'لم يتمكن g4f من الإجابة حالياً.'


# ═══════════════════════════════════════════════════════════════════════════════
# System Prompt
# ═══════════════════════════════════════════════════════════════════════════════

def _build_system(repo, project_map, open_files, agent_mode=False):
    parts = [f'أنت مساعد برمجي متقدم لمستودع GitHub: {repo}', '']

    if agent_mode:
        parts += [
            '🤖 **وضع الوكيل المستقل — صلاحياتك الكاملة:**',
            '  • استكشف المستودع بنفسك: اقرأ الملفات، ابحث في الكود',
            '  • عدّل الملفات وارفعها مباشرةً إلى GitHub دون انتظار المستخدم',
            '  • أنشئ ملفات جديدة عند الحاجة',
            '  • افحص نتائج التعديلات واستمر حتى اكتمال المهمة كاملاً',
            '',
            '📋 **طريقة العمل:**',
            '  1. ابدأ بقراءة الملفات ذات الصلة بالمهمة (read_file / list_files)',
            '  2. خطّط التعديلات المطلوبة بدقة',
            '  3. نفّذها واحدة تلو الأخرى (write_file / create_file)',
            '  4. تحقق من النتائج واستمر إن لزم',
            '',
            '⚠️ **قواعد مهمة:**',
            '  • اكتب محتوى الملف كاملاً في write_file — لا اختصار أو "..."',
            '  • اشرح كل خطوة باللغة العربية',
            '  • عند HTTP 409 أعِد قراءة الملف واحصل على sha الحديث',
        ]
    else:
        parts += [
            'قدراتك:',
            '  • قراءة وتعديل ملفات المستودع',
            '  • تحليل الكود وشرحه بالعربية',
            '  • اقتراح تعديلات وإصلاح أخطاء',
            '  • إنشاء ملفات جديدة وكامل الكود مهما طال',
            '',
            'قواعد:',
            '  • اشرح باللغة العربية، اكتب الكود بالإنجليزية',
            '  • اذكر اسم الملف قبل كتلة الكود عند التعديل',
            '  • [OPEN_FILE: path] لطلب فتح ملف',
            '  • [APPLY_TO: filename] للتطبيق على ملف مفتوح',
            '  • اكتب الكود كاملاً دون اختصار',
        ]

    parts.append('')
    if project_map:
        parts += ['── خريطة المشروع ──', project_map[:6000], '']
    if open_files:
        parts.append('── الملفات المفتوحة ──')
        for f in open_files[:6]:
            parts += [f'📄 {f["path"]}:', '```',
                      str(f.get('content', ''))[:5000], '```', '']
    return '\n'.join(parts)


# ═══════════════════════════════════════════════════════════════════════════════
# GitHub helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _parse_repo(repo_input: str) -> str:
    if not repo_input:
        return 'abdalkhalqali/rowadaltahseeli1'
    s = repo_input.strip().rstrip('/').replace('.git', '')
    if 'github.com/' in s:
        parts = [p for p in s.split('github.com/')[-1].split('/') if p]
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
    data = resp.json()
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
    data = resp.json()
    if not isinstance(data, list):
        return None, 'المسار ليس مجلداً'
    items = [{'name': i['name'], 'path': i['path'],
              'type': i['type'], 'size': i.get('size', 0)} for i in data]
    items.sort(key=lambda x: (0 if x['type'] == 'dir' else 1, x['name'].lower()))
    return items, None

def _gh_default_branch(repo):
    resp = rq.get(f'https://api.github.com/repos/{repo}', headers=_gh_headers(), timeout=10)
    if resp.status_code == 200:
        return resp.json().get('default_branch', 'main')
    return 'main'

def _gh_tree(repo):
    branch = _gh_default_branch(repo)
    url    = f'https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1'
    resp   = rq.get(url, headers=_gh_headers(), timeout=20)
    if resp.status_code != 200:
        logger.warning(f'_gh_tree {repo}: {resp.status_code} {resp.text[:120]}')
        return None
    tree = resp.json().get('tree', [])
    return [t['path'] for t in tree if t['type'] == 'blob']

def _gh_search(query: str, repo: str) -> dict:
    """بحث نصي داخل المستودع عبر GitHub Search API."""
    try:
        hdrs = _gh_headers()
        hdrs['Accept'] = 'application/vnd.github.v3+json'
        r = rq.get('https://api.github.com/search/code',
                   headers=hdrs,
                   params={'q': f'{query} repo:{repo}', 'per_page': 10},
                   timeout=15)
        if r.status_code == 200:
            items = r.json().get('items', [])
            return {'results': [{'path': i['path']} for i in items],
                    'total': r.json().get('total_count', 0)}
        return {'results': [], 'error': f'HTTP {r.status_code}'}
    except Exception as e:
        return {'results': [], 'error': str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# الوكيل المستقل — الأدوات
# ═══════════════════════════════════════════════════════════════════════════════

AGENT_TOOLS = [
    {"type": "function", "function": {
        "name": "read_file",
        "description": "اقرأ محتوى ملف من GitHub",
        "parameters": {"type": "object",
                       "properties": {"path": {"type": "string", "description": "مسار الملف"}},
                       "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "list_files",
        "description": "اعرض محتويات مجلد في المستودع",
        "parameters": {"type": "object",
                       "properties": {"path": {"type": "string", "description": "مسار المجلد"}},
                       "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "عدّل ملفاً موجوداً وارفعه مباشرةً إلى GitHub",
        "parameters": {"type": "object",
                       "properties": {
                           "path":    {"type": "string", "description": "مسار الملف"},
                           "content": {"type": "string", "description": "المحتوى الجديد الكامل"},
                           "message": {"type": "string", "description": "رسالة commit"}},
                       "required": ["path", "content"]}}},
    {"type": "function", "function": {
        "name": "create_file",
        "description": "أنشئ ملفاً جديداً في GitHub",
        "parameters": {"type": "object",
                       "properties": {
                           "path":    {"type": "string", "description": "مسار الملف الجديد"},
                           "content": {"type": "string", "description": "محتوى الملف"},
                           "message": {"type": "string", "description": "رسالة commit"}},
                       "required": ["path", "content"]}}},
    {"type": "function", "function": {
        "name": "analyze_tree",
        "description": "احصل على قائمة كل ملفات المستودع",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "search_code",
        "description": "ابحث عن نص أو كود داخل ملفات المستودع",
        "parameters": {"type": "object",
                       "properties": {"query": {"type": "string", "description": "النص المطلوب"}},
                       "required": ["query"]}}},
]

def _execute_tool(tool_name, tool_args, repo):
    """نفّذ أداة الوكيل وأعِد النتيجة."""
    try:
        if tool_name == 'read_file':
            result, err = _gh_read(tool_args.get('path', ''), repo)
            if err: return {'error': err}
            return {'content': result['content'][:8000], 'sha': result['sha']}

        elif tool_name == 'list_files':
            items, err = _gh_list(tool_args.get('path', ''), repo)
            if err: return {'error': err}
            return {'items': items}

        elif tool_name == 'write_file':
            path    = tool_args.get('path', '')
            content = tool_args.get('content', '')
            message = tool_args.get('message', f'agent: update {path}')
            existing, _ = _gh_read(path, repo)
            if not existing:
                return {'error': f'الملف {path} غير موجود — استخدم create_file'}
            ok, err, new_sha = _gh_write(path, content, existing['sha'], message, repo)
            if not ok and '409' in (err or ''):
                fresh, _ = _gh_read(path, repo)
                if fresh:
                    ok, err, new_sha = _gh_write(path, content, fresh['sha'], message, repo)
            return {'success': ok, 'msg': f'✅ حُفظ {path}' if ok else err}

        elif tool_name == 'create_file':
            path    = tool_args.get('path', '')
            content = tool_args.get('content', '')
            message = tool_args.get('message', f'agent: create {path}')
            url  = f'https://api.github.com/repos/{repo}/contents/{path}'
            body = {'message': message,
                    'content': base64.b64encode(content.encode('utf-8')).decode('ascii')}
            resp = rq.put(url, json=body, headers=_gh_headers(), timeout=30)
            if resp.status_code in (200, 201):
                return {'success': True, 'msg': f'✅ تم إنشاء {path}',
                        'sha': resp.json().get('content', {}).get('sha', '')}
            return {'error': f'HTTP {resp.status_code}: {resp.text[:150]}'}

        elif tool_name == 'analyze_tree':
            files = _gh_tree(repo)
            return {'files': files[:300] if files else [], 'count': len(files) if files else 0}

        elif tool_name == 'search_code':
            return _gh_search(tool_args.get('query', ''), repo)

        return {'error': f'أداة غير معروفة: {tool_name}'}
    except Exception as e:
        return {'error': str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# فحص المفاتيح والرصيد
# ═══════════════════════════════════════════════════════════════════════════════

def _test_provider(pid):
    """يختبر مفتاح مزوّد بإرسال رسالة قصيرة — المفتاح في Header فقط."""
    prov = PROVIDERS.get(pid)
    if not prov: return False, 'مزود غير معروف'
    key = _provider_key(pid)
    if not key: return False, f'المفتاح {prov["env_var"]} غير موجود في الأسرار'
    test_msgs = [{'role': 'user', 'content': 'قل كلمة واحدة: مرحبا'}]
    try:
        if prov['api_type'] == 'openai':
            hdrs = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
            if prov.get('extra_headers'): hdrs.update(prov['extra_headers'])
            r = rq.post(prov['url'],
                       json={'model': prov['default_model'], 'messages': test_msgs, 'max_tokens': 20},
                       headers=hdrs, timeout=25)
            if r.status_code == 200:
                reply = r.json()['choices'][0]['message'].get('content', '')
                return True, f'✅ يعمل — "{reply[:40]}"'
            return False, f'HTTP {r.status_code}: {r.text[:120]}'
        elif prov['api_type'] == 'anthropic':
            body = {'model': prov['default_model'], 'max_tokens': 20, 'messages': test_msgs}
            r = rq.post('https://api.anthropic.com/v1/messages', json=body,
                       headers={'x-api-key': key, 'anthropic-version': '2023-06-01',
                                'Content-Type': 'application/json'}, timeout=25)
            if r.status_code == 200:
                text = r.json()['content'][0]['text']
                return True, f'✅ يعمل — "{text[:40]}"'
            return False, f'HTTP {r.status_code}: {r.text[:120]}'
        elif prov['api_type'] == 'gemini':
            url  = (f'https://generativelanguage.googleapis.com/v1beta/models/'
                    f'{prov["default_model"]}:generateContent?key={key}')
            body = {'contents': [{'role': 'user', 'parts': [{'text': 'say hello'}]}],
                    'generationConfig': {'maxOutputTokens': 20}}
            r = rq.post(url, json=body, timeout=25)
            if r.status_code == 200:
                text = r.json()['candidates'][0]['content']['parts'][0].get('text', '')
                return True, f'✅ يعمل — "{text[:40]}"'
            return False, f'HTTP {r.status_code}: {r.text[:120]}'
    except Exception as e:
        return False, str(e)[:120]
    return False, 'فشل'


def _get_balance(pid):
    """يجلب رصيد المفتاح من API المزوّد."""
    prov = PROVIDERS.get(pid)
    if not prov or not prov.get('balance_url'):
        return None, 'هذا المزود لا يوفر API للرصيد'
    key = _provider_key(pid)
    if not key: return None, 'المفتاح غير موجود'
    try:
        if pid == 'openrouter':
            r = rq.get(prov['balance_url'],
                      headers={'Authorization': f'Bearer {key}'}, timeout=10)
            if r.status_code == 200:
                d     = r.json().get('data', {})
                usage = float(d.get('usage', 0))
                limit = d.get('limit')
                return {
                    'label':     d.get('label', 'غير مُسمَّى'),
                    'usage':     f'${usage:.4f}',
                    'limit':     f'${float(limit):.2f}' if limit else 'غير محدود',
                    'free_tier': not bool(limit),
                }, None
        elif pid == 'deepseek':
            r = rq.get(prov['balance_url'],
                      headers={'Authorization': f'Bearer {key}'}, timeout=10)
            if r.status_code == 200:
                b = (r.json().get('balance_infos') or [{}])[0]
                return {
                    'total':   f'${float(b.get("total_balance", 0)):.4f}',
                    'granted': f'${float(b.get("granted_balance", 0)):.4f}',
                    'topped':  f'${float(b.get("topped_up_balance", 0)):.4f}',
                }, None
        return None, 'جاري التطوير لهذا المزوّد'
    except Exception as e:
        return None, str(e)[:100]


# ═══════════════════════════════════════════════════════════════════════════════
# Repos favorites
# ═══════════════════════════════════════════════════════════════════════════════

def _load_repos():
    try:
        from services.data_store import _read_local
        return _read_local('code_assistant_repos.json') or []
    except Exception:
        return []

def _save_repos(repos):
    try:
        from services.data_store import _write_local
        _write_local('code_assistant_repos.json', repos)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@code_assistant_bp.route('/admin/code-assistant')
@login_required
@_super_admin_required
def index():
    return render_template('admin_code_assistant.html', models=MODELS, providers=PROVIDERS)


# ─── Chat (streaming SSE — دردشة عادية) ───────────────────────────────────────

@code_assistant_bp.route('/admin/code-assistant/chat/stream', methods=['POST'])
@login_required
@_super_admin_required
def chat_stream():
    data        = request.get_json(silent=True) or {}
    messages    = data.get('messages', [])
    model_id    = data.get('model', 'auto')
    repo        = _parse_repo(data.get('repo', ''))
    open_files  = data.get('open_files', [])
    project_map = data.get('project_map', '')

    if not messages:
        def _err():
            yield f"data: {_json.dumps({'error': 'لا توجد رسائل'})}\n\n"
            yield "data: [DONE]\n\n"
        return Response(stream_with_context(_err()), content_type='text/event-stream')

    system      = _build_system(repo, project_map, open_files, agent_mode=False)
    ai_messages = [{'role': 'system', 'content': system}] + messages[-20:]
    meta        = MODELS.get(model_id, {})
    pid         = meta.get('provider', '')
    mn          = meta.get('model', '')

    def generate():
        # ── مزوّد محدد ────────────────────────────────────────────────────────
        if pid and mn:
            key  = _provider_key(pid)
            prov = PROVIDERS.get(pid, {})
            if key:
                accumulated = []
                if prov['api_type'] == 'openai':
                    for chunk in _openai_compat_stream(ai_messages, mn, prov['url'], key, prov.get('extra_headers')):
                        accumulated.append(chunk)
                        yield f"data: {_json.dumps({'chunk': chunk})}\n\n"
                elif prov['api_type'] == 'anthropic':
                    for chunk in _anthropic_stream(ai_messages, mn, key):
                        accumulated.append(chunk)
                        yield f"data: {_json.dumps({'chunk': chunk})}\n\n"
                elif prov['api_type'] == 'gemini':
                    for chunk in _gemini_stream(ai_messages, mn, key):
                        accumulated.append(chunk)
                        yield f"data: {_json.dumps({'chunk': chunk})}\n\n"
                if accumulated:
                    yield "data: [DONE]\n\n"; return
            yield f"data: {_json.dumps({'error': f'مفتاح {pid} غير موجود — أضفه في الإعدادات ⚙️'})}\n\n"
            yield "data: [DONE]\n\n"; return

        # ── وضع تلقائي: جرّب كل المزودين بالترتيب ────────────────────────────
        priority = ['deepseek', 'openrouter', 'gemini', 'groq', 'openai', 'anthropic', 'mistral', 'xai', 'together']
        for p in priority:
            key = _provider_key(p)
            if not key: continue
            prov = PROVIDERS[p]
            accumulated = []
            try:
                if prov['api_type'] == 'openai':
                    gen = _openai_compat_stream(ai_messages, prov['default_model'],
                                                 prov['url'], key, prov.get('extra_headers'))
                elif prov['api_type'] == 'anthropic':
                    gen = _anthropic_stream(ai_messages, prov['default_model'], key)
                elif prov['api_type'] == 'gemini':
                    gen = _gemini_stream(ai_messages, prov['default_model'], key)
                else:
                    continue
                for chunk in gen:
                    accumulated.append(chunk)
                    yield f"data: {_json.dumps({'chunk': chunk})}\n\n"
            except Exception as e:
                logger.warning(f'auto-stream {p}: {e}'); continue
            if accumulated:
                yield "data: [DONE]\n\n"; return

        # g4f كآخر خيار
        yield from _stream_chunks_from_g4f(ai_messages)

    return Response(
        stream_with_context(generate()),
        content_type='text/event-stream',
        headers={'Cache-Control': 'no-cache, no-transform',
                 'X-Accel-Buffering': 'no', 'Connection': 'keep-alive'},
    )


# ─── وكيل مستقل (agent streaming SSE) ────────────────────────────────────────

@code_assistant_bp.route('/admin/code-assistant/agent/stream', methods=['POST'])
@login_required
@_super_admin_required
def agent_stream():
    data        = request.get_json(silent=True) or {}
    messages    = data.get('messages', [])
    model_id    = data.get('model', 'auto')
    repo        = _parse_repo(data.get('repo', ''))
    project_map = data.get('project_map', '')
    open_files  = data.get('open_files', [])

    if not messages:
        def _err():
            yield f"data: {_json.dumps({'error': 'لا توجد رسائل'})}\n\n"
            yield "data: [DONE]\n\n"
        return Response(stream_with_context(_err()), content_type='text/event-stream')

    system = _build_system(repo, project_map, open_files, agent_mode=True)

    def generate():
        meta = MODELS.get(model_id, {})
        pid  = meta.get('provider', '')
        mn   = meta.get('model', '')

        # اختر مزوّداً يدعم tool-calling
        tool_providers_priority = ['openai', 'anthropic', 'deepseek', 'groq', 'mistral', 'xai']

        if not pid:
            # auto — اختر أول مزوّد متاح يدعم الأدوات
            for p in tool_providers_priority:
                if _provider_key(p):
                    pid = p; mn = PROVIDERS[p]['default_model']
                    break

        prov           = PROVIDERS.get(pid, {})
        supports_tools = prov.get('supports_tools', False) and bool(_provider_key(pid))

        ai_messages = [{'role': 'system', 'content': system}] + messages[-20:]
        MAX_ITERS   = 15

        if supports_tools:
            key = _provider_key(pid)

            for iteration in range(MAX_ITERS):
                try:
                    # ── Anthropic tool calling ────────────────────────────────
                    if prov['api_type'] == 'anthropic':
                        sys_c = ''; chat = []
                        for m in ai_messages:
                            if m['role'] == 'system': sys_c = m['content']
                            else: chat.append(m)
                        ant_tools = [{'name': t['function']['name'],
                                      'description': t['function']['description'],
                                      'input_schema': t['function']['parameters']}
                                     for t in AGENT_TOOLS]
                        r = rq.post('https://api.anthropic.com/v1/messages',
                                   json={'model': mn, 'max_tokens': 4096,
                                        'messages': chat[-20:], 'system': sys_c,
                                        'tools': ant_tools},
                                   headers={'x-api-key': key, 'anthropic-version': '2023-06-01',
                                            'Content-Type': 'application/json'}, timeout=120)
                        if r.status_code != 200:
                            yield f"data: {_json.dumps({'error': f'Anthropic HTTP {r.status_code}'})}\n\n"
                            break
                        resp        = r.json()
                        stop_reason = resp.get('stop_reason', '')
                        text_parts  = []; tool_calls = []
                        for block in resp.get('content', []):
                            if block.get('type') == 'text':   text_parts.append(block.get('text', ''))
                            elif block.get('type') == 'tool_use': tool_calls.append(block)
                        if text_parts:
                            text = ''.join(text_parts)
                            for i in range(0, len(text), 40):
                                yield f"data: {_json.dumps({'chunk': text[i:i+40]})}\n\n"
                        if stop_reason == 'end_turn' or not tool_calls:
                            yield "data: [DONE]\n\n"; return
                        ai_messages.append({'role': 'assistant', 'content': resp['content']})
                        tool_results = []
                        for tc in tool_calls:
                            yield f"data: {_json.dumps({'tool': tc['name'], 'args': tc.get('input', {})})}\n\n"
                            result = _execute_tool(tc['name'], tc.get('input', {}), repo)
                            yield f"data: {_json.dumps({'tool_result': result, 'tool': tc['name']})}\n\n"
                            tool_results.append({'type': 'tool_result', 'tool_use_id': tc['id'],
                                                 'content': _json.dumps(result, ensure_ascii=False)})
                        ai_messages.append({'role': 'user', 'content': tool_results})

                    # ── OpenAI-compatible tool calling ────────────────────────
                    else:
                        hdrs = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
                        if prov.get('extra_headers'): hdrs.update(prov['extra_headers'])
                        r = rq.post(prov['url'],
                                   json={'model': mn, 'messages': ai_messages[-20:],
                                        'max_tokens': 4096, 'tools': AGENT_TOOLS,
                                        'tool_choice': 'auto'},
                                   headers=hdrs, timeout=120)
                        if r.status_code != 200:
                            yield f"data: {_json.dumps({'error': f'HTTP {r.status_code}'})}\n\n"
                            break
                        resp = r.json()
                        msg  = resp['choices'][0]['message']
                        stop = resp['choices'][0].get('finish_reason', '')
                        if msg.get('content'):
                            text = msg['content']
                            for i in range(0, len(text), 40):
                                yield f"data: {_json.dumps({'chunk': text[i:i+40]})}\n\n"
                        tool_calls = msg.get('tool_calls', [])
                        if stop == 'stop' or not tool_calls:
                            yield "data: [DONE]\n\n"; return
                        ai_messages.append(msg)
                        for tc in tool_calls:
                            fn        = tc.get('function', {})
                            tool_name = fn.get('name', '')
                            try:   tool_args = _json.loads(fn.get('arguments', '{}'))
                            except: tool_args = {}
                            yield f"data: {_json.dumps({'tool': tool_name, 'args': tool_args})}\n\n"
                            result = _execute_tool(tool_name, tool_args, repo)
                            yield f"data: {_json.dumps({'tool_result': result, 'tool': tool_name})}\n\n"
                            ai_messages.append({'role': 'tool', 'tool_call_id': tc['id'],
                                                'content': _json.dumps(result, ensure_ascii=False)})
                except Exception as e:
                    logger.warning(f'agent_stream iter {iteration}: {e}')
                    yield f"data: {_json.dumps({'error': str(e)[:200]})}\n\n"
                    break
            yield "data: [DONE]\n\n"
            return

        # fallback: دردشة عادية (مزوّد بدون tool-calling)
        meta2 = MODELS.get(model_id, {})
        p2 = meta2.get('provider', '')
        m2 = meta2.get('model', '')
        if p2 and m2:
            key2  = _provider_key(p2)
            prov2 = PROVIDERS.get(p2, {})
            if key2:
                accumulated = []
                if prov2['api_type'] == 'openai':
                    gen = _openai_compat_stream(ai_messages, m2, prov2['url'], key2, prov2.get('extra_headers'))
                elif prov2['api_type'] == 'gemini':
                    gen = _gemini_stream(ai_messages, m2, key2)
                else:
                    gen = iter([])
                for chunk in gen:
                    accumulated.append(chunk)
                    yield f"data: {_json.dumps({'chunk': chunk})}\n\n"
                if accumulated:
                    yield "data: [DONE]\n\n"; return

        yield from _stream_chunks_from_g4f(ai_messages)

    return Response(
        stream_with_context(generate()),
        content_type='text/event-stream',
        headers={'Cache-Control': 'no-cache, no-transform',
                 'X-Accel-Buffering': 'no', 'Connection': 'keep-alive'},
    )


# ─── Classic chat (backward compat) ───────────────────────────────────────────

@code_assistant_bp.route('/admin/code-assistant/chat', methods=['POST'])
@login_required
@_super_admin_required
def chat():
    data        = request.get_json(silent=True) or {}
    messages    = data.get('messages', [])
    model_id    = data.get('model', 'auto')
    repo        = _parse_repo(data.get('repo', ''))
    open_files  = data.get('open_files', [])
    project_map = data.get('project_map', '')
    if not messages:
        return jsonify({'error': 'لا توجد رسائل'}), 400
    system      = _build_system(repo, project_map, open_files)
    ai_messages = [{'role': 'system', 'content': system}] + messages[-20:]
    reply       = _call_ai(ai_messages, model_id)
    return jsonify({'reply': reply})


# ─── Analyze ──────────────────────────────────────────────────────────────────

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
    prompt = (f'لديك مستودع GitHub: {repo}\nشجرة الملفات:\n{tree_text}\n\n'
              'قم بتحليل سريع للمشروع بالعربية:\n'
              '1. نوع المشروع وتقنياته\n2. الملفات الرئيسية ووظيفة كل منها\n'
              '3. هيكل المجلدات\n4. نقاط الدخول والتشغيل\nأجب باختصار ووضوح.')
    summary = _call_ai([{'role': 'user', 'content': prompt}], model)
    return jsonify({'repo': repo, 'files': files, 'file_count': len(files),
                    'summary': summary, 'tree_text': tree_text[:2000]})


# ─── File operations ──────────────────────────────────────────────────────────

@code_assistant_bp.route('/admin/code-assistant/files')
@login_required
@_super_admin_required
def list_files():
    path  = request.args.get('path', '')
    repo  = _parse_repo(request.args.get('repo', ''))
    items, err = _gh_list(path, repo)
    if err: return jsonify({'error': err}), 400
    return jsonify({'items': items, 'path': path, 'repo': repo})


@code_assistant_bp.route('/admin/code-assistant/file')
@login_required
@_super_admin_required
def read_file_route():
    path = request.args.get('path', '')
    repo = _parse_repo(request.args.get('repo', ''))
    if not path: return jsonify({'error': 'path مطلوب'}), 400
    result, err = _gh_read(path, repo)
    if err: return jsonify({'error': err}), 400
    return jsonify(result)


@code_assistant_bp.route('/admin/code-assistant/file', methods=['POST'])
@login_required
@_super_admin_required
def write_file_route():
    data    = request.get_json(silent=True) or {}
    path    = data.get('path', '')
    content = data.get('content', '')
    sha     = data.get('sha', '')
    message = data.get('message', '')
    repo    = _parse_repo(data.get('repo', ''))
    if not path or not content or not sha:
        return jsonify({'error': 'path + content + sha مطلوبة'}), 400
    ok, err, new_sha = _gh_write(path, content, sha, message, repo)
    if not ok: return jsonify({'error': err}), 400
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
    if not path: return jsonify({'error': 'path مطلوب'}), 400
    url  = f'https://api.github.com/repos/{repo}/contents/{path}'
    body = {'message': message,
            'content': base64.b64encode(content.encode('utf-8')).decode('ascii')}
    resp = rq.put(url, json=body, headers=_gh_headers(), timeout=30)
    if resp.status_code in (200, 201):
        new_sha = resp.json().get('content', {}).get('sha', '')
        return jsonify({'success': True, 'msg': f'✅ تم إنشاء {path}', 'sha': new_sha})
    return jsonify({'error': f'HTTP {resp.status_code}: {resp.text[:150]}'}), 400


# ─── Keys — حالة + فحص + رصيد ────────────────────────────────────────────────

@code_assistant_bp.route('/admin/code-assistant/keys')
@login_required
@_super_admin_required
def get_keys():
    """حالة كل مفاتيح API — بدون كشف القيم."""
    result = {}
    for pid, prov in PROVIDERS.items():
        key = _provider_key(pid)
        result[pid] = {
            'name':          prov['name'],
            'icon':          prov['icon'],
            'env_var':       prov['env_var'],
            'has_key':       bool(key),
            'preview':       ('••••' + key[-4:]) if len(key) > 4 else ('••••' if key else ''),
            'hint':          prov.get('hint', ''),
            'models':        prov.get('models', []),
            'default_model': prov.get('default_model', ''),
            'has_balance':   bool(prov.get('balance_url')),
            'supports_tools': prov.get('supports_tools', False),
        }
    token = _gh_token()
    result['github'] = {
        'name': 'GitHub Token', 'icon': '⚡',
        'env_var': 'GITHUB_PERSONAL_ACCESS_TOKEN',
        'has_key': bool(token),
        'preview': ('••••' + token[-4:]) if len(token) > 4 else ('••••' if token else ''),
        'hint': 'github.com/settings/tokens — صلاحية repo',
        'has_balance': False, 'supports_tools': False,
    }
    return jsonify(result)


@code_assistant_bp.route('/admin/code-assistant/keys/test', methods=['POST'])
@login_required
@_super_admin_required
def test_key_route():
    data = request.get_json(silent=True) or {}
    pid  = data.get('provider', '')
    if pid == 'github':
        token = _gh_token()
        if not token: return jsonify({'ok': False, 'msg': 'التوكن غير موجود'})
        try:
            r = rq.get('https://api.github.com/user', headers=_gh_headers(), timeout=10)
            if r.status_code == 200:
                login = r.json().get('login', '')
                return jsonify({'ok': True, 'msg': f'✅ يعمل — المستخدم: {login}'})
            return jsonify({'ok': False, 'msg': f'HTTP {r.status_code}'})
        except Exception as e:
            return jsonify({'ok': False, 'msg': str(e)})
    ok, msg = _test_provider(pid)
    return jsonify({'ok': ok, 'msg': msg})


@code_assistant_bp.route('/admin/code-assistant/keys/balance', methods=['POST'])
@login_required
@_super_admin_required
def balance_route():
    data = request.get_json(silent=True) or {}
    pid  = data.get('provider', '')
    bal, err = _get_balance(pid)
    if err: return jsonify({'error': err}), 400
    return jsonify({'balance': bal})


# ─── Settings ─────────────────────────────────────────────────────────────────

@code_assistant_bp.route('/admin/code-assistant/settings', methods=['GET'])
@login_required
@_super_admin_required
def get_settings():
    """حالة كل المفاتيح — يُستخدم لتحديث لوحة الإعدادات."""
    result = {}
    for pid in PROVIDERS:
        key = _provider_key(pid)
        result[f'has_{pid}_key'] = bool(key)
        result[f'{pid}_preview'] = ('••••' + key[-4:]) if len(key) > 4 else ('••••' if key else '')
    token = _gh_token()
    result['has_github_token'] = bool(token)
    result['token_preview'] = ('••••' + token[-4:]) if len(token) > 4 else ('••••' if token else '')
    # للتوافق
    result['has_openrouter_key'] = result.get('has_openrouter_key', False)
    result['key_preview'] = result.get('openrouter_preview', '')
    return jsonify(result)


@code_assistant_bp.route('/admin/code-assistant/settings', methods=['POST'])
@login_required
@_super_admin_required
def save_settings():
    """
    يحفظ الأسرار في ملف محلي آمن فقط — لا يُرفع إلى GitHub أبداً.
    data_store/.ca_secrets.json موجود في .gitignore.
    """
    data  = request.get_json(silent=True) or {}
    saved = []
    for pid in PROVIDERS:
        val = (data.get(f'{pid}_key') or '').strip()
        if val:
            _save_local_secret(f'{pid}_key', val)
            saved.append(PROVIDERS[pid]['name'])
    gh_tok = (data.get('github_token') or '').strip()
    if gh_tok:
        _save_local_secret('github_token', gh_tok)
        saved.append('GitHub Token')
    if not saved:
        return jsonify({'error': 'لم يُرسَل أي مفتاح'}), 400
    return jsonify({'success': True, 'msg': f'✅ تم الحفظ بأمان: {", ".join(saved)}'})


# ─── Favourite Repos ──────────────────────────────────────────────────────────

@code_assistant_bp.route('/admin/code-assistant/repos', methods=['GET'])
@login_required
@_super_admin_required
def get_repos():
    return jsonify({'repos': _load_repos()})


@code_assistant_bp.route('/admin/code-assistant/repos', methods=['POST'])
@login_required
@_super_admin_required
def add_repo():
    data = request.get_json(silent=True) or {}
    repo = data.get('repo', '').strip()
    if not repo: return jsonify({'error': 'repo مطلوب'}), 400
    repos = _load_repos()
    if repo not in repos:
        repos.insert(0, repo)
        repos = repos[:30]
        _save_repos(repos)
    return jsonify({'success': True, 'repos': repos})


@code_assistant_bp.route('/admin/code-assistant/repos/<path:repo>', methods=['DELETE'])
@login_required
@_super_admin_required
def delete_repo(repo):
    repos = [r for r in _load_repos() if r != repo]
    _save_repos(repos)
    return jsonify({'success': True, 'repos': repos})


# ─── Models ───────────────────────────────────────────────────────────────────

@code_assistant_bp.route('/admin/code-assistant/models')
@login_required
@_super_admin_required
def get_models():
    return jsonify({'models': MODELS, 'has_key': bool(_get_key())})
