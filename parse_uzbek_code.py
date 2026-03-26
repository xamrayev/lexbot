#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер для кодексов Узбекистана (латиница)
Сохраняет иерархию: Kodeks → Qism → Boʻlim → Bob → Modda
"""

import json
import re
from datetime import datetime


def normalize_text(text: str) -> str:
    """
    Normalize text by fixing common encoding artifacts in Uzbek Latin script.
    Handles ISO-8859 to UTF-8 conversion issues.
    """
    replacements = {
        "?": "ʻ",  # apostrophe-like character
        "Ò": "Oʻ",  # O with apostrophe
        "ò": "oʻ",  # o with apostrophe
        "Ñ": "Gʻ",  # Gh with apostrophe
        "ñ": "gʻ",  # gh with apostrophe
        "Ä": "Aʼ",  # A with apostrophe (Cyrillic influence)
        "ä": "aʼ",  # a with apostrophe
        "Ï": "Iʼ",  # I with apostrophe
        "ï": "iʼ",  # i with apostrophe
        "Ö": "Oʼ",  # O with apostrophe (different encoding)
        "ö": "oʼ",  # o with apostrophe
        "¤": "modda",  # section marker artifact
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


class UzbekCodeParser:
    """Парсер для узбекских правовых документов"""

    def __init__(self, code_name: str, code_short: str):
        self.code_name = code_name
        self.code_short = code_short
        self.articles = []
        self.context = {
            "qism": None,
            "bolim_num": None,
            "bolim_title": None,
            "bob_num": None,
            "bob_title": None,
        }

    def parse(self, text: str) -> list[dict]:
        """Парсит сырой текст в структурированные статьи"""
        # Normalize the text first
        text = normalize_text(text)
        lines = text.split("\n")
        current_article = None
        current_text_lines = []

        for line in lines:
            line_stripped = line.strip()

            # Пропускаем пустые строки и заголовок кодекса
            if not line_stripped or "KODEKSI" in line_stripped.upper():
                continue

            # 1. UMUMIY QISM (Часть)
            if re.match(r"^UMUMIY QISM\s*$", line_stripped, re.IGNORECASE):
                self.context["qism"] = "UMUMIY QISM"
                continue

            # 2. I BOʻLIM. UMUMIY QOIDALAR (Раздел) - handle both BOʻLIM and BOLIM
            bolim_match = re.match(
                r"^([IVXLC]+)\s*BO[ʻʼ]?LIM[.\s]+(.+)$", line_stripped
            )
            if bolim_match:
                self.context["bolim_num"] = bolim_match.group(1)
                self.context["bolim_title"] = bolim_match.group(2).strip()
                continue

            # 3. 1-bob. Asosiy qoidalar (Глава)
            bob_match = re.match(r"^(\d+)-bob[.\s]+(.+)$", line_stripped, re.IGNORECASE)
            if bob_match:
                self.context["bob_num"] = bob_match.group(1)
                self.context["bob_title"] = bob_match.group(2).strip()
                continue

            # 4. 1-modda. Title (Статья) — НОВАЯ СТАТЬЯ
            modda_match = re.match(
                r"^(\d+[a-zA-Zʻʼ]?)\s*-modda[.\s]+(.+)$", line_stripped, re.IGNORECASE
            )
            if modda_match:
                # Сохраняем предыдущую статью
                if current_article:
                    current_article["text"] = " ".join(current_text_lines).strip()
                    self.articles.append(current_article)

                # Создаём новую статью
                current_article = {
                    "id": f"{self.code_short}_{modda_match.group(1)}",
                    "code": self.code_short,
                    "modda_number": modda_match.group(1),
                    "modda_title": modda_match.group(2).strip(),
                    "qism": self.context["qism"],
                    "bolim_num": self.context["bolim_num"],
                    "bolim_title": self.context["bolim_title"],
                    "bob_num": self.context["bob_num"],
                    "bob_title": self.context["bob_title"],
                    "text": "",
                    "bands": [],
                    "references": [],
                    "metadata": {
                        "full_code_name": self.code_name,
                        "hierarchy": f"{self.context['bolim_title'] or ''} → {self.context['bob_title'] or ''}",
                        "language": "uz",
                    },
                }
                current_text_lines = []
                continue

            # 5. Текст статьи (собираем все строки до следующей статьи)
            if current_article and line_stripped:
                # Проверяем, не пункт ли это (список с точкой с запятой)
                if line_stripped.endswith(";") or re.match(r"^[a-z]", line_stripped):
                    current_article["bands"].append(line_stripped)
                else:
                    current_text_lines.append(line_stripped)

        # Сохраняем последнюю статью
        if current_article:
            current_article["text"] = " ".join(current_text_lines).strip()
            self.articles.append(current_article)

        return self.articles

    def extract_references(self) -> list[dict]:
        """Извлекает ссылки на другие статьи из текста"""
        # Паттерны для ссылок в узбекском тексте
        ref_patterns = [
            r"(\d+[a-zA-Zʻʼ]?)\s*-modda(?:ga|da|ni|ning|lariga|si)?",
            r"ushbu\s+Kodeksning\s+(\d+[а-яА-Яʻʼ]?)\s*-moddasi",
            r"Mazkur\s+Kodeksning\s+(\d+[а-яА-Яʻʼ]?)\s*-moddasi",
            r"(\d+[а-яА-Яʻʼ]?)\s*-moddada\s+nazarda\s+tutilgan",
        ]

        for article in self.articles:
            full_text = article["text"] + " " + " ".join(article["bands"])
            found_refs = set()

            for pattern in ref_patterns:
                matches = re.findall(pattern, full_text, re.IGNORECASE)
                found_refs.update(matches)

            # Удаляем ссылку на саму себя
            found_refs.discard(article["modda_number"])

            article["references"] = [
                {
                    "target_modda": ref,
                    "target_id": f"{self.code_short}_{ref}",
                    "relation_type": "REFERENCES",
                }
                for ref in sorted(
                    found_refs, key=lambda x: int(re.search(r"\d+", x).group())
                )
            ]

        return self.articles

    def prepare_chunks(self, strategy: str = "by_article") -> list[dict]:
        """Готовит чанки для векторного поиска"""
        chunks = []

        for article in self.articles:
            # Собираем полный текст для поиска
            searchable_text = self._build_searchable_text(article)

            if strategy == "by_article":
                chunks.append(
                    {
                        "id": article["id"],
                        "type": "article",
                        "text": searchable_text,
                        "metadata": {
                            "code": article["code"],
                            "modda_number": article["modda_number"],
                            "modda_title": article["modda_title"],
                            "bob_num": article["bob_num"],
                            "bob_title": article["bob_title"],
                            "bolim_num": article["bolim_num"],
                            "hierarchy": article["metadata"]["hierarchy"],
                            "references": [
                                r["target_id"] for r in article["references"]
                            ],
                            "language": "uz",
                        },
                    }
                )

            elif strategy == "hybrid":
                # Основной чанк + отдельные для пунктов
                chunks.append(
                    {
                        "id": article["id"],
                        "type": "article_main",
                        "text": searchable_text,
                        "metadata": {**article["metadata"], "is_main": True},
                    }
                )
                for i, band in enumerate(article["bands"]):
                    chunks.append(
                        {
                            "id": f"{article['id']}_band_{i + 1}",
                            "type": "band",
                            "text": f"{article['modda_title']}: {band}",
                            "metadata": {
                                "parent_article_id": article["id"],
                                "modda_number": article["modda_number"],
                                "band_index": i + 1,
                                "references": [
                                    r["target_id"] for r in article["references"]
                                ],
                            },
                        }
                    )

        return chunks

    def _build_searchable_text(self, article: dict) -> str:
        """Собирает текст статьи для векторного поиска"""
        parts = [
            f"{article['code']} {article['modda_number']}-modda",
            article["modda_title"],
            article["text"],
        ]
        if article["bands"]:
            parts.extend(article["bands"])
        return " | ".join(parts)

    def export(self, output_path: str, strategy: str = "by_article"):
        """Экспорт в JSON для llm-graph-builder"""
        chunks = self.prepare_chunks(strategy)

        output = {
            "metadata": {
                "code_name": self.code_name,
                "code_short": self.code_short,
                "total_articles": len(self.articles),
                "total_chunks": len(chunks),
                "chunk_strategy": strategy,
                "language": "uz",
                "processed_at": datetime.now().isoformat(),
            },
            "articles": self.articles,
            "chunks": chunks,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"✅ Экспорт завершён: {output_path}")
        print(f"   📊 Статей: {len(self.articles)}")
        print(f"   📊 Чанков: {len(chunks)}")
        total_refs = sum(len(a["references"]) for a in self.articles)
        print(f"   🔗 Ссылок между статьями: {total_refs}")

        return output


# ============================================
# ЗАПУСК
# ============================================
if __name__ == "__main__":
    # 1. Читаем исходный файл (пробуем разные кодировки)
    raw_text = None
    for encoding in ["utf-8", "iso-8859-1", "cp1251", "koi8-r"]:
        try:
            with open("mehnat_kodeksi_uz.txt", "r", encoding=encoding) as f:
                raw_text = f.read()
            print(f"✅ Файл прочитан с кодировкой: {encoding}")
            break
        except UnicodeDecodeError:
            continue

    if raw_text is None:
        raise ValueError("Не удалось прочитать файл ни с одной из известных кодировок")

    # 2. Инициализируем парсер
    parser = UzbekCodeParser(
        code_name="OʻZBEKISTON RESPUBLIKASINING MEHNAT KODEKSI", code_short="MK_RUz"
    )

    # 3. Парсим
    parser.parse(raw_text)

    # 4. Извлекаем ссылки
    parser.extract_references()

    # 5. Экспортируем (стратегия: одна статья = один чанк)
    parser.export("mehnat_kodeksi_processed.json", strategy="by_article")
