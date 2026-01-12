import os
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from meme.analyze_memes import fetch_as_data_url
from meme.client import DoubaoClient
from meme.config import APIConfig, DEFAULT_INSTRUCT_PROMPT
from meme.exceptions import ConfigurationError


app = FastAPI(title="Meme Analyzer API", version="0.1.0")

_rag_instance = None


def log(msg: str) -> None:
    print(f"[meme] {msg}")


def get_rag():
    global _rag_instance
    if _rag_instance is None:
        index_path = os.getenv("MEME_INDEX_PATH", "meme_index.npz")
        if os.path.exists(index_path):
            from meme.rag import MemeRAG
            log(f"Loading RAG index from {index_path}")
            _rag_instance = MemeRAG()
            _rag_instance.load_index(index_path)
            log(f"RAG index loaded: {len(_rag_instance.memes)} memes")
    return _rag_instance


def normalize_size(size: str, min_pixels: int = 3686400, fallback: str = "1920x1920") -> str:
    if "x" not in size:
        return size

    try:
        width_str, height_str = size.lower().split("x", 1)
        width = int(width_str)
        height = int(height_str)
    except Exception:
        log(f"Invalid size format '{size}', fallback to {fallback}")
        return fallback

    if width <= 0 or height <= 0:
        log(f"Invalid size '{size}', fallback to {fallback}")
        return fallback

    if width * height < min_pixels:
        log(f"Size '{size}' too small, fallback to {fallback}")
        return fallback

    return size


class AnalyzeRequest(BaseModel):
    url: str
    image_mode: str = "remote"
    download_timeout: float = 15.0
    api_key: str | None = None


class MatchRequest(BaseModel):
    url: str
    image_mode: str = "remote"
    download_timeout: float = 15.0
    top_k: int = 3
    api_key: str | None = None


class SearchRequest(BaseModel):
    query: str
    top_k: int = 3


@app.post("/analyze")
async def analyze(req: AnalyzeRequest) -> dict[str, Any]:
    log(f"Analyze: {req.url[:50]}...")
    try:
        config = APIConfig.from_env(api_key_override=req.api_key)
        client = DoubaoClient(config)

        image_url = req.url
        if req.image_mode == "data":
            log("Fetching image as data URL")
            image_url = fetch_as_data_url(req.url, req.download_timeout)

        log("Calling Doubao API")
        response = client.analyze_image(image_url)
        analysis = client.extract_analysis(response)
        if isinstance(analysis, dict) and "raw" in analysis:
            log(f"Analysis raw: {str(analysis.get('raw'))[:200]}")
        if isinstance(analysis, dict) and "raw" in analysis:
            log(f"Analysis raw: {str(analysis.get('raw'))[:200]}")
        log("Analysis done")

        return {"analysis": analysis}

    except ConfigurationError as e:
        log(f"Config error: {e}")
        raise HTTPException(status_code=500, detail={"error": "configuration_error", "message": str(e)})
    except Exception as e:
        log(f"Error: {e}")
        raise HTTPException(status_code=500, detail={"error": "analysis_failed", "message": str(e)})


@app.post("/match")
async def match(req: MatchRequest) -> dict[str, Any]:
    log(f"Match: {req.url[:50]}...")
    rag = get_rag()
    if rag is None:
        raise HTTPException(
            status_code=500,
            detail={"error": "index_not_loaded", "message": "Set MEME_INDEX_PATH env var"},
        )

    try:
        config = APIConfig.from_env(api_key_override=req.api_key)
        client = DoubaoClient(config)

        image_url = req.url
        if req.image_mode == "data":
            log("Fetching image as data URL")
            image_url = fetch_as_data_url(req.url, req.download_timeout)

        log("Calling Doubao API")
        response = client.analyze_image(image_url)
        analysis = client.extract_analysis(response)
        if isinstance(analysis, dict) and "raw" in analysis:
            log(f"Analysis raw: {str(analysis.get('raw'))[:200]}")

        log("Searching similar memes")
        matches = rag.find_similar_from_analysis(analysis, req.top_k)
        log(f"Found {len(matches)} matches")

        return {"analysis": analysis, "matches": matches}

    except ConfigurationError as e:
        log(f"Config error: {e}")
        raise HTTPException(status_code=500, detail={"error": "configuration_error", "message": str(e)})
    except Exception as e:
        log(f"Error: {e}")
        raise HTTPException(status_code=500, detail={"error": "match_failed", "message": str(e)})


