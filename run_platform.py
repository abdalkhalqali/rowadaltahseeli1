"""
نقطة تشغيل منصة رواد التحصيلي الاحترافية
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'coach_tahseeli'))
os.chdir(os.path.join(os.path.dirname(__file__), 'coach_tahseeli'))

from app import create_app

app = create_app()

if __name__ == '__main__':
    print("🚀 منصة رواد التحصيلي — تشغيل على المنفذ 5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
