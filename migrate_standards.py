import sqlite3

DB = 'coach_tahseeli/tahseeli.db'

NEW_NAMES = {
    1:  'طبيعة العلم وتاريخ تطور الفيزياء',
    2:  'المنهج العلمي وطرق البحث والقياس',
    3:  'المختبرات وإجراءات السلامة والمهارات المختبرية',
    4:  'المهارات الرياضية في الفيزياء',
    5:  'الميكانيكا والحركة والقوى والشغل والطاقة',
    6:  'الموائع (الهيدروستاتيكا والهيدروديناميكا)',
    7:  'خواص المادة الصلبة وحالات المادة',
    8:  'الكهرباء الساكنة',
    9:  'التيار الكهربائي والدوائر الكهربائية',
    10: 'المغناطيسية والكهرومغناطيسية',
    11: 'الحرارة والديناميكا الحرارية وقوانين الغازات',
    12: 'الموجات الميكانيكية والصوت',
    13: 'الضوء والبصريات',
    14: 'الفيزياء الحديثة ونظرية الكم',
    15: 'الفيزياء النووية والذرية',
    16: 'علاقة الفيزياء بالعلوم الأخرى وتطبيقاتها',
    17: 'استراتيجيات ومهارات تدريس الفيزياء والتوجهات الحديثة في التربية العلمية',
    18: 'التخطيط للدرس وتنفيذه وإدارة بيئة التعلم وأساليب التقويم',
}

conn = sqlite3.connect(DB)
cur = conn.cursor()

print("=== Step 1: Remapping educational standards (platform م1-م9) → م17 and م18 ===")

# platform م2 (نظريات التعلم) → م17
cur.execute("UPDATE pro_license_questions SET standard_num='17', standard_name=? WHERE standard_num='2'", (NEW_NAMES[17],))
print(f"  م2→م17: {cur.rowcount} سؤال")

# platform م4 (استراتيجيات التدريس) → م17
cur.execute("UPDATE pro_license_questions SET standard_num='17', standard_name=? WHERE standard_num='4'", (NEW_NAMES[17],))
print(f"  م4→م17: {cur.rowcount} سؤال")

# platform م7 (توظيف التكنولوجيا) → م17
cur.execute("UPDATE pro_license_questions SET standard_num='17', standard_name=? WHERE standard_num='7'", (NEW_NAMES[17],))
print(f"  م7→م17: {cur.rowcount} سؤال")

# platform م8 (التعلم النشط) → م17
cur.execute("UPDATE pro_license_questions SET standard_num='17', standard_name=? WHERE standard_num='8'", (NEW_NAMES[17],))
print(f"  م8→م17: {cur.rowcount} سؤال")

# platform م1 (مبادئ تربوية) → م18
cur.execute("UPDATE pro_license_questions SET standard_num='18', standard_name=? WHERE standard_num='1'", (NEW_NAMES[18],))
print(f"  م1→م18: {cur.rowcount} سؤال")

# platform م3 (تخطيط التدريس) → م18
cur.execute("UPDATE pro_license_questions SET standard_num='18', standard_name=? WHERE standard_num='3'", (NEW_NAMES[18],))
print(f"  م3→م18: {cur.rowcount} سؤال")

# platform م5 (التقويم والقياس) → م18
cur.execute("UPDATE pro_license_questions SET standard_num='18', standard_name=? WHERE standard_num='5'", (NEW_NAMES[18],))
print(f"  م5→م18: {cur.rowcount} سؤال")

# platform م6 (إدارة بيئة التعلم) → م18
cur.execute("UPDATE pro_license_questions SET standard_num='18', standard_name=? WHERE standard_num='6'", (NEW_NAMES[18],))
print(f"  م6→م18: {cur.rowcount} سؤال")

# platform م9 (الأخلاقيات) → م18
cur.execute("UPDATE pro_license_questions SET standard_num='18', standard_name=? WHERE standard_num='9'", (NEW_NAMES[18],))
print(f"  م9→م18: {cur.rowcount} سؤال")

print("\n=== Step 2: Remapping physics standards ===")

# platform م10 (ميكانيكا) + م11 (شغل وطاقة) → م5
cur.execute("UPDATE pro_license_questions SET standard_num='5', standard_name=? WHERE standard_num='10'", (NEW_NAMES[5],))
print(f"  م10→م5: {cur.rowcount} سؤال")
cur.execute("UPDATE pro_license_questions SET standard_num='5', standard_name=? WHERE standard_num='11'", (NEW_NAMES[5],))
print(f"  م11→م5: {cur.rowcount} سؤال")

