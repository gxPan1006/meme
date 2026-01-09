import json
import os
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer


DEFAULT_MODEL = "BAAI/bge-small-zh-v1.5"


class MemeRAG:
    def __init__(
        self,
        analysis_path: str | None = None,
        model_name: str = DEFAULT_MODEL,
    ) -> None:
        self.model = SentenceTransformer(model_name)
        self.memes: list[dict[str, Any]] = []
        self.embeddings: np.ndarray | None = None
        self.texts: list[str] = []

        if analysis_path:
            self.load_memes(analysis_path)

    def load_memes(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.memes = []
        self.texts = []

        for item in data:
            analysis = item.get("analysis", {})
            if isinstance(analysis, dict) and "error" not in analysis:
                text = self._analysis_to_text(analysis)
                if text:
                    self.memes.append(item)
                    self.texts.append(text)

    def _analysis_to_text(self, analysis: dict[str, Any]) -> str:
        parts = []

        emotion = analysis.get("所代表情绪", "")
        if isinstance(emotion, str):
            parts.append(emotion)
        elif isinstance(emotion, list):
            parts.extend(emotion)

        scene = analysis.get("使用场景", "")
        if isinstance(scene, str):
            parts.append(scene)
        elif isinstance(scene, list):
            parts.extend(scene)

        design = analysis.get("设计灵感", "")
        if isinstance(design, str):
            parts.append(design)
        elif isinstance(design, list):
            parts.extend(design)

        raw = analysis.get("raw", "")
        if isinstance(raw, str) and raw.strip():
            parts.append(raw)

        return " ".join(str(p) for p in parts if p)

    def build_index(self) -> None:
        if not self.texts:
            raise ValueError("No memes loaded. Call load_memes() first.")
        self.embeddings = self.model.encode(self.texts, convert_to_numpy=True)

    def save_index(self, path: str) -> None:
        if self.embeddings is None:
            raise ValueError("No index built. Call build_index() first.")

        memes_path = Path(path).with_suffix(".json")
        with open(memes_path, "w", encoding="utf-8") as f:
            json.dump(self.memes, f, ensure_ascii=False, indent=2)

        np.savez_compressed(path, embeddings=self.embeddings, texts=self.texts)

    def load_index(self, path: str) -> None:
        memes_path = Path(path).with_suffix(".json")
        with open(memes_path, "r", encoding="utf-8") as f:
            self.memes = json.load(f)

        data = np.load(path, allow_pickle=True)
        self.embeddings = data["embeddings"]
        self.texts = list(data["texts"])

    def search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        if self.embeddings is None:
            raise ValueError("No index available. Build or load index first.")

        query_embedding = self.model.encode([query], convert_to_numpy=True)
        similarities = np.dot(self.embeddings, query_embedding.T).flatten()
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            meme = self.memes[idx].copy()
            meme["score"] = float(similarities[idx])
            results.append(meme)

        return results

    def find_similar_from_analysis(
        self,
        analysis: dict[str, Any],
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        query_text = self._analysis_to_text(analysis)
        print(f"[RAG] Analysis keys: {list(analysis.keys())}")
        print(f"[RAG] Query text: {query_text[:100] if query_text else '(empty)'}")
        if isinstance(analysis, dict) and "raw" in analysis:
            raw = analysis.get("raw")
            print(f"[RAG] Raw type: {type(raw).__name__}")
            if isinstance(raw, str):
                print(f"[RAG] Raw preview: {raw[:200]}")
        if not query_text:
            return []
        return self.search(query_text, top_k)


def build_index(analysis_path: str, output_path: str) -> None:
    rag = MemeRAG(analysis_path)
    rag.build_index()
    rag.save_index(output_path)
    print(f"Built index with {len(rag.memes)} memes -> {output_path}")


def search_memes(
    query: str,
    index_path: str,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    rag = MemeRAG()
    rag.load_index(index_path)
    return rag.search(query, top_k)


if __name__ == "__main__":
    import sys

    def print_usage():
        print("Usage:")
        print("  python -m meme.rag index <analysis.json> [output.npz]")
        print("  python -m meme.rag search <query> <index.npz> [top_k]")
        sys.exit(1)

    if len(sys.argv) < 2:
        print_usage()

    cmd = sys.argv[1]

    if cmd == "index":
        if len(sys.argv) < 3:
            print_usage()
        analysis_path = sys.argv[2]
        output_path = sys.argv[3] if len(sys.argv) > 3 else "meme_index.npz"
        build_index(analysis_path, output_path)

    elif cmd == "search":
        if len(sys.argv) < 4:
            print_usage()
        query = sys.argv[2]
        index_path = sys.argv[3]
        top_k = int(sys.argv[4]) if len(sys.argv) > 4 else 3

        results = search_memes(query, index_path, top_k)
        for i, meme in enumerate(results, 1):
            print(f"\n[{i}] {meme['name']} (score: {meme['score']:.4f})")
            print(f"    URL: {meme['url']}")
            emotion = meme.get("analysis", {}).get("所代表情绪", "")
            if isinstance(emotion, str) and len(emotion) > 100:
                emotion = emotion[:100] + "..."
            print(f"    情绪: {emotion}")

    else:
        print_usage()
