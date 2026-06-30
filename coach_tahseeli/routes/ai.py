from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from services.ai_service import (
    evaluate_level_with_ai,
    get_study_recommendations
)
ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/evaluate', methods=['POST'])
@login_required
def evaluate():
    data    = request.get_json()
    subject = data.get('subject', 'physics')
    answers = data.get('answers', {})
    result  = evaluate_level_with_ai(subject, answers)
    return jsonify(result)

@ai_bp.route('/recommend', methods=['GET'])
@login_required
def recommend():
    weak = current_user.get_weak_points_list()
    recs = get_study_recommendations(current_user.level, weak)
    return jsonify({'recommendations': recs})


@ai_bp.route('/chat', methods=['POST'])
@login_required
def chat():
    data    = request.get_json()
    message = data.get('message', '')
    subject = data.get('subject', 'general')
    from services.ai_service import ai_chat
    reply = ai_chat(message, subject, current_user.name)
    return jsonify({'reply': reply})
