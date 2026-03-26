# Knowledge Graph Builder — Bilim Grafigi Yaratuvchi
![Python](https://img.shields.io/badge/Python-yellow)
![FastAPI](https://img.shields.io/badge/FastAPI-green)
![React](https://img.shields.io/badge/React-blue)

Nazorat qilinmagan ma'lumotlarni (PDF, DOC, TXT, YouTube videolari, veb-sahifalar va boshqalar) Katta Til Modellaridan (LLM) foydalanib, tuzilgan Bilim Grafigiga aylantiring va Neo4j da saqlang.

Ushbu ilova turli manbalardan (lokal kompyuter, GCS, S3 bucket yoki veb-manbalar) fayllarni yuklash, kerakli LLM modelini tanlash va Bilim Grafigini yaratish imkonini beradi.

## Boshlash

### **Talablar**
- **Python 3.12 yoki undan yuqori** (lokal/ayrim backend deploy uchun)
- Neo4j Ma'lumotlar bazasi **5.23 yoki undan keyingi versiya**, APOC o'rnatilgan.
  - **Neo4j Aura** ma'lumotlar bazalari (shu jumladan bepul versiya) qo'llab-quvvatlanadi.
  - Agar **Neo4j Desktop** ishlatilsa, backend va frontend ni alohida deploy qilish kerak (docker-compose qo'llab-quvvatlanmaydi).

#### **Backend Sozlash**
1. `backend/example.env` faylini `backend` papkasiga `.env` nomi bilan nusxalangan.
2. Foydalanuvchi ma'lumotlarini oldindan sozlang:
   ```bash
   NEO4J_URI=<sizning-neo4j-uri>
   NEO4J_USERNAME=<sizning-foydalanuvchi-nomi>
   NEO4J_PASSWORD=<sizning-parol>
   NEO4J_DATABASE=<sizning-baza-nomi>
   ```
3. Ishga tushiring:
   ```bash
   cd backend
   python3.12 -m venv venv
   source venv/bin/activate  # Windows da: venv\Scripts\activate
   pip install -r requirements.txt -c constraints.txt
   uvicorn score:app --reload
   ```

## Asosiy Xususiyatlar

### **Bilim Grafigini Yaratish**
- Nazorat qilinmagan ma'lumotlarni zamonaviy LLM yordamida tuzilgan Bilim Grafigiga aylantiring.
- Tugunlar (nodes), bog'lanishlar (relationships) va ularning xususiyatlarini ajratib oling.

### **Sxema Qo'llab-quvvatlash**
- Graflarni yaratish uchun shaxsiy sxema yoki sozlamalarda mavjud sxemalardan foydalaning.

### **Graf Vizualizatsiyasi**
- **Neo4j Bloom** da ma'lumot manbalari uchun graflarni ko'ring.

### **Ma'lumotlar bilan Chat**
- Neo4j bazasidagi ma'lumotlar bilan suhbatlashing.
- Savollaringizga javoblar manbalarini oling.
- Maxsus chat interfeysi uchun **[/chat-only](/chat-only)** marshrutidan foydalaning.

### **Qo'llab-quvvatlanadigan LLM Modellar**
1. OpenAI
2. Gemini
3. Diffbot
4. Azure OpenAI (dev versiya)
5. Anthropic (dev versiya)
6. Fireworks (dev versiya)
7. Groq (dev versiya)
8. Amazon Bedrock (dev versiya)
9. Ollama (dev versiya)
10. Deepseek (dev versiya)
11. Boshqa OpenAI-compatible modellar (dev versiya)

### **Token Ishlatishni Kuzatish**
- Har bir foydalanuvchi va baza ulanishi uchun LLM token ishlatilishini kuzating.
- `TRACK_USER_USAGE` muhit o'zgaruvchisini `true` ga sozlang.
- Kunlik va oylik token chegaralaringizni ko'ring.

### **Embedding Modelini Tanlash**
- Ma'lumotlaringiz uchun turli embedding modellaridan foydalaning.
- **Graf Sozlamalari > Processing Configuration > Select Embedding Model** orqali tanlang.
- Qo'llab-quvvatlanadigan provayderlar: OpenAI, Gemini, Amazon Titan, Sentence Transformers.

#### **Lokal Sozlash**
Embedding modelini lokal sozlash uchun ikki usul:

1. **Foydalanuvchi Kuzatuvi Bilan (`TRACK_USER_USAGE=true`):**
   - `TRACK_USER_USAGE` ni `true` ga sozlang.
   - Token kuzatish bazasi ma'lumotlarini kiriting.
   - Frontend orqali embedding modelini tanlang.

2. **Foydalanuvchi Kuzatuvisiz (`TRACK_USER_USAGE=false`):**
   - `TRACK_USER_USAGE` ni `false` ga sozlang.
   - `EMBEDDING_MODEL` va `EMBEDDING_PROVIDER` ni `.env` da belgilang.
   - Agar so'zlanmasa, Sentence Transformer ishlatiladi.

---

## Deploy Variantlari

### **Lokal Deploy**

#### Docker-Compose orqali
Standart `docker-compose` konfiguratsiyasidan foydalaning.

1. **Qo'llab-quvvatlanadigan LLM Modellar:**
   Sukat bo'yicha faqat OpenAI va Diffbot yoqilgan. Gemini uchun qo'shimcha GCP sozlamalari kerak.
   ```bash
   VITE_LLM_MODELS_PROD="gemini_2.5_flash,openai_gpt_5_mini,diffbot,anthropic_claude_4.5_haiku"
   ```

2. **Input Manbalar:**
   Sukat bo'yicha: `local`, `YouTube`, `Wikipedia`, `AWS S3`, `web`.
   GCS qo'shish uchun:
   ```bash
   VITE_REACT_APP_SOURCES="local,youtube,wiki,s3,gcs,web"
   VITE_GOOGLE_CLIENT_ID="sizning-google-client-id"
   ```

#### Chat Rejimlari
`VITE_CHAT_MODES` orqali chat rejimlarini sozlang:
- Sukat bo'yicha barchasi yoqilgan: `vector`, `graph_vector`, `graph`, `fulltext`, `graph_vector_fulltext`, `entity_vector`, `global_vector`.
- Maxsus rejimlar:
   ```bash
   VITE_CHAT_MODES="vector,graph"
   ```

---

### **Backend va Frontend ni Alohida Ishga Tushirish**

#### **Frontend Sozlash**
1. `frontend/example.env` faylini `frontend` papkasiga `.env` nomi bilan nusxalangan.
2. Muhit o'zgaruvchilarini yangilang.
3. Ishga tushiring:
   ```bash
   cd frontend
   yarn
   yarn run dev
   ```

#### **Backend Sozlash**
1. `backend/example.env` faylini `backend` papkasiga `.env` nomi bilan nusxalangan.
2. Foydalanuvchi ma'lumotlarini kiriting:
   ```bash
   NEO4J_URI=<sizning-neo4j-uri>
   NEO4J_USERNAME=<sizning-foydalanuvchi-nomi>
   NEO4J_PASSWORD=<sizning-parol>
   NEO4J_DATABASE=<sizning-baza-nomi>
   ```
3. Ishga tushiring:
   ```bash
   cd backend
   python -m venv envName
   source envName/bin/activate
   pip install -r requirements.txt
   uvicorn score:app --reload
   ```

---

### **Cloud Deploy**

Ilovani **Google Cloud Platform** da deploy qiling:

#### **Frontend Deploy**
```bash
gcloud run deploy dev-frontend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

#### **Backend Deploy**
```bash
gcloud run deploy dev-backend \
  --set-env-vars "OPENAI_API_KEY=<sizning-openai-api-key>" \
  --set-env-vars "DIFFBOT_API_KEY=<sizning-diffbot-api-key>" \
  --set-env-vars "NEO4J_URI=<sizning-neo4j-uri>" \
  --set-env-vars "NEO4J_USERNAME=<sizning-foydalanuvchi-nomi>" \
  --set-env-vars "NEO4J_PASSWORD=<sizning-parol>" \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

---

## Lokal LLMlar uchun (Ollama)

1. Ollama docker obrazini yuklang:
   ```bash
   docker pull ollama/ollama
   ```

2. Ollama docker obrazini ishga tushiring:
   ```bash
   docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
   ```

3. Istalgan LLM modelini ishga tushiring, masalan, llama3:
   ```bash
   docker exec -it ollama ollama run llama3
   ```

4. Docker compose da muhit o'zgaruvchilarini sozlang:
   ```env
   LLM_MODEL_CONFIG_ollama_<model-nomi>
   # misol
   LLM_MODEL_CONFIG_ollama_llama3=${LLM_MODEL_CONFIG_ollama_llama3-llama3,http://host.docker.internal:11434}
   ```

5. Backend API URL ni sozlang:
   ```env
   VITE_BACKEND_API_URL=${VITE_BACKEND_API_URL-backendurl}
   ```

6. Ilovani brauzerda oching va graf yaratish uchun ollama modelini tanlang.
7. Graf yaratishdan zavqlaning!

---

## Foydalanish

1. Neo4j Aura Instance ga ulang (AURA DS yoki AURA DB). Backend muhiti orqali URI va parolni o'tkazish, login oynasini to'ldirish yoki Neo4j credentials faylini tashlash orqali.
2. Farqlash uchun turli ikonlar qo'shilgan. AURA DB uchun baza ikon, AURA DS uchun ilmiy molekula ikon.
3. Graf yaratish uchun nazorat qilinmagan manbalardan birini tanlang.
4. Graf yaratish uchun dropdown dan LLM ni o'zgartiring.
5. Ixtiyoriy: entity grafiksini ajratish sozlamalarida sxemani (tugun va bog'lanish belgilarini) belgilang.
6. Bir nechta faylni 'Generate Graph' uchun tanlang yoki 'New' holatidagi barcha fayllar graf yaratish uchun qayta ishlanadi.
7. Grid da 'View' orqali alohida fayllar uchun grafni ko'ring yoki bir yoki bir nechta faylni tanlab 'Preview Graph' ni bosing.
8. Chatbot ga qayta ishlangan/tugallangan manbalar bilan bog'liq savollar bering. Shuningdek, LLM tomonidan yaratilgan javoblaringiz haqida batafsil ma'lumot oling.

---

## [ENV][env-sheet] Jadvali

| Muhit O'zgaruvchisi | Majburiy/Ixtiyoriy | Sukat Qiymat | Tavsif |
|---------------------|-------------------|--------------|--------|
| **BACKEND ENV** | | | |
| OPENAI_API_KEY | Ixtiyoriy | | OpenAI LLM modeli uchun API kalit |
| DIFFBOT_API_KEY | Majburiy | | Diffbot NLP xizmati uchun API kalit |
| BUCKET_UPLOAD_FILE | Ixtiyoriy | | Yuklangan faylni GCS da saqlash uchun bucket nomi |
| BUCKET_FAILED_FILE | Ixtiyoriy | | Xato bo'lgan faylni GCS da saqlash uchun bucket nomi |
| NEO4J_USER_AGENT | Ixtiyoriy | llm-graph-builder | Neo4j baza faoliyatini kuzatish uchun user agent nomi |
| ENABLE_USER_AGENT | Ixtiyoriy | true | Neo4j user agent ni yoqish/o'chirish |
| DUPLICATE_TEXT_DISTANCE | Ixtiyoriy | 5 | Tugun juftlari orasidagi masofani topish uchun |
| DUPLICATE_SCORE_VALUE | Ixtiyoriy | 0.97 | Dublikat tugunlarni moslashtirish uchun ball |
| EFFECTIVE_SEARCH_RATIO | Ixtiyoriy | 1 | Samarali qidiruv hisob-kitoblari uchun nisbat |
| GRAPH_CLEANUP_MODEL | Ixtiyoriy | openai_gpt_5_mini | Post-protsessingda grafni tozalash uchun model |
| MAX_TOKEN_CHUNK_SIZE | Ixtiyoriy | 10000 | Fayl tarkibini qayta ishlash uchun maksimal token o'lchami |
| YOUTUBE_TRANSCRIPT_PROXY | Majburiy | | YouTube videolaridan transkript olish uchun proxy kalit |
| IS_EMBEDDING | Ixtiyoriy | true | Matn embedding ni yoqish uchun flag |
| KNN_MIN_SCORE | Ixtiyoriy | 0.8 | KNN algoritmi uchun minimal ball |
| GCP_LOG_METRICS_ENABLED | Ixtiyoriy | False | Google Cloud loglarini yoqish uchun flag |
| NEO4J_URI | Ixtiyoriy | neo4j://database:7687 | Neo4j baza URI |
| NEO4J_USERNAME | Ixtiyoriy | neo4j | Neo4j baza foydalanuvchi nomi |
| NEO4J_PASSWORD | Ixtiyoriy | password | Neo4j baza paroli |
| GCS_FILE_CACHE | Ixtiyoriy | False | Agar True bo'lsa, fayllar GCS da saqlanadi. Agar False bo'lsa, lokal saqlanadi |
| ENTITY_EMBEDDING | Ixtiyoriy | False | Agar True bo'lsa, har bir entity uchun embedding qo'shiladi |
| LLM_MODEL_CONFIG_ollama_<model_nomi> | Ixtiyoriy | | Lokal deploy uchun ollama sozlamasi: model_nomi,model_mahalliy_url |
| **FRONTEND ENV** | | | |
| VITE_BLOOM_URL | Majburiy | [Bloom URL][bloom-url] | Bloom vizualizatsiyasi uchun URL |
| VITE_REACT_APP_SOURCES | Majburiy | local,youtube,wiki,s3 | Input manbalari ro'yxati |
| VITE_CHAT_MODES | Majburiy | vector,graph+vector,graph,hybrid | S&J uchun chat rejimlari |
| VITE_ENV | Majburiy | DEV yoki PROD | Ilova uchun muhit o'zgaruvchisi |
| VITE_LLM_MODELS | Ixtiyoriy | openai_gpt_5_mini,gemini_2.5_flash,anthropic_claude_4.5_haiku | Ilova uchun qo'llab-quvvatlanadigan modellar |
| VITE_BACKEND_API_URL | Ixtiyoriy | [localhost][backend-url] | Backend API uchun URL |
| VITE_TIME_PER_PAGE | Ixtiyoriy | 50 | Qayta ishlash uchun har bir sahifa vaqti |
| VITE_CHUNK_SIZE | Ixtiyoriy | 5242880 | Yuklash uchun faylning har bir chunk o'lchami |
| VITE_GOOGLE_CLIENT_ID | Ixtiyoriy | | Google autentifikatsiyasi uchun client ID |
| VITE_LLM_MODELS_PROD | Ixtiyoriy | openai_gpt_5_mini,gemini_2.5_flash,anthropic_claude_4.5_haiku | Muhitga asoslanib modellar farqlash (PROD yoki DEV) |
| VITE_AUTH0_CLIENT_ID | Autentifikatsiyani yoqasangiz majburiy, aks holda ixtiyoriy | | Autentifikatsiya uchun Okta OAuth Client ID |
| VITE_AUTH0_DOMAIN | Autentifikatsiyani yoqasangiz majburiy, aks holda ixtiyoriy | | Autentifikatsiya uchun Okta OAuth Client Domain |
| VITE_SKIP_AUTH | Ixtiyoriy | true | Autentifikatsiyani o'tkazib yuborish uchun flag |
| VITE_CHUNK_OVERLAP | Ixtiyoriy | 20 | Chunk overlap ni sozlash uchun o'zgaruvchi |
| VITE_TOKENS_PER_CHUNK | Ixtiyoriy | 100 | Har bir chunk uchun tokenlar sonini sozlash uchun o'zgaruvchi |
| VITE_CHUNK_TO_COMBINE | Ixtiyoriy | 1 | Parallel qayta ishlash uchun birlashtiriladigan chunklar soni |

### Misol Muhit Fayllari

Qo'shimcha o'zgaruvchilar va sozlamalar uchun misol muhit fayllariga qarang:

- [Backend example.env](https://github.com/neo4j-labs/llm-graph-builder/blob/main/backend/example.env)
- [Frontend example.env](https://github.com/neo4j-labs/llm-graph-builder/blob/main/frontend/example.env)

---

## Cloud Build Deployment

Backend va frontend ni Google Cloud Run ga Cloud Build orqali deploy qilishingiz mumkin (avtomatik yoki qo'lda).

### **Avtomatik Deploy (Tavsiya etiladi)**

1. **Repouzitoriyangizni Google Cloud Build ga ulang:**
   - Google Cloud Console da Cloud Build > Triggers ga o'ting.
   - Yangi trigger yarating va repouzitoriyangizni tanlang.
   - Trigger ni kerakli branch ga (`main`, `staging`, `dev`) push qilganda ishlashga sozlang.
   - Cloud Build avtomatik ravishda repouzitoriyingiz ildizidagi `cloudbuild.yaml` faylidan foydalanadi.

2. **Almashtirishlar va Sirrlarni Sozlang:**
   - Trigger sozlamalarida kerakli almashtirishlarni (`_OPENAI_API_KEY`, `_DIFFBOT_API_KEY` va boshqalar) muhit o'zgaruvchilari sifatida qo'shing yoki maxfiy ma'lumotlar uchun Secret Manager dan foydalaning.

3. **Kodingizni Push Qiling:**
   - Sozlangan branch ga push qilganingizda, Cloud Build `cloudbuild.yaml` da belgilangan qadamlardan foydalanib, backend (va ixtiyoriy frontend) ni Cloud Run ga build va deploy qiladi.

### **Qo'lda Deploy**

1. **Google Cloud SDK ni sozlang va autentifikatsiya qiling:**
   ```bash
   gcloud auth login
   gcloud config set project <SIZNING_LOYIHANGIZ_ID>
   ```

2. **Cloud Build ni qo'lda ishga tushiring:**
   ```bash
   gcloud builds submit --config cloudbuild.yaml \
     --substitutions=_REGION=us-central1,_REPO=cloud-run-repo,_OPENAI_API_KEY=<sizning-openai-kalit>,_DIFFBOT_API_KEY=<sizning-diffbot-kalit>,_BUCKET_UPLOAD_FILE=<sizning-bucket>,_BUCKET_FAILED_FILE=<sizning-bucket>,_PROJECT_ID=<sizning-loyihangiz>,_GCS_FILE_CACHE=False,_TRACK_USER_USAGE=False,_TOKEN_TRACKER_DB_URI=...,_TOKEN_TRACKER_DB_USERNAME=...,_TOKEN_TRACKER_DB_PASSWORD=...,_TOKEN_TRACKER_DB_DATABASE=...,_DEFAULT_DIFFBOT_CHAT_MODEL=...,_YOUTUBE_TRANSCRIPT_PROXY=...,_EMBEDDING_MODEL=...,_EMBEDDING_PROVIDER=...,_BEDROCK_EMBEDDING_MODEL_KEY=...,_LLM_MODEL_CONFIG_OPENAI_GPT_5_2=...,_LLM_MODEL_CONFIG_OPENAI_GPT_5_MINI=...,_LLM_MODEL_CONFIG_GEMINI_2_5_FLASH=...,_LLM_MODEL_CONFIG_GEMINI_2_5_PRO=...,_LLM_MODEL_CONFIG_DIFFBOT=...,_LLM_MODEL_CONFIG_GROQ_LLAMA3_1_8B=...,_LLM_MODEL_CONFIG_ANTHROPIC_CLAUDE_4_5_SONNET=...,_LLM_MODEL_CONFIG_ANTHROPIC_CLAUDE_4_5_HAIKU=...,_LLM_MODEL_CONFIG_LLAMA4_MAVERICK=...,_LLM_MODEL_CONFIG_FIREWORKS_QWEN3_30B=...,_LLM_MODEL_CONFIG_FIREWORKS_GPT_OSS=...,_LLM_MODEL_CONFIG_FIREWORKS_DEEPSEEK_V3=...,_LLM_MODEL_CONFIG_BEDROCK_NOVA_MICRO_V1=...,_LLM_MODEL_CONFIG_BEDROCK_NOVA_LITE_V1=...,_LLM_MODEL_CONFIG_BEDROCK_NOVA_PRO_V1=...,_LLM_MODEL_CONFIG_OLLAMA_LLAMA3=...
   ```
   - Burchak qavslardagi qiymatlarni haqiqiy konfiguratsiya va sirlaringiz bilan almashtiring.
   - Deploy uchun kerakli almashtirishlarni qo'shishingiz yoki olib tashlashingiz mumkin.

3. **Build ni Kuzating:**
   - Build va deploy jarayoni Cloud Build console da ko'rinadi.

4. **Deploy Qilingan Xizmatingizga Kirishing:**
   - Deploy dan keyin, backend ingiz Cloud Console da ko'rsatilgan Cloud Run xizmati URL da mavjud bo'ladi.

---

**Eslatma:**
- `cloudbuild.yaml` fayli branch nomiga ko'ra bir nechta muhitlarni (`main`, `staging`, `dev`) qo'llab-quvvatlaydi.
- Frontend build va deploy qadamlari sukut bo'yicha izoh qilingan. Agar frontend ni deploy qilmoqchi bo'lsangiz, `cloudbuild.yaml` da ularni izohdan chiqaring.

Batafsil ma'lumot uchun [`cloudbuild.yaml`](cloudbuild.yaml) dagi izohlarga qarang.

---

## Havolalar

[LLM Knowledge Graph Builder Ilovasi][app-link]

[Neo4j Workspace][neo4j-workspace]

## Havola

[Ilova demosini][demo-video] ko'ring

## Aloqa
Har qanday savollar yoki yordam uchun [GitHub Issues][github-issues] da so'rang.

[backend-url]: http://localhost:8000
[env-sheet]: https://docs.google.com/spreadsheets/d/1DBg3m3hz0PCZNqIjyYJsYALzdWwMlLah706Xvxt62Tk/edit?gid=184339012#gid=184339012
[env-vars]: https://docs.google.com/spreadsheets/d/1DBg3m3hz0PCZNqIjyYJsYALzdWwMlLah706Xvxt62Tk/edit?gid=0#gid=0
[app-link]: https://llm-graph-builder.neo4jlabs.com/
[neo4j-workspace]: https://workspace-preview.neo4j.io/workspace/query
[demo-video]: https://www.youtube.com/watch?v=LlNy5VmV290
[github-issues]: https://github.com/neo4j-labs/llm-graph-builder/issues
[bloom-url]: https://workspace-preview.neo4j.io/workspace/explore?connectURL={CONNECT_URL}&search=Show+me+a+graph&featureGenAISuggestions=true&featureGenAISuggestionsInternal=true
[langchain-endpoint]: https://api.smith.langchain.com

## Baxtli Graf Yaratish!
