"""Retrieval quality evaluation against the seeded Labor Code knowledge base.

Dataset: ``data/rag_eval_labor_code.jsonl`` — lines of
``{"question": str, "article": str}`` where ``article`` is the expected
Labor Code article (modda) number. Metrics: hit@1, hit@k, MRR computed over
the ``article`` meta of retrieved chunks.

Usage (DB must be seeded via app.scripts.seed_labor_code):
    python -m app.scripts.rag_eval [path/to/dataset.jsonl] [--top-k 5]
"""

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import async_session_factory
from app.services.rag.pipeline import retrieve
from app.services.rag.retrieval import LEGISLATION_TENANT_ID

DEFAULT_DATASET = Path(__file__).resolve().parents[3] / ".." / "data" / "rag_eval_labor_code.jsonl"


@dataclass
class EvalReport:
    total: int
    hit_at_1: float
    hit_at_k: float
    mrr: float
    top_k: int
    misses: list[str]


def load_dataset(path: Path) -> list[dict]:
    samples = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            samples.append(json.loads(line))
    return samples


async def evaluate(db: AsyncSession, samples: list[dict], top_k: int = 5) -> EvalReport:
    """Run retrieval for every sample; deterministic (reranker off)."""
    hits1 = hitsk = 0
    rr_sum = 0.0
    misses: list[str] = []
    for sample in samples:
        result = await retrieve(
            db, LEGISLATION_TENANT_ID, sample["question"], top_k=top_k, use_reranker=False
        )
        articles = [str(s.get("article", "")) for s in result.sources]
        expected = str(sample["article"])
        if expected in articles:
            rank = articles.index(expected) + 1
            hitsk += 1
            rr_sum += 1.0 / rank
            if rank == 1:
                hits1 += 1
        else:
            misses.append(f"{sample['question']!r} → ждали ст. {expected}, получили {articles}")
    total = len(samples)
    return EvalReport(
        total=total,
        hit_at_1=hits1 / total if total else 0.0,
        hit_at_k=hitsk / total if total else 0.0,
        mrr=rr_sum / total if total else 0.0,
        top_k=top_k,
        misses=misses,
    )


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", nargs="?", default=str(DEFAULT_DATASET))
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    samples = load_dataset(Path(args.dataset))
    async with async_session_factory() as db:
        report = await evaluate(db, samples, top_k=args.top_k)

    print(f"\nRAG retrieval evaluation — {report.total} questions, top_k={report.top_k}")
    print("-" * 52)
    print(f"  hit@1        : {report.hit_at_1:6.1%}")
    print(f"  hit@{report.top_k}        : {report.hit_at_k:6.1%}")
    print(f"  MRR          : {report.mrr:6.3f}")
    if report.misses:
        print(f"\nПромахи ({len(report.misses)}):")
        for miss in report.misses[:15]:
            print(f"  - {miss}")
    if report.hit_at_k < 0.5:
        print("\n⚠ hit@k ниже 50% — проверьте, что база засеяна (seed_labor_code) и эмбеддинги есть.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
