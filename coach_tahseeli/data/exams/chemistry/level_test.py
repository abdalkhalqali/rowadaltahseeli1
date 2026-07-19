from data.exams.chemistry.chapter_1 import QUESTIONS as Q1
from data.exams.chemistry.chapter_2 import QUESTIONS as Q2
import random
_pool = Q1 + Q2
QUESTIONS = [{**q, 'exam_type': 'level_test'} for q in random.sample(_pool, min(len(_pool), len(_pool)))]