@app.post("/search")
async def search(req: SearchRequest) -> dict[str, Any]:
    log(f"Search: {req.query}")
    rag = get_rag()
    if rag is None:
        raise HTTPException(
            status_code=500,
            detail={"error": "index_not_loaded", "message": "Set MEME_INDEX_PATH env var"},
        )

    results = rag.search(req.query, req.top_k)
    log(f"Found {len(results)} results")
    return {"results": results}


class GenerateRequest(BaseModel):
    url: str
    image_mode: str = "remote"
    download_timeout: float = 15.0
    text: str | None = None
    size: str = "1920x1920"
    need_ref: bool = True
    api_key: str | None = None


@app.post("/generate")
async def generate(req: GenerateRequest) -> dict[str, Any]:
    log(f"Generate: {req.url[:50]}...")
    rag = get_rag()
    if rag is None:
        raise HTTPException(
            status_code=500,
            detail={"error": "index_not_loaded", "message": "Set MEME_INDEX_PATH env var"},
        )

    try:
        config = APIConfig.from_env(api_key_override=req.api_key)
        client = DoubaoClient(config)

        image_url = req.url
        if req.image_mode == "data":
            log("Fetching image as data URL")
            image_url = fetch_as_data_url(req.url, req.download_timeout)

        log("Step 1: Analyzing input image")
        prompt_override = DEFAULT_INSTRUCT_PROMPT if req.text else None
        response = client.analyze_image(
            image_url,
            prompt_override=prompt_override,
            extra_text=req.text,
        )
        input_analysis = client.extract_analysis(response)
        if isinstance(input_analysis, dict) and "raw" in input_analysis:
            log(f"Analysis raw: {str(input_analysis.get('raw'))[:200]}")

        log("Step 2: Finding similar meme via RAG")
        matches = rag.find_similar_from_analysis(input_analysis, top_k=1)
        if not matches:
            log("Error: No similar memes found")
            raise HTTPException(status_code=500, detail={"error": "no_matches", "message": "No similar memes found"})

        best_match = matches[0]
        design_inspiration = best_match.get("analysis", {}).get("设计灵感", "")
        log(f"Best match: {best_match['name']} (score: {best_match['score']:.4f})")

        if not design_inspiration:
            log("Error: Best match has no design inspiration")
            raise HTTPException(status_code=500, detail={"error": "no_inspiration", "message": "Best match has no design inspiration"})

        log(f"Step 3: Generating new meme with prompt: {design_inspiration[:50]}...")
        safe_size = normalize_size(req.size)
        if req.need_ref:
            prompt = (
                f"可参考的设计灵感：{design_inspiration}\n\n"
                "结合参考的表情包(图一)和设计灵感，基于图二去设计一个新的表情包"
            )
            images = [best_match["url"], image_url]
            gen_response = client.generate_image(
                prompt=prompt,
                images=images,
                size=safe_size,
            )
        else:
            gen_response = client.generate_image(
                prompt=design_inspiration,
                image_url=image_url,
                size=safe_size,
            )

        if "error" in gen_response:
            error_msg = gen_response["error"].get("message", str(gen_response["error"]))
            log(f"Error: Image generation failed: {error_msg}")
            raise HTTPException(status_code=500, detail={"error": "generation_failed", "message": error_msg})

        generated_url = None
        if "data" in gen_response and gen_response["data"]:
            generated_url = gen_response["data"][0].get("url")

        log(f"Generation done: {generated_url}")

        return {
            "input_analysis": input_analysis,
            "best_match": {
                "name": best_match["name"],
                "url": best_match["url"],
                "score": best_match["score"],
                "design_inspiration": design_inspiration,
            },
            "generated_image_url": generated_url,
            "raw_response": gen_response,
        }

    except ConfigurationError as e:
        log(f"Config error: {e}")
        raise HTTPException(status_code=500, detail={"error": "configuration_error", "message": str(e)})
    except HTTPException:
        raise
    except Exception as e:
        log(f"Error: {e}")
        raise HTTPException(status_code=500, detail={"error": "generate_failed", "message": str(e)})


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("ANALYSIS_HOST", "127.0.0.1")
    port = int(os.getenv("ANALYSIS_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
