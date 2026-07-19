import os, json, uuid
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, send_from_directory, abort
from flask_login import login_required, current_user
from extensions import db
from models.cms import ContentSection, ContentFile, ContentCode
from werkzeug.utils import secure_filename

cms_bp = Blueprint('cms', __name__)

def _get_upload_folder():
    from flask import current_app
    base = current_app.config.get('PERSISTENT_UPLOADS', os.path.join(os.path.dirname(__file__), '..', 'static', 'uploads'))
    return os.path.join(base, 'cms')

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'static', 'uploads', 'cms')
ALLOWED_EXT   = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'webm', 'mp3',
                 'py', 'html', 'js', 'css', 'txt', 'zip', 'docx', 'xlsx', 'pptx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

def get_file_type(filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext == 'pdf':                          return 'pdf'
    if ext in ('png','jpg','jpeg','gif','webp'): return 'image'
    if ext in ('mp4','webm'):                 return 'video'
    if ext == 'mp3':                          return 'audio'
    if ext in ('py','html','js','css','txt'): return 'code'
    return 'file'

def _ai_analyze(content_text, content_type='text'):
    try:
        from services.ai_service import _call_ai
        prompt = f"""أنت محلل محتوى تعليمي. حلّل المحتوى التالي وأعد JSON فقط بهذا الشكل:
{{"topic": "الموضوع الرئيسي", "keywords": "كلمة1، كلمة2، كلمة3", "summary": "ملخص قصير في جملتين", "difficulty": "سهل/متوسط/صعب"}}

المحتوى:
{content_text[:1500]}

أعد JSON فقط بدون أي نص إضافي."""
        result = _call_ai([{'role': 'user', 'content': prompt}], max_tokens=300)
        if result:
            start = result.find('{')
            end   = result.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(result[start:end])
    except Exception:
        pass
    return {}

def _build_tree(parent_id=None):
    sections = ContentSection.query.filter_by(parent_id=parent_id).order_by(ContentSection.order_num).all()
    result = []
    for s in sections:
        node = s.to_dict(include_children=False)
        node['children'] = _build_tree(s.id)
        result.append(node)
    return result

# ═══════════════════════════════════════
# واجهة المالك / المشرف
# ═══════════════════════════════════════

@cms_bp.route('/admin/cms/')
@login_required
def admin_cms():
    if not current_user.is_admin:
        abort(403)
    tree     = _build_tree()
    sections = ContentSection.query.order_by(ContentSection.order_num).all()
    files    = ContentFile.query.filter_by(is_active=True).order_by(ContentFile.created_at.desc()).all()
    codes    = ContentCode.query.filter_by(is_active=True).order_by(ContentCode.created_at.desc()).all()
    return render_template('admin_cms.html', tree=tree, sections=sections, files=files, codes=codes)

@cms_bp.route('/admin/cms/section/add', methods=['POST'])
@login_required
def admin_cms_section_add():
    if not current_user.is_admin:
        abort(403)
    name         = request.form.get('name','').strip()
    icon         = request.form.get('icon','📁').strip()
    parent_id    = request.form.get('parent_id') or None
    order_num    = int(request.form.get('order_num', 0))
    link         = request.form.get('link','').strip()
    fallback_msg = request.form.get('fallback_msg','').strip()
    description  = request.form.get('description','').strip()
    if not name:
        flash('اسم القسم مطلوب', 'warning')
        return redirect(url_for('cms.admin_cms'))
    s = ContentSection(name=name, icon=icon, parent_id=parent_id,
                       order_num=order_num, link=link,
                       fallback_msg=fallback_msg, description=description)
    db.session.add(s)
    db.session.commit()
    flash(f'✅ تم إضافة القسم "{name}"', 'success')
    return redirect(url_for('cms.admin_cms'))

@cms_bp.route('/admin/cms/section/<int:sid>/edit', methods=['POST'])
@login_required
def admin_cms_section_edit(sid):
    if not current_user.is_admin:
        abort(403)
    s = ContentSection.query.get_or_404(sid)
    s.name         = request.form.get('name', s.name).strip()
    s.icon         = request.form.get('icon', s.icon).strip()
    s.parent_id    = request.form.get('parent_id') or None
    s.order_num    = int(request.form.get('order_num', s.order_num))
    s.link         = request.form.get('link', s.link).strip()
    s.fallback_msg = request.form.get('fallback_msg', s.fallback_msg).strip()
    s.description  = request.form.get('description', s.description).strip()
    db.session.commit()
    flash('✅ تم تحديث القسم', 'success')
    return redirect(url_for('cms.admin_cms'))

@cms_bp.route('/admin/cms/section/<int:sid>/delete', methods=['POST'])
@login_required
def admin_cms_section_delete(sid):
    if not current_user.is_admin:
        abort(403)
    s = ContentSection.query.get_or_404(sid)
    db.session.delete(s)
    db.session.commit()
    flash('🗑 تم حذف القسم', 'success')
    return redirect(url_for('cms.admin_cms'))

@cms_bp.route('/admin/cms/section/reorder', methods=['POST'])
@login_required
def admin_cms_section_reorder():
    if not current_user.is_admin:
        abort(403)
    data = request.get_json() or {}
    for item in data.get('items', []):
        s = ContentSection.query.get(item['id'])
        if s:
            s.order_num = item['order']
            s.parent_id = item.get('parent_id') or None
    db.session.commit()
    return jsonify({'ok': True})

@cms_bp.route('/admin/cms/file/upload', methods=['POST'])
@login_required
def admin_cms_file_upload():
    if not current_user.is_admin:
        abort(403)
    title      = request.form.get('title','').strip()
    section_id = request.form.get('section_id') or None
    file       = request.files.get('file')

    if not title or not file or file.filename == '':
        flash('العنوان والملف مطلوبان', 'warning')
        return redirect(url_for('cms.admin_cms'))

    if not allowed_file(file.filename):
        flash('نوع الملف غير مسموح', 'danger')
        return redirect(url_for('cms.admin_cms'))

    folder = _get_upload_folder()
    os.makedirs(folder, exist_ok=True)
    ext      = file.filename.rsplit('.', 1)[1].lower()
    fname    = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(folder, fname)
    file.save(filepath)
    file_size = os.path.getsize(filepath)
    file_url  = f"/cms/files/{fname}"

    cf = ContentFile(
        title=title, section_id=section_id,
        file_path=filepath, file_url=file_url,
        file_type=get_file_type(file.filename),
        file_size=file_size,
        created_by=current_user.id
    )
    db.session.add(cf)
    db.session.commit()

    # تحليل ذكي تلقائي
    if ext in ('pdf','txt','py','html','js'):
        try:
            text = ''
            if ext == 'pdf':
                import fitz
                doc = fitz.open(filepath)
                text = ' '.join(p.get_text() for p in doc)[:1500]
            else:
                with open(filepath, 'r', errors='ignore') as f:
                    text = f.read(1500)
            if text:
                ai = _ai_analyze(text)
                if ai:
                    cf.ai_topic     = ai.get('topic','')
                    cf.ai_keywords  = ai.get('keywords','')
                    cf.ai_summary   = ai.get('summary','')
                    cf.ai_difficulty= ai.get('difficulty','')
                    db.session.commit()
        except Exception:
            pass

    flash(f'✅ تم رفع الملف "{title}"', 'success')
    return redirect(url_for('cms.admin_cms'))

@cms_bp.route('/admin/cms/file/<int:fid>/delete', methods=['POST'])
@login_required
def admin_cms_file_delete(fid):
    if not current_user.is_admin:
        abort(403)
    cf = ContentFile.query.get_or_404(fid)
    try:
        if cf.file_path and os.path.exists(cf.file_path):
            os.remove(cf.file_path)
    except Exception:
        pass
    cf.is_active = False
    db.session.commit()
    flash('🗑 تم حذف الملف', 'success')
    return redirect(url_for('cms.admin_cms'))

@cms_bp.route('/admin/cms/file/<int:fid>/edit', methods=['POST'])
@login_required
def admin_cms_file_edit(fid):
    if not current_user.is_admin:
        abort(403)
    cf = ContentFile.query.get_or_404(fid)
    cf.title      = request.form.get('title', cf.title).strip()
    cf.section_id = request.form.get('section_id') or None
    db.session.commit()
    flash('✅ تم تحديث الملف', 'success')
    return redirect(url_for('cms.admin_cms'))

@cms_bp.route('/admin/cms/code/add', methods=['POST'])
@login_required
def admin_cms_code_add():
    if not current_user.is_admin:
        abort(403)
    title         = request.form.get('title','').strip()
    section_id    = request.form.get('section_id') or None
    code_type     = request.form.get('code_type','python')
    difficulty    = request.form.get('difficulty','medium')
    description   = request.form.get('description','').strip()
    code_content  = request.form.get('code_content','').strip()
    external_url  = request.form.get('external_url','').strip()
    questions_raw = request.form.get('questions_json','[]').strip()

    if not title:
        flash('العنوان مطلوب', 'warning')
        return redirect(url_for('cms.admin_cms'))

    # رفع ملف الكود إن وُجد
    file = request.files.get('code_file')
    if file and file.filename:
        folder = _get_upload_folder()
        os.makedirs(folder, exist_ok=True)
        ext   = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'txt'
        fname = f"code_{uuid.uuid4().hex}.{ext}"
        fpath = os.path.join(folder, fname)
        file.save(fpath)
        with open(fpath, 'r', errors='ignore') as f:
            code_content = f.read()

    try:
        json.loads(questions_raw)
    except Exception:
        questions_raw = '[]'

    cc = ContentCode(
        title=title, section_id=section_id,
        code_type=code_type, difficulty=difficulty,
        description=description, code_content=code_content,
        external_url=external_url, questions_json=questions_raw,
        created_by=current_user.id
    )
    db.session.add(cc)
    db.session.commit()

    # تحليل ذكي تلقائي
    if code_content:
        ai = _ai_analyze(code_content, 'code')
        if ai:
            cc.ai_topic     = ai.get('topic','')
            cc.ai_keywords  = ai.get('keywords','')
            cc.ai_summary   = ai.get('summary','')
            db.session.commit()

    flash(f'✅ تمت إضافة الكود "{title}"', 'success')
    return redirect(url_for('cms.admin_cms'))

@cms_bp.route('/admin/cms/code/<int:cid>/delete', methods=['POST'])
@login_required
def admin_cms_code_delete(cid):
    if not current_user.is_admin:
        abort(403)
    cc = ContentCode.query.get_or_404(cid)
    cc.is_active = False
    db.session.commit()
    flash('🗑 تم حذف الكود', 'success')
    return redirect(url_for('cms.admin_cms'))

@cms_bp.route('/admin/cms/code/<int:cid>/edit', methods=['POST'])
@login_required
def admin_cms_code_edit(cid):
    if not current_user.is_admin:
        abort(403)
    cc = ContentCode.query.get_or_404(cid)
    cc.title       = request.form.get('title', cc.title).strip()
    cc.section_id  = request.form.get('section_id') or None
    cc.code_type   = request.form.get('code_type', cc.code_type)
    cc.difficulty  = request.form.get('difficulty', cc.difficulty)
    cc.description = request.form.get('description', cc.description).strip()
    cc.code_content= request.form.get('code_content', cc.code_content)
    cc.external_url= request.form.get('external_url', cc.external_url).strip()
    db.session.commit()
    flash('✅ تم تحديث الكود', 'success')
    return redirect(url_for('cms.admin_cms'))

@cms_bp.route('/admin/cms/ai-analyze', methods=['POST'])
@login_required
def admin_cms_ai_analyze():
    if not current_user.is_admin:
        abort(403)
    text = request.json.get('text','')
    if not text:
        return jsonify({'error': 'لا يوجد نص للتحليل'}), 400
    ai = _ai_analyze(text)
    if not ai:
        return jsonify({'error': 'الذكاء الاصطناعي غير متاح حالياً — تأكد من إعداد مفتاح OpenRouter في الإعدادات'}), 503
    return jsonify(ai)

# ═══════════════════════════════════════
# واجهة الطالب
# ═══════════════════════════════════════

@cms_bp.route('/cms/')
@login_required
def student_cms():
    tree = _build_tree()
    return render_template('cms_browse.html', tree=tree)

@cms_bp.route('/cms/section/<int:sid>')
@login_required
def cms_section_content(sid):
    section = ContentSection.query.get_or_404(sid)
    files   = ContentFile.query.filter_by(section_id=sid, is_active=True).order_by(ContentFile.created_at.desc()).all()
    codes   = ContentCode.query.filter_by(section_id=sid, is_active=True).order_by(ContentCode.created_at.desc()).all()
    return jsonify({
        'id':          section.id,
        'name':        section.name,
        'icon':        section.icon,
        'link':        section.link,
        'fallback_msg':section.fallback_msg,
        'description': section.description,
        'files':       [f.to_dict() for f in files],
        'codes':       [c.to_dict() for c in codes],
    })

@cms_bp.route('/cms/files/<filename>')
@login_required
def cms_serve_file(filename):
    return send_from_directory(_get_upload_folder(), filename)

@cms_bp.route('/cms/code/<int:cid>')
@login_required
def cms_code_detail(cid):
    cc = ContentCode.query.get_or_404(cid)
    return jsonify(cc.to_dict())

@cms_bp.route('/cms/api/tree')
@login_required
def cms_api_tree():
    return jsonify(_build_tree())
