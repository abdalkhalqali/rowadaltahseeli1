from data.exams.physics.chapter_1 import QUESTIONS as Q1
from data.exams.physics.chapter_2 import QUESTIONS as Q2
import random
_pool = Q1 + Q2
QUESTIONS = [{**q, 'exam_type': 'daily_train'} for q in random.sample(_pool, min(15, len(_pool)))]
