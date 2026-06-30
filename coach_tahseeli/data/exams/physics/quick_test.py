from data.exams.physics.chapter_1 import QUESTIONS as Q1
import random
QUESTIONS = [{**q, 'exam_type': 'quick_test'} for q in random.sample(Q1, min(10, len(Q1)))]
