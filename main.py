import json
import os
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from neo4j import GraphDatabase
from openai import OpenAI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

load_dotenv()

app = FastAPI(title="Uzbek Labor Code GraphRAG")

# --- Инициализация ---
neo4j_driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")),
)

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_API_BASE")
)

embed_model = SentenceTransformer(os.getenv("EMBEDDING_MODEL"))


# --- Модели данных ---
class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]
    modda_numbers: List[str]


# --- Функции ---
def get_embedding(text: str) -> List[float]:
    return embed_model.encode(text, convert_to_numpy=True).tolist()


def search_graph(query: str, top_k: int = 5):
    vector = get_embedding(query)
    with neo4j_driver.session() as session:
        result = session.run(
            """
            CALL db.index.vector.queryNodes('chunk_embedding', $top_k, $vector)
            YIELD node, score
            MATCH (node)-[:BELONGS_TO|CONTAINS_CHUNK*0..1]-(meta)
            RETURN
                node.text AS text,
                node.modda_number AS modda_number,
                node.modda_title AS modda_title,
                node.code AS code,
                score
            ORDER BY score DESC
            LIMIT $top_k
        """,
            vector=vector,
            top_k=top_k,
        )
        return [dict(r) for r in result]


def generate_answer(query: str, context: List[dict]) -> str:
    context_text = "\n\n".join(
        [f"Модда {c['modda_number']} ({c['code']}): {c['text']}" for c in context]
    )

    prompt = f"""Сиз Ўзбекистон Меҳнат Кодекси бўйича ёрдамчисиз.
Фақат берилган контекст асосида жавоб беринг.

Контекст:
{context_text}

Савол: {query}

Жавоб (ўзбек тилида):"""

    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL"),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
        temperature=0.3,
    )
    return response.choices[0].message.content


# --- Эндпоинты ---
@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    try:
        context = search_graph(request.query)
        if not context:
            return QueryResponse(
                answer="Маълумот топилмади.", sources=[], modda_numbers=[]
            )

        answer = generate_answer(request.query, context)
        modda_numbers = [c["modda_number"] for c in context if c.get("modda_number")]

        return QueryResponse(
            answer=answer, sources=context, modda_numbers=modda_numbers
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload")
async def upload_data(file_path: str = "/app/data/mehnat_kodeksi_processed.json"):
    """Загрузка данных из JSON в Neo4j"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        with neo4j_driver.session() as session:
            # Создаем векторный индекс
            session.run("""
                CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS
                FOR (c:Chunk) ON (c.embedding)
                OPTIONS {
                    indexConfig: {
                        `vector.dimensions`: 384,
                        `vector.similarity_function`: 'cosine'
                    }
                }
            """)

            # Загружаем чанки
            for chunk in data.get("chunks", []):
                embedding = get_embedding(chunk["text"])
                session.run(
                    """
                    MERGE (c:Chunk {id: $id})
                    SET c.text = $text,
                        c.embedding = $embedding,
                        c.modda_number = $modda_number,
                        c.code = $code,
                        c.bob_title = $bob_title
                """,
                    id=chunk["id"],
                    text=chunk["text"],
                    embedding=embedding,
                    modda_number=chunk["metadata"].get("modda_number"),
                    code=chunk["metadata"].get("code"),
                    bob_title=chunk["metadata"].get("bob_title"),
                )

        return {"status": "success", "chunks_loaded": len(data.get("chunks", []))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
