import logging
import os
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from github_integ import CustomGithubClient
from llmman import generate_report
from models import StdRequest
from nlpops import build_report_prompt

logger = logging.getLogger("reposense.api")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

RATE_LIMIT = max(1, int(os.getenv("RATE_LIMIT_REQUESTS", "10")))
RATE_WINDOW_SECONDS = max(1, int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")))
_request_times: dict[str, deque[float]] = defaultdict(deque)
_rate_lock = Lock()


class AnalyzeRequest(BaseModel):
    repo_url: str = Field(min_length=1, max_length=500)


app = FastAPI(title="Repo Sense API", version="1.0.0")

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def _check_rate_limit(client_key: str) -> None:
    now = time.monotonic()
    with _rate_lock:
        timestamps = _request_times[client_key]
        while timestamps and now - timestamps[0] >= RATE_WINDOW_SECONDS:
            timestamps.popleft()
        if len(timestamps) >= RATE_LIMIT:
            raise HTTPException(status_code=429, detail="rate limit exceeded; try again shortly")
        timestamps.append(now)


def _run_analysis(repo_url: str) -> dict:
    request = StdRequest(repo_url=repo_url)
    github = CustomGithubClient()
    github_response = github.fetch_repo(request)
    prompt = build_report_prompt(github_response)
    report = generate_report(prompt)

    repo = report.get("repo")
    if isinstance(repo, dict):
        parsed = github.parse_github_url(repo_url)
        if parsed:
            owner, name = parsed
            repo["owner"] = repo.get("owner") or owner
            repo["name"] = repo.get("name") or name
            repo["url"] = repo.get("url") or repo_url
    return report


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analyze")
def analyze(payload: AnalyzeRequest, request: Request) -> dict:
    repo_url = payload.repo_url.strip()
    github = CustomGithubClient()
    if not github.parse_github_url(repo_url):
        raise HTTPException(
            status_code=400,
            detail="repo_url must be a GitHub URL such as https://github.com/owner/repo",
        )

    _check_rate_limit(request.client.host if request.client else "unknown")
    started = time.perf_counter()
    status = "error"
    try:
        report = _run_analysis(repo_url)
        status = str(report.get("status", "unknown"))
        return report
    except RuntimeError as exc:
        if "GROQ_API_KEY" in str(exc) or "LLM" in str(exc):
            raise HTTPException(status_code=500, detail="server LLM configuration is missing") from exc
        raise HTTPException(status_code=500, detail="analysis configuration error") from exc
    except (ValueError, KeyError) as exc:
        logger.warning("analysis rejected repo_url=%s error=%s", repo_url, exc)
        raise HTTPException(status_code=502, detail="repository analysis failed") from exc
    except Exception as exc:
        logger.exception("analysis failed repo_url=%s", repo_url)
        raise HTTPException(status_code=500, detail="analysis service unavailable") from exc
    finally:
        latency_ms = (time.perf_counter() - started) * 1000
        logger.info("analyze repo_url=%s latency_ms=%.0f status=%s", repo_url, latency_ms, status)
