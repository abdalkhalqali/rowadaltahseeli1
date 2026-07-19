import os, smtplib, logging, requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

logger = logging.getLogger(__name__)


# ── Resend API (الأولوية الأولى — يعمل على Render وReplit) ───────────────
def _send_via_resend(to: str, subject: str, html: str):
    api_key = os.getenv("RESEND_API_KEY", "")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY غير مضبوط")

    from_email = os.getenv("RESEND_FROM_EMAIL") \
              or os.getenv("SENDGRID_FROM_EMAIL") \
              or "onboarding@resend.dev"

    payload = {
        "from":    f"رواد التحصيلي <{from_email}>",
        "to":      [to],
        "subject": subject,
        "html":    html,
    }
    resp = requests.post(
        "https://api.resend.com/emails",
        json=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=20
    )
    logger.info(f"[RESEND] status={resp.status_code} body={resp.text[:200]}")
    if resp.status_code not in (200, 201, 202):
        raise RuntimeError(f"Resend error {resp.status_code}: {resp.text[:300]}")


# ── SendGrid HTTP (الأولوية الثانية) ─────────────────────────────────────
def _send_via_sendgrid(to: str, subject: str, html: str):
    api_key    = os.getenv("SENDGRID_API_KEY", "")
    from_email = os.getenv("SENDGRID_FROM_EMAIL", "")
    if not api_key or not from_email:
        raise RuntimeError("SENDGRID_API_KEY أو SENDGRID_FROM_EMAIL غير مضبوط")

    payload = {
        "personalizations": [{"to": [{"email": to}]}],
        "from": {"email": from_email, "name": "رواد التحصيلي"},
        "subject": subject,
        "content": [{"type": "text/html", "value": html}],
    }
    resp = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        json=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=20
    )
    logger.info(f"[SENDGRID] status={resp.status_code}")
    if resp.status_code not in (200, 201, 202):
        raise RuntimeError(f"SendGrid error {resp.status_code}: {resp.text[:300]}")


# ── Gmail SMTP (احتياطي أخير — يعمل على Replit فقط) ─────────────────────
def _send_via_gmail(to: str, subject: str, html: str):
    username = os.getenv("MAIL_USERNAME", "")
    password = os.getenv("MAIL_PASSWORD", "").replace(" ", "")
    if not username or not password:
        raise RuntimeError("MAIL_USERNAME أو MAIL_PASSWORD غير مضبوط")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"]    = Header(f"رواد التحصيلي <{username}>", "utf-8")
    msg["To"]      = to
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(username, password)
        server.send_message(msg)


# ── الدالة الموحّدة: تجرب بالترتيب حتى تنجح ─────────────────────────────
# الترتيب: Gmail أولاً (يعمل دائماً) ← SendGrid ← Resend احتياطي
def _send_email(to: str, subject: str, html: str):
    errors = []

    # 1) Gmail SMTP — الأولوية الأولى لأنه يصل لجميع البريد
    if os.getenv("MAIL_USERNAME") and os.getenv("MAIL_PASSWORD"):
        try:
            logger.info(f"[MAIL] محاولة Gmail SMTP → {to}")
            _send_via_gmail(to, subject, html)
            logger.info(f"[MAIL] ✅ Gmail نجح → {to}")
            return
        except Exception as e:
            logger.warning(f"[MAIL] Gmail فشل: {e}")
            errors.append(f"Gmail: {e}")

    # 2) SendGrid
    if os.getenv("SENDGRID_API_KEY"):
        try:
            logger.info(f"[MAIL] محاولة SendGrid → {to}")
            _send_via_sendgrid(to, subject, html)
            logger.info(f"[MAIL] ✅ SendGrid نجح → {to}")
            return
        except Exception as e:
            logger.warning(f"[MAIL] SendGrid فشل: {e}")
            errors.append(f"SendGrid: {e}")

    # 3) Resend — احتياطي أخير (يحتاج دومين مُتحقق للوصول لأي بريد)
    if os.getenv("RESEND_API_KEY"):
        try:
            logger.info(f"[MAIL] محاولة Resend → {to}")
            _send_via_resend(to, subject, html)
            logger.info(f"[MAIL] ✅ Resend نجح → {to}")
            return
        except Exception as e:
            logger.warning(f"[MAIL] Resend فشل: {e}")
            errors.append(f"Resend: {e}")

    raise RuntimeError("فشل إرسال البريد من جميع الطرق: " + " | ".join(errors))


# ── رمز التحقق OTP ────────────────────────────────────────────────────────
def send_otp_email(email: str, name: str, otp: str):
    html = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#080B14;font-family:Arial,sans-serif;">
  <div style="max-width:520px;margin:40px auto;background:#0D1628;border-radius:16px;
              border:1px solid #FFB800;overflow:hidden;">
    <div style="background:linear-gradient(135deg,#FFB800,#FF8C00);padding:30px;text-align:center;">
      <h1 style="color:#080B14;margin:0;font-size:26px;">رواد التحصيلي</h1>
      <p style="color:#080B14;margin:8px 0 0;font-size:14px;">كُن رائداً لا تابعاً</p>
    </div>
    <div style="padding:32px;text-align:center;">
      <h2 style="color:#F8FAFC;margin:0 0 8px;">مرحباً {name}</h2>
      <p style="color:#94A3B8;margin:0 0 24px;">رمز التحقق الخاص بك:</p>
      <div style="background:#1E293B;border:2px solid #FFB800;border-radius:12px;
                  padding:20px;margin:0 auto 24px;display:inline-block;">
        <span style="font-size:40px;font-weight:900;color:#FFB800;letter-spacing:10px;">{otp}</span>
      </div>
      <p style="color:#94A3B8;font-size:13px;">صالح لمدة <strong style="color:#FFB800;">10 دقائق</strong> فقط</p>
      <p style="color:#64748B;font-size:12px;margin-top:20px;">
        إذا لم تطلب هذا الرمز، تجاهل هذه الرسالة.
      </p>
    </div>
    <div style="background:#0A0E1A;padding:16px;text-align:center;">
      <p style="color:#475569;font-size:12px;margin:0;">© 2025 منصة رواد التحصيلي الاحترافية</p>
    </div>
  </div>
