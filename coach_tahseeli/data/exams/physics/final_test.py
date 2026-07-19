from data.exams.physics.chapter_1 import QUESTIONS as Q1
from data.exams.physics.chapter_2 import QUESTIONS as Q2
QUESTIONS = [{**q, 'exam_type': 'final_test'} for q in (Q1 + Q2)]
