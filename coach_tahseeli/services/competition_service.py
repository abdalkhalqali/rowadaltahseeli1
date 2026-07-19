from models import Competition, CompetitionParticipant, Question, User
from extensions import db
from datetime import datetime
import json, random

def create_competition(data: dict, admin_id: int) -> Competition:
    comp = Competition(
        name=data['name'],
        subject=data['subject'],
        description=data.get('description', ''),
        duration_min=int(data.get('duration_min', 30)),
        total_q=int(data.get('total_q', 20)),
        difficulty=data.get('difficulty', 'mixed'),
        status=data.get('status', 'upcoming'),
        prize=data.get('prize', ''),
        max_participants=int(data.get('max_participants', 100)),
        created_by=admin_id
    )

    if data.get('start_time'):
        try:
            comp.start_time = datetime.fromisoformat(data['start_time'])
        except Exception:
            pass

    db.session.add(comp)
    db.session.flush()

    questions = _select_competition_questions(data['subject'], comp.total_q, data.get('difficulty', 'mixed'))
    comp.questions_ids = json.dumps([q.id for q in questions])
    db.session.commit()
    return comp

def _select_competition_questions(subject: str, count: int, difficulty: str) -> list:
    q = Question.query.filter_by(is_active=True)
    if subject != 'mixed':
        q = q.filter_by(subject=subject)
    if difficulty != 'mixed':
        q = q.filter_by(difficulty=difficulty)
    qs = q.all()
    if len(qs) > count:
        qs = random.sample(qs, count)
    return qs

def get_competition_questions(comp: Competition) -> list:
    ids = comp.get_questions_ids()
    if not ids:
        return []
    return Question.query.filter(Question.id.in_(ids)).all()

def submit_competition_answers(participant: CompetitionParticipant,
                               answers: dict, time_taken: int) -> dict:
    comp      = Competition.query.get(participant.competition_id)
    questions = get_competition_questions(comp)

    correct = 0
    for q in questions:
        user_ans = answers.get(str(q.id), '').upper()
        if user_ans == q.answer.upper():
            correct += 1

    score = (correct * 100) // len(questions) if questions else 0

    participant.answers    = json.dumps(answers)
    participant.correct    = correct
    participant.total_q    = len(questions)
    participant.score      = score
    participant.time_taken = time_taken
    participant.submitted  = True
    participant.finished_at = datetime.utcnow()
    db.session.commit()

    _recalculate_ranks(comp.id)

    return {'score': score, 'correct': correct, 'total': len(questions)}

def _recalculate_ranks(competition_id: int):
    parts = (CompetitionParticipant.query
             .filter_by(competition_id=competition_id, submitted=True)
             .order_by(CompetitionParticipant.score.desc(),
                       CompetitionParticipant.time_taken.asc())
             .all())
    for i, p in enumerate(parts, 1):
        p.rank = i
    db.session.commit()

def get_leaderboard(competition_id: int) -> list:
    parts = (CompetitionParticipant.query
             .filter_by(competition_id=competition_id, submitted=True)
             .order_by(CompetitionParticipant.rank.asc())
             .all())
    result = []
    for p in parts:
        user = User.query.get(p.user_id)
        result.append({
            'rank':       p.rank,
            'user_id':    p.user_id,
            'name':       user.name if user else '—',
            'score':      p.score,
            'correct':    p.correct,
            'total_q':    p.total_q,
            'time_taken': p.time_taken,
        })
    return result
