# 🚀 llm-graph-builder — O'zbekiston Mehnat Kodeksi

Neo4j Labs'ning **llm-graph-builder** loyihasi asosida O'zbekiston Mehnat Kodeksi uchun GraphRAG tizimi.

## 📋 Qisqacha Ma'lumot

Ushbu tizim:
- ✅ **Avtomatik graf bog'lanishlari** - Moddalar, huquqlar, majburiyatlar o'rtasida avtomatik bog'lanishlar yaratadi
- ✅ **Gibrid qidiruv** - Vektor + Graph qidiruv (an'anaviy usuldan ko'ra aniqroq)
- ✅ **O'zbek tili** - Barcha promptlar o'zbek tilida sozlangan
- ✅ **UI Interfeys** - Foydalanuvchi uchun qulay interfeys (8080-port)
- ✅ **Neo4j Graph** - Zamonaviy graf ma'lumotlar bazasi

## 📁 Loyiha Tuzilishi

```
llm_graph_builder/
├── backend/                    # Python FastAPI backend
│   ├── src/
│   │   ├── prompts_uzbek.py   # O'zbek tilida promptlar
│   │   ├── create_chunks.py   # Matnni chunklarga bo'lish
│   │   ├── schema_extraction.py # Sxema ajratib olish
│   │   └── ...
│   ├── .env                    # Konfiguratsiya
│   └── Dockerfile
├── frontend/                   # React UI
├── data/                       # Ma'lumotlar papkasi
│   └── mehnat_kodeksi_processed.json
├── docker-compose-uzbek.yml    # Docker konfiguratsiya
└── README_UZ.md               # Ushbu fayl
```

## ⚙️ 1-Qadam: .env Faylini Sozlash

`backend/.env` fayli allaqachon sozlangan. Agar API kalitni o'zgartirmoqchi bo'lsangiz:

```bash
# backend/.env faylini oching
nano backend/.env

# OPENAI_API_KEY ni o'zgartiring
LLM_MODEL_CONFIG_openrouter_free="openrouter/free,sk-or-v1-YANGI_KALIT"
```

## 📊 2-Qadam: Ma'lumotlarni Joylashtirish

Öz `mehnat_kodeksi_processed.json` faylingizni `data/` papkasiga joylashtiring:

```bash
# Agar sizda tayyor JSON bo'lsa:
cp /path/to/mehnat_kodeksi_processed.json llm_graph_builder/data/

# Yo'q bo'lsa, original loyihadan ko'chiring:
cp ../mehnat_kodeksi_processed.json llm_graph_builder/data/
```

**JSON Format:**
```json
{
  "chunks": [
    {
      "id": "chunk_001",
      "text": "115-modda. Xodimlarga yillik asosiy ta'til 21 kalendar kunidan kam bo'lmasdan beriladi.",
      "metadata": {
        "modda_number": "115",
        "bob_title": "Mehnat ta'tili",
        "code": "MK"
      }
    }
  ]
}
```

## 🐳 3-Qadam: Docker Compose orqali Ishga Tushirish

```bash
# llm_graph_builder papkasiga o'ting
cd llm_graph_builder

# Barcha xizmatlarni ishga tushiring
docker-compose -f docker-compose-uzbek.yml up -d

# Loglarni kuzatish
docker-compose -f docker-compose-uzbek.yml logs -f backend

# Xizmat to'xtatish
docker-compose -f docker-compose-uzbek.yml down
```

## 🌐 4-Qadam: Interfeysni Ochish

| Xizmat | Manzil | Tavsif |
|--------|--------|--------|
| **UI Interface** | http://localhost:8080 | Asosiy interfeys (Graph builder) |
| **Neo4j Browser** | http://localhost:7474 | Neo4j graf brauzeri |
| **API Docs** | http://localhost:8000/docs | FastAPI dokumentatsiya |
| **Health Check** | http://localhost:8000/health | Tizim holati |

### Neo4j Browserga Kirish

```
URL: http://localhost:7474
Username: neo4j
Password: LegalGraph2024!
```

## 📝 5-Qadam: Ma'lumotlarni Yuklash

### UI orqali:

1. http://localhost:8080 manziliga o'ting
2. **"Upload"** bo'limiga kiring
3. **"Local"** manbasini tanlang
4. `mehnat_kodeksi_processed.json` faylini yuklang
5. **"Build Graph"** tugmasini bosing
6. Graf yaratilishini kuting (5-10 daqiqa)

### API orqali:

```bash
# Ma'lumotlarni yuklash
curl -X POST "http://localhost:8000/upload" \
  -H "Content-Type: application/json" \
  -d '{"file_name": "mehnat_kodeksi_processed.json"}'

# Holatni tekshirish
curl "http://localhost:8000/health"
```

## 🔍 6-Qadam: Qidiruv va Savollar

### UI orqali:

