from fastapi import APIRouter
from pydantic import BaseModel, HttpUrl

from app.services.web_search import WebSearchService
from app.services.web_parser import WebParserService

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    max_results: int = 5


class ParseRequest(BaseModel):
    url: HttpUrl
    extract_links: bool = False


@router.post("/web-search")
async def web_search(req: SearchRequest):
    """DuckDuckGo search → list of {title, url, snippet}."""
    svc = WebSearchService()
    results = await svc.search(req.query, max_results=req.max_results)
    return {"results": results}


@router.post("/web-parse")
async def web_parse(req: ParseRequest):
    """Fetch URL → extract clean text (+ optional links)."""
    svc = WebParserService()
    result = await svc.parse(str(req.url), extract_links=req.extract_links)
    return result
