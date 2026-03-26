# ==============================================
# UZBEK LANGUAGE PROMPTS FOR LLM-GRAPH-BUILDER
# O'zbekiston Mehnat Kodeksi uchun
# ==============================================

# ENTITY EXTRACTION PROMPT (O'zbek tilida)
ENTITY_EXTRACTION_PROMPT = """
Siz O'zbekiston Mehnat Kodeksi bo'yicha ekspertsiz.
Vazifangiz: Matndan asosiy tushunchalar (entitetlar) va ular o'rtasidagi bog'lanishlarni ajratib olish.

QOIDALAR:
1. Faqat Mehnat Kodeksiga tegishli entitetlarni ajratib oling
2. Quyidagi turdagi entitetlarni aniqlang:
   - MODDA (Article) - qonun moddalari
   - HUQUQ (Right) - xodimlarning huquqlari
   - MAJBURIYAT (Obligation) - ish beruvchi majburiyatlari
   - TATIL (Leave) - ta'til turlari
   - ISH_HAQI (Salary) - mehnat haqi to'lovlari
   - JAZO (Penalty) - intizomiy jazolar
   - SHARTNOMA (Contract) - mehnat shartnomasi
   - VAQT (Time) - ish vaqti, muddatlar

3. Bog'lanishlarni aniqlang:
   - BELONGS_TO (tegishli)
   - DEFINES (belgilaydi)
   - TALAB_QILADI (talab qiladi)
   - BERADI (beradi)
   - TASHKIL_TOPADI (tashkil topadi)
   - TO'LANADI (to'lanadi)

Misol:
INPUT: "115-modda. Xodimlarga yillik asosiy ta'til 21 kalendar kunidan kam bo'lmasdan beriladi."
OUTPUT:
{
  "entities": [
    {"label": "MODDA", "value": "115-modda"},
    {"label": "TATIL", "value": "yillik asosiy ta'til"},
    {"label": "VAQT", "value": "21 kalendar kuni"}
  ],
  "relationships": [
    {"from": "115-modda", "type": "BELONGS_TO", "to": "yillik asosiy ta'til"},
    {"from": "yillik asosiy ta'til", "type": "TASHKIL_TOPADI", "to": "21 kalendar kuni"}
  ]
}

MATN:
{text}
"""

# RELATIONSHIP EXTRACTION PROMPT (O'zbek tilida)
RELATIONSHIP_EXTRACTION_PROMPT = """
Siz Mehnat Kodeksi bo'yicha graf bog'lanishlari ekspertisiz.

Vazifangiz: Berilgan matndan quyidagi bog'lanishlarni ajratib olish:

BOG'LANISH TURLARI:
1. BELONGS_TO (tegishli) - modda bo'lim yoki bobga tegishli
2. CONTAINS (o'z ichiga oladi) - bob moddalarni o'z ichiga oladi
3. DEFINES (belgilaydi) - modda huquq yoki majburiyatni belgilaydi
4. REQUIRES (talab qiladi) - shart bajarilishi kerak
5. GRANTS (beradi) - huquq beradi
6. RESTRICTS (cheklaydi) - cheklov qo'yadi
7. APPLIES_TO (qo'llaniladi) - qaysi toifaga qo'llaniladi
8. PRECEDES (oldidan keladi) - jarayon tartibi
9. FOLLOWS (keyinidan keladi) - keyingi jarayon
10. REFERENCES (havola qiladi) - boshqa moddaga havola

Misol:
INPUT: "Xodimlarga yillik asosiy ta'til beriladi. Ta'til haqi saqlanadi."
OUTPUT:
[
  {"subject": "xodim", "predicate": "GRANTS", "object": "yillik asosiy ta'til"},
  {"subject": "yillik asosiy ta'til", "predicate": "APPLIES_TO", "object": "xodim"},
  {"subject": "ta'til", "predicate": "HAS_PROPERTY", "object": "haqi saqlanadi"}
]

MATN:
{text}
"""

# SCHEMA EXTRACTION PROMPT (O'zbek tilida)
SCHEMA_EXTRACTION_PROMPT = """
Siz graf sxemalarini yaratish bo'yicha ekspertsiz.

Vazifangiz: Mehnat Kodeksi matni asosida umumlashtirilgan graf sxemasini yaratish.

Natija quyidagi formatda bo'lishi kerak:
{{"triplets": ["<NodeType1>-<RELATIONSHIP_TYPE>-><NodeType2>"]}}

Misol:
INPUT: "115-modda. Xodimlarga yillik asosiy ta'til 21 kalendar kunidan kam bo'lmasdan beriladi. 116-modda. Yillik qo'shimcha ta'tillar beriladi."
OUTPUT:
{{"triplets": [
  "MODDA-BELONGS_TO->BOB",
  "MODDA-DEFINES->HUQUQ",
  "HUQUQ-APPLIES_TO->XODIM",
  "TATIL-HAS_DURATION->VAQT",
  "MODDA-REFERENCES->MODDA"
]}}

MATN:
{text}
"""

# GRAPH CLEANUP PROMPT (O'zbek tilida)
GRAPH_CLEANUP_PROMPT = """
Siz graf ma'lumotlarini tozalash bo'yicha ekspertsiz.

Vazifangiz: Grafdb dan ortiqcha yoki noto'g'ri bog'lanishlarni olib tashlash.

QOIDALAR:
1. Faqat semantik jihatdan to'g'ri bog'lanishlarni qoldiring
2. Takrorlanuvchi tugunlarni birlashtiring
3. Mantiqiy bog'lanishlarni tekshiring
4. O'zbek tilidagi terminlarni to'g'ri ishlatilishini tekshiring

INPUT: {graph_data}
OUTPUT: {{
  "nodes_to_merge": [],
  "relationships_to_remove": [],
  "validation_errors": []
}}
"""

# CHUNK PROCESSING PROMPT (O'zbek tilida)
CHUNK_PROCESSING_PROMPT = """
Siz O'zbekiston Mehnat Kodeksi matnini qayta ishlash bo'yicha ekspertsiz.

Vazifangiz:
1. Matnni mantiqiy qismlarga (chunk) bo'lish
2. Har bir chunk uchun metadata yaratish:
   - modda_number (modda raqami)
   - bob_title (bob nomi)
   - code (kodeks kodi: MK)
   - language (til: uz)

3. Har bir chunk uchun qisqacha mazmun (summary) yaratish

MATN:
{text}

OUTPUT FORMAT (JSON):
{{
  "chunks": [
    {{
      "id": "chunk_001",
      "text": "...",
      "metadata": {{
        "modda_number": "115",
        "bob_title": "Mehnat ta'tili",
        "code": "MK",
        "language": "uz"
      }},
      "summary": "..."
    }}
  ]
}}
"""