1. **"Chat"** yoki **"Explore"** bo'limiga o'ting
2. Savolni yozing (o'zbek tilida)
3. Tizim graf + vektor qidiruvini bajaradi
4. Javob va manbalar ko'rsatiladi

### API orqali:

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "Yillik mehnat ta''tili qancha kun?"}'
```

**Javob:**
```json
{
  "answer": "O'zbekiston Mehnat Kodeksiga ko'ra, yillik asosiy ta'til 21 kalendar kunidan kam bo'lmasdan beriladi.",
  "sources": [
    {
      "text": "115-modda. Xodimlarga yillik asosiy ta'til...",
      "modda_number": "115",
      "score": 0.95
    }
  ],
  "entities": ["MODDA:115", "TATIL:yillik asosiy"],
  "relationships": ["115-modda-DEFINES->yillik ta'til"]
}
```

## 🧪 Test Savollar

| Savol (O'zbekcha) | Kutilayotgan Natija |
|-------------------|---------------------|
| "Yillik mehnat ta'tili qancha kun?" | 21 kun, 115-modda |
| "Dekret ta'tili qanday beriladi?" | Homiladorlik ta'tili, 118-modda |
| "Ishdan bo'shatish asoslari" | 100-modda, asoslar ro'yxati |
| "Mehnat haqi qanchadan marta to'lanadi?" | Oyida kamida 1 marta |
| "115-modda haqida ma'lumot" | 115-modda matni + bog'lanishlar |

## 🔧 Sozlamalarni O'zgartirish

### LLM Modelni O'zgartirish

```bash
# backend/.env faylida
# OpenRouter (tavsiya etiladi):
LLM_MODEL_CONFIG_openrouter_free="openrouter/free,sk-or-v1-..."

# To'g'ridan-to'g'ri OpenAI:
LLM_MODEL_CONFIG_gpt_4o_mini="gpt-4o-mini,sk-..."

# Ollama (lokal):
LLM_MODEL_CONFIG_ollama_llama3="llama3,http://host.docker.internal:11434"
```

### Embedding Model

```bash
# Ko'p tilli (tavsiya etiladi):
EMBEDDING_MODEL="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# OpenAI embeddings:
EMBEDDING_PROVIDER="openai"
EMBEDDING_MODEL="text-embedding-3-small"
```

### Chunk Hajmi

```bash
# backend/.env
TOKEN_CHUNK_SIZE="512"      # Har bir chunk hajmi
CHUNK_OVERLAP="50"          # Overlap hajmi
MAX_TOKEN_CHUNK_SIZE="10000" # Maksimal token
```

## 🛠 Muammolarni Hal Qilish

### 1. Neo4j Ulanmayapti

```bash
# Neo4j loglarini tekshiring
docker-compose -f docker-compose-uzbek.yml logs neo4j

# Qayta ishga tushiring
docker-compose -f docker-compose-uzbek.yml restart neo4j
```

### 2. Backend Ma'lumotlarni Yuklamayapti

```bash
# Backend loglarini tekshiring
docker-compose -f docker-compose-uzbek.yml logs backend

# Bepul API kalitni tekshiring
# OpenRouter: https://openrouter.ai/keys
```

### 3. Embedding Model Yuklanmayapti

Birinchi ishga tushirishda modelni yuklash uchun internet kerak:

```bash
# Modelni oldindan yuklab oling
docker-compose -f docker-compose-uzbek.yml run backend \
  python -c "from sentence_transformers import SentenceTransformer; \
             SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"
```

### 4. UI Ko'rinmayapti

```bash
# Frontend loglarini tekshiring
docker-compose -f docker-compose-uzbek.yml logs frontend

# Brauzer cache'ni tozalang (Ctrl+Shift+R)
```

### 5. Graf Bo'sh (Entitylar Yo'q)

```bash
# Graph creation loglarini tekshiring
curl "http://localhost:8000/graph/status"

# Qo'lda graf yaratish
curl -X POST "http://localhost:8000/graph/generate"
```

## 📚 Texnik Ma'lumotlar

- **Python**: 3.10+
- **FastAPI**: 0.109+
- **Neo4j**: 5.23 (Community)
- **LangChain**: 0.1+
- **Sentence Transformers**: 2.3+
- **React**: 18+

## 📄 Promptlar (O'zbek Tilida)

`backend/src/prompts_uzbek.py` faylida quyidagi promptlar mavjud:

1. **Entity Extraction** - Moddalar, huquqlar, majburiyatlar
2. **Relationship Extraction** - Bog'lanish turlari (BELONGS_TO, DEFINES, ...)
3. **Schema Extraction** - Umumlashtirilgan graf sxemasi
4. **Graph Cleanup** - Graf tozalash
5. **Chunk Processing** - Matnni qayta ishlash

## 🎯 Keyingi Qadamlar

1. ✅ Ma'lumotlarni yuklang
2. ✅ Graf yaratilishini kuting
3. ✅ UI orqali savollar bering
4. ✅ Neo4j Browserda grafni ko'ring
5. 🔄 Promptlarni o'z ehtiyojingizga moslang

## 📞 Yordam

- **GitHub Issues**: https://github.com/neo4j-labs/llm-graph-builder/issues
- **Neo4j Docs**: https://neo4j.com/docs/
- **O'zbek tilidagi hujjatlari**: `docs/` papkasida

## 🔑 Kalit So'zlar

- GraphRAG
- Neo4j
- O'zbekiston Mehnat Kodeksi
- Entity Extraction
- Relationship Extraction
- Vector Search
- Hybrid Search
- Uzbek NLP

---

**Muallif:** NazarAI - UBS Namangan
**Litsenziya:** MIT
**Til:** O'zbek / English
