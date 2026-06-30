from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from extensions import db
from models import Competition, CompetitionParticipant, Question
from services.competition_service import (
    get_competition_questions,
    submit_competition_answers,
    get_leaderboard
)

competition_bp = Blueprint('competition', __name__)

@competition_bp.route('/')
@login_required
def index():
    active   = Competition.query.filter_by(status='active').all()
    upcoming = Competition.query.filter_by(status='upcoming').all()
    finished = Competition.query.filter_by(status='finished').order_by(
               Competition.end_time.desc()).limit(10).all()
    return render_template('competitions/index.html',
                           active=active, upcoming=upcoming, finished=finished)

@competition_bp.route('/join/<int:comp_id>', methods=['GET', 'POST'])
@login_required
def join(comp_id):
    comp = Competition.query.get_or_404(comp_id)

    if not comp.is_joinable:
        flash('هذه المسابقة غير متاحة للانضمام', 'warning')
        return redirect(url_for('competition.index'))

    existing = CompetitionParticipant.query.filter_by(
        competition_id=comp_id, user_id=current_user.id).first()
    if existing and existing.submitted:
        return redirect(url_for('competition.leaderboard', comp_id=comp_id))

    if request.method == 'POST':
        if not existing:
            participant = CompetitionParticipant(
                competition_id=comp_id, user_id=current_user.id)
            db.session.add(participant)
            db.session.commit()
        return redirect(url_for('competition.live', comp_id=comp_id))

    return render_template('competitions/join.html', comp=comp)

@competition_bp.route('/live/<int:comp_id>', methods=['GET', 'POST'])
@login_required
def live(comp_id):
    comp = Competition.query.get_or_404(comp_id)
    participant = CompetitionParticipant.query.filter_by(
        competition_id=comp_id, user_id=current_user.id).first()

    if not participant:
        return redirect(url_for('competition.join', comp_id=comp_id))

    if participant.submitted:
        return redirect(url_for('competition.leaderboard', comp_id=comp_id))

    if request.method == 'POST':
        data       = request.get_json()
        answers    = data.get('answers', {})
        time_taken = data.get('time_taken', 0)
        result     = submit_competition_answers(participant, answers, time_taken)
        return jsonify({'success': True, 'score': result['score'],
                        'correct': result['correct'],
                        'redirect': url_for('competition.leaderboard', comp_id=comp_id)})

    questions = get_competition_questions(comp)
    return render_template('competitions/live.html', comp=comp,
                           questions=questions, participant=participant)

@competition_bp.route('/leaderboard/<int:comp_id>')
@login_required
def leaderboard(comp_id):
    comp     = Competition.query.get_or_404(comp_id)
    rankings = get_leaderboard(comp_id)
    my_rank  = next((r for r in rankings if r['user_id'] == current_user.id), None)
    return render_template('competitions/leaderboard.html',
                           comp=comp, rankings=rankings, my_rank=my_rank)

@competition_bp.route('/my-competitions')
@login_required
def my_competitions():
    parts = (CompetitionParticipant.query
             .filter_by(user_id=current_user.id)
             .order_by(CompetitionParticipant.joined_at.desc()).all())
    return render_template('competitions/my_competitions.html', parts=parts)