# platform م13 (موجات وصوت) → م12
cur.execute("UPDATE pro_license_questions SET standard_num='12', standard_name=? WHERE standard_num='13'", (NEW_NAMES[12],))
print(f"  م13→م12: {cur.rowcount} سؤال")

# platform م14 (ضوء وبصريات) → م13
cur.execute("UPDATE pro_license_questions SET standard_num='13', standard_name=? WHERE standard_num='14'", (NEW_NAMES[13],))
print(f"  م14→م13: {cur.rowcount} سؤال")

# platform م15 (ديناميكا حرارية) → م11
cur.execute("UPDATE pro_license_questions SET standard_num='11', standard_name=? WHERE standard_num='15'", (NEW_NAMES[11],))
print(f"  م15→م11: {cur.rowcount} سؤال")

# platform م16 (فيزياء حديثة) → م14
cur.execute("UPDATE pro_license_questions SET standard_num='14', standard_name=? WHERE standard_num='16'", (NEW_NAMES[14],))
print(f"  م16→م14: {cur.rowcount} سؤال")

# platform م17 (فيزياء نووية) → م15
cur.execute("UPDATE pro_license_questions SET standard_num='15', standard_name=? WHERE standard_num='17'", (NEW_NAMES[15],))
print(f"  م17→م15: {cur.rowcount} سؤال")

# platform م18 (تطبيقات) → م16
cur.execute("UPDATE pro_license_questions SET standard_num='16', standard_name=? WHERE standard_num='18'", (NEW_NAMES[16],))
print(f"  م18→م16: {cur.rowcount} سؤال")

print("\n=== Step 3: Splitting platform م12 (كهرباء ومغناطيسية) ===")

# م8 - كهرباء ساكنة: كولوم، شحنة، مجال كهربائي، جهد، مكثف
static_ids = [218, 219, 223, 571, 574, 577]
cur.execute(f"UPDATE pro_license_questions SET standard_num='8', standard_name=? WHERE id IN ({','.join(map(str,static_ids))})", (NEW_NAMES[8],))
print(f"  →م8 (كهرباء ساكنة): {cur.rowcount} سؤال")

# م9 - تيار كهربائي: أوم، مقاومة، تيار، مكثف، كيرشوف
current_ids = [220, 221, 222, 230, 232, 236, 568, 569, 570, 575, 578, 581, 583, 584]
cur.execute(f"UPDATE pro_license_questions SET standard_num='9', standard_name=? WHERE id IN ({','.join(map(str,current_ids))})", (NEW_NAMES[9],))
print(f"  →م9 (تيار كهربائي): {cur.rowcount} سؤال")

# م10 - مغناطيسية وكهرومغناطيسية
magnet_ids = [224, 225, 226, 227, 228, 231, 233, 235, 572, 573, 576, 579, 580, 582, 585]
cur.execute(f"UPDATE pro_license_questions SET standard_num='10', standard_name=? WHERE id IN ({','.join(map(str,magnet_ids))})", (NEW_NAMES[10],))
print(f"  →م10 (مغناطيسية): {cur.rowcount} سؤال")

# م14 - فيزياء حديثة (الكهروضوئي والطيف الكهرومغناطيسي)
modern_ids = [229, 586]
cur.execute(f"UPDATE pro_license_questions SET standard_num='14', standard_name=? WHERE id IN ({','.join(map(str,modern_ids))})", (NEW_NAMES[14],))
print(f"  →م14 (فيزياء حديثة من م12): {cur.rowcount} سؤال")

# م7 - خواص المادة (الناقل الفائق)
material_ids = [234]
cur.execute(f"UPDATE pro_license_questions SET standard_num='7', standard_name=? WHERE id IN ({','.join(map(str,material_ids))})", (NEW_NAMES[7],))
print(f"  →م7 (خواص المادة من م12): {cur.rowcount} سؤال")

conn.commit()
print("\n=== Step 4: Verify current state before adding new questions ===")
cur.execute("SELECT standard_num, COUNT(*) FROM pro_license_questions GROUP BY standard_num ORDER BY CAST(standard_num AS INTEGER)")
for r in cur.fetchall():
    print(f"  م{r[0]}: {r[1]} سؤال")

conn.close()
print("\nDone! Step 1-3 complete.")