</body>
</html>"""
    _send_email(email, "رمز التحقق - منصة رواد التحصيلي", html)


# ── إشعار ترقية مشرف ──────────────────────────────────────────────────────
def send_promotion_email(email: str, name: str, role: str, permissions: dict, dashboard_url: str):
    perm_labels = {
        'perm_questions':    '📚 إدارة الأسئلة',
        'perm_users':        '👥 إدارة المستخدمين',
        'perm_community':    '💬 إدارة المجتمع',
        'perm_analytics':    '📊 الإحصائيات والتقارير',
        'perm_notifications':'🔔 إرسال الإشعارات',
    }
    granted = [label for key, label in perm_labels.items() if permissions.get(key)]
    perms_html = ''.join(
        f'<li style="padding:6px 0;color:#00E5FF;font-size:14px;">{p}</li>'
        for p in granted
    ) if granted else '<li style="color:#94A3B8;">لا توجد صلاحيات محددة</li>'

    html = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#080B14;font-family:Arial,sans-serif;">
  <div style="max-width:540px;margin:40px auto;background:#0D1628;border-radius:16px;
              border:1px solid #00E5FF;overflow:hidden;">
    <div style="background:linear-gradient(135deg,#1E3A5F,#0D1628);padding:30px;text-align:center;
                border-bottom:2px solid #00E5FF;">
      <div style="font-size:48px;margin-bottom:10px;">🎖️</div>
      <h1 style="color:#FFB800;margin:0;font-size:24px;">تهانينا {name}!</h1>
      <p style="color:#94A3B8;margin:8px 0 0;font-size:14px;">لقد تمت ترقيتك في منصة رواد التحصيلي</p>
    </div>
    <div style="padding:32px;">
      <div style="background:#1E293B;border-radius:12px;padding:20px;margin-bottom:24px;
                  border-right:4px solid #FFB800;">
        <p style="color:#94A3B8;margin:0 0 4px;font-size:12px;">المنصب الجديد</p>
        <p style="color:#FFB800;margin:0;font-size:20px;font-weight:bold;">{role}</p>
      </div>
      <p style="color:#F8FAFC;font-size:15px;margin:0 0 12px;">صلاحياتك في لوحة الإشراف:</p>
      <ul style="list-style:none;padding:0;margin:0 0 28px;background:#1E293B;
                 border-radius:12px;padding:16px;">
        {perms_html}
      </ul>
      <div style="text-align:center;">
        <a href="{dashboard_url}"
           style="display:inline-block;background:linear-gradient(135deg,#FFB800,#FF8C00);
                  color:#080B14;text-decoration:none;padding:14px 36px;border-radius:10px;
                  font-weight:bold;font-size:16px;">
          🚀 الدخول إلى لوحة الإشراف
        </a>
      </div>
    </div>
    <div style="background:#0A0E1A;padding:16px;text-align:center;">
      <p style="color:#475569;font-size:12px;margin:0;">© 2025 منصة رواد التحصيلي الاحترافية</p>
    </div>
  </div>
</body>
</html>"""
    _send_email(email, "تهانينا! تمت ترقيتك إلى مشرف - رواد التحصيلي", html)


# ── نتيجة الاختبار ────────────────────────────────────────────────────────
def send_result_email(email: str, name: str, subject_ar: str, score: float, grade_label: str):
    color = "#10B981" if score >= 75 else "#FFB800" if score >= 50 else "#EF4444"
    html = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#080B14;font-family:Arial,sans-serif;">
  <div style="max-width:520px;margin:40px auto;background:#0D1628;border-radius:16px;
              border:1px solid #00E5FF;overflow:hidden;">
    <div style="background:linear-gradient(135deg,#0D1628,#1E293B);padding:30px;text-align:center;
                border-bottom:2px solid #00E5FF;">
      <h1 style="color:#FFB800;margin:0;">نتيجة اختبارك</h1>
    </div>
    <div style="padding:32px;text-align:center;">
      <h2 style="color:#F8FAFC;">مرحباً {name}</h2>
      <p style="color:#94A3B8;">نتيجة اختبار <strong style="color:#00E5FF;">{subject_ar}</strong></p>
      <div style="background:#1E293B;border-radius:50%;width:120px;height:120px;
                  margin:20px auto;display:flex;align-items:center;justify-content:center;
                  border:4px solid {color};">
        <span style="font-size:32px;font-weight:900;color:{color};">{score}%</span>
      </div>
      <div style="background:#1E293B;border-radius:10px;padding:16px;margin-top:16px;">
        <span style="color:{color};font-size:22px;font-weight:bold;">{grade_label}</span>
      </div>
    </div>
    <div style="background:#0A0E1A;padding:16px;text-align:center;">
      <p style="color:#475569;font-size:12px;margin:0;">© 2025 رواد التحصيلي</p>
    </div>
  </div>
</body>
</html>"""
    try:
        _send_email(email, f"نتيجة اختبار {subject_ar} - رواد التحصيلي", html)
    except Exception:
        pass
