# 🚀 GraphRAG - O'zbekiston Mehnat Kodeksi AI Yordamchisi

Ushbu loyiha O'zbekiston Respublikasi Mehnat Kodeksiga nisbatan savollarga javob berish uchun mo'ljallangan GraphRAG (Graph Retrieval-Augmented Generation) tizimi.

## 📁 Loyiha tuzilishi

```
graph_rag_api/
├── .env                        # Konfiguratsiya fayli
├── docker-compose.yml          # Docker orkestratsiyasi
├── Dockerfile                  # Backend Docker obraz
├── requirements.txt            # Python bog'liqliklar
├── main.py                     # FastAPI backend
├── README.md                   # Ushbu fayl
├── data/
│   └── mehnat_kodeksi_processed.json  # Ma'lumotlar JSON
└── chat/
    └── app.py                  # Streamlit chat interfeys
```

## ⚙️ Sozlash

### 1️⃣ `.env` faylini sozlash

`.env` faylini oching va quyidagi qiymatlarni o'zingizga moslang:

```bash
# LLM (agar OpenAI ishlatilsa)
OPENAI_API_KEY=sk-... # Haqiqiy kalitni kiriting

# Agar Ollama ishlatilsa:
# OPENAI_API_BASE=http://host.docker.internal:11434/v1
# LLM_MODEL=llama3.1

# Agar OpenAI ishlatilsa:
OPENAI_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

### 2️⃣ Ma'lumotlar faylini joylashtirish

Öz zamonaviy `mehnat_kodeksi_processed.json` faylingizni `data/` papkasiga joylashtiring:

```bash
cp /path/to/your/mehnat_kodeksi_processed.json graph_rag_api/data/
```

**JSON format:**
```json
{
  "chunks": [
    {
      "id": "chunk_001",
      "text": "Matn qismi...",
      "metadata": {
        "modda_number": "115",
        "code": "MK",
        "bob_title": "Bob nomi"
      }
    }
  ]
}
```

## 🐳 Ishga tushirish

### Docker bilan (Tavsiya etiladi)

```bash
# Loyiha papkasiga o'ting
cd graph_rag_api

# Barcha xizmatlarni ishga tushiring
docker-compose up -d

# Loglarni tekshiring
docker-compose logs -f backend

# Ma'lumotlarni yuklash (agar avtomatik bo'lmasa)
curl -X POST http://localhost:8000/upload

# Xizmat to'xtatilganda
docker-compose down
```

### Mahalliylashtirilgan ishga tushirish (Dockersiz)

```bash
# 1. Virtual muhit yaratish
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Bog'liqliklarni o'rnatish
pip install -r requirements.txt

# 3. Neo4j ishga tushiring (alohida container)
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/LegalGraph2024! \
  neo4j:5.23-community

# 4. Backend ishga tushiring
python main.py

# 5. Chat interfeysini ishga tushiring (boshqa terminal)
cd chat
streamlit run app.py
```

## 🌐 Foydalanish

| Interfeys | Manzil |
|-----------|--------|
| **Chat UI** | http://localhost:8501 |
| **Neo4j Browser** | http://localhost:7474 |
| **API Dokumentatsiya** | http://localhost:8000/docs |
| **Health Check** | http://localhost:8000/health |

## 📝 API Endpointlari

### POST /query
Savol yuboring va javob oling.

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Yillik ta\'til necha kun?"}'
```

**Javob namunasi:**
```json
{
  "answer": "O'zbekiston Mehnat Kodeksiga ko'ra, yillik asosiy ta'til 21 kalendar kunidan kam bo'lmasdan beriladi.",
  "sources": [
    {
      "text": "O'zbekiston Respublikasi Mehnat kodeksiga muvofiq...",
      "modda_number": "115",
      "code": "MK",
      "score": 0.97
    }
  ],
  "modda_numbers": ["115"]
}
```

### POST /upload
Ma'lumotlarni Neo4j ga yuklash.

```bash
curl -X POST "http://localhost:8000/upload"
```

### GET /health
Xizmat holatini tekshirish.

```bash
curl http://localhost:8000/health
```

## 🧪 Test savollar

Quyidagi savollar bilan tizimni sinab ko'ring:

| Savol (O'zbek tilida) | Kutilayotgan natija |
|----------------------|---------------------|
| "Yillik mehnat ta'tili qancha kun?" | 21 kun haqida ma'lumot |
| "Ishdan bo'shatish asoslari" | Bo'shatish sabablari ro'yxati |
| "Dekret ta'tili shartlari" | Homila va bolani parvarish qilish ta'tili |
| "115-modda haqida ma'lumot" | 115-modda matni |
| "Mehnat haqi qanchadan marta to'lanadi?" | Oyiga kamida bir marta |

## 🔧 LLM Proveyderlarini sozlash

### OpenAI
```bash
OPENAI_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

### Ollama (Mahalliylashgan)
```bash
OPENAI_API_BASE=http://host.docker.internal:11434/v1
LLM_MODEL=llama3.1
```

### vLLM
```bash
OPENAI_API_BASE=http://sizning-serveringiz:8000/v1
LLM_MODEL=mistral-7b
```

### SambaNova
```bash
OPENAI_API_BASE=https://api.sambanova.ai/v1
LLM_MODEL=Meta-Llama-3.1-70B
```

## ⚠️ Muhim eslatmalar

1. **Embedding Model**: `paraphrase-multilingual-MiniLM-L12-v2` o'zbek tilini qo'llab-quvvatlaydi
2. **Neo4j Parolemlar**: Vector index va genai procedurelari ruxsat etilgan
3. **Xotira**: Neo4j uchun kamida 4GB RAM tavsiya etiladi
4. **Portlar**: 7474, 7687, 8000, 8501 portlarining bo'sh ekanligini tekshiring

## 🛠 Muammolarni hal qilish

### Neo4j ulanmayapti
```bash
docker-compose logs neo4j
```

### Backend ma'lumotlarni yuklamayapti
```bash
docker-compose logs backend
curl http://localhost:8000/upload
```

### Embedding modeli yuklanmayapti
Birinchi ishga tushirishda modelni yuklash uchun internet kerak. Keyingi marotoba offline ishlaydi.

## 📚 Texnik ma'lumotlar

- **Python**: 3.11
- **FastAPI**: 0.109.0
- **Neo4j**: 5.23 (Community)
- **Sentence Transformers**: 2.3.1
- **OpenAI SDK**: 1.12.0

## 📄 Litsenziya

Bu loyiha ta'lim maqsadida yaratilgan. Mehnat Kodeksining rasmiy matni faqat O'zbekiston Respublikasi Vazirlar Mahkamasining rasmiy saytidan olinishi kerak.