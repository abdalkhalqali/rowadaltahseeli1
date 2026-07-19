import re, random, string, hashlib
from datetime import datetime

def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def generate_random_code(length: int = 6) -> str:
    return ''.join(random.choices(string.digits, k=length))

def format_date(dt: datetime, arabic: bool = True) -> str:
    if not dt:
        return '—'
    if arabic:
        months = ['يناير','فبراير','مارس','أبريل','مايو','يونيو',
                  'يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر']
        return f"{dt.day} {months[dt.month-1]} {dt.year}"
    return dt.strftime('%Y-%m-%d %H:%M')

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def score_to_grade(pct: float) -> dict:
    if pct >= 90:
        return {'label': 'ممتاز',          'color': '#10B981', 'icon': '🏆'}
    elif pct >= 80:
        return {'label': 'جيد جداً',        'color': '#00E5FF', 'icon': '🌟'}
    elif pct >= 70:
        return {'label': 'جيد',             'color': '#7C3AED', 'icon': '✅'}
    elif pct >= 60:
        return {'label': 'مقبول',           'color': '#FFB800', 'icon': '📈'}
    else:
        return {'label': 'بحاجة لمراجعة',   'color': '#EF4444', 'icon': '📚'}

def subject_arabic(subject: str) -> str:
    mapping = {
        'physics':   'الفيزياء',
        'chemistry': 'الكيمياء',
        'biology':   'الأحياء',
        'math':      'الرياضيات',
        'mixed':     'مختلطة'
    }
    return mapping.get(subject, subject)

def time_since(dt: datetime) -> str:
    if not dt:
        return '—'
    delta = datetime.utcnow() - dt
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return 'منذ لحظات'
    elif seconds < 3600:
        return f'منذ {seconds//60} دقيقة'
    elif seconds < 86400:
        return f'منذ {seconds//3600} ساعة'
    else:
        return f'منذ {seconds//86400} يوم'

def level_arabic(level: str) -> dict:
    levels = {
        'beginner':     {'ar': 'مبتدئ',     'color': '#FFB800', 'icon': '🌱'},
        'intermediate': {'ar': 'متوسط',     'color': '#00E5FF', 'icon': '⚡'},
        'advanced':     {'ar': 'متقدم',     'color': '#10B981', 'icon': '🔥'},
        'unknown':      {'ar': 'غير محدد',  'color': '#94A3B8', 'icon': '❓'},
    }
    return levels.get(level, levels['unknown'])
