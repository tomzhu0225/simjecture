"""Bounded host-side literature and web reconnaissance.

The computational sandbox deliberately has no network.  This module gives the
agent a narrow, auditable search boundary instead: fixed public search services
return metadata and snippets, while credentials and arbitrary network access
remain outside the sandbox.
"""

from __future__ import annotations

import hashlib
import html
from datetime import datetime
from enum import StrEnum
from html.parser import HTMLParser
from typing import Annotated, Any, Literal, Protocol
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from pydantic import Field

from .models import StrictModel, utc_now


class LiteratureSearchStatus(StrEnum):
    COMPLETED = "completed"
    UNAVAILABLE = "unavailable"


BoundedAuthor = Annotated[str, Field(min_length=1, max_length=300)]


class LiteratureSource(StrictModel):
    """One bounded search hit, not evidence for the active hypothesis."""

    id: str = Field(min_length=1, max_length=1200)
    kind: Literal["paper", "web"]
    provider: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=1000)
    authors: tuple[BoundedAuthor, ...] = Field(default=(), max_length=50)
    publication_year: int | None = Field(default=None, ge=1400, le=3000)
    doi: str | None = Field(default=None, max_length=1000)
    url: str = Field(min_length=1, max_length=4000)
    full_text_url: str | None = Field(default=None, max_length=4000)
    abstract: str | None = Field(default=None, max_length=3000)
    snippet: str | None = Field(default=None, max_length=1000)
    source_name: str | None = Field(default=None, max_length=1000)
    cited_by_count: int | None = Field(default=None, ge=0)
    open_access: bool | None = None


class LiteratureSearchRecord(StrictModel):
    """Immutable result of one startup or later reconnaissance attempt."""

    schema_version: Literal["0.1.0"] = "0.1.0"
    id: str = Field(pattern=r"^literature_search_[0-9a-f]{16}$")
    hypothesis_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    query: str = Field(min_length=3)
    purpose: str = Field(min_length=3)
    requested_results: int = Field(ge=1, le=20)
    status: LiteratureSearchStatus
    sources: tuple[LiteratureSource, ...] = ()
    provider_status: dict[str, str]
    errors: tuple[str, ...] = ()
    searched_at: datetime
    scientific_evidence_eligible: Literal[False] = False

    def diagnostics(self) -> dict[str, Any]:
        """Summarize provider coverage without overstating a zero-hit search."""

        reachable = sorted(
            name for name, value in self.provider_status.items() if value.startswith("ok:")
        )
        failed = sorted(
            name
            for name, value in self.provider_status.items()
            if value.startswith("error:")
        )
        zero_hit = sorted(
            name for name, value in self.provider_status.items() if value == "ok:0"
        )
        if self.sources:
            coverage = "sources_found"
        elif reachable and failed:
            coverage = "zero_hits_with_provider_failures"
        elif reachable:
            coverage = "zero_hits"
        else:
            coverage = "providers_unavailable"
        return {
            "coverage": coverage,
            "usable_source_count": len(self.sources),
            "reachable_providers": reachable,
            "failed_providers": failed,
            "zero_hit_providers": zero_hit,
            "partial_provider_failure": bool(reachable and failed),
            "supports_absence_or_novelty_claim": False,
        }


class LiteratureSearchClient(Protocol):
    @property
    def identity(self) -> dict[str, Any]: ...

    def search(
        self,
        *,
        hypothesis: str,
        query: str,
        purpose: str,
        max_results: int,
    ) -> LiteratureSearchRecord: ...


def _compact_space(value: str) -> str:
    return " ".join(html.unescape(value).split())


def _bounded_text(value: object, maximum: int) -> str:
    return _compact_space(str(value))[:maximum]


def _abstract_from_inverted_index(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    positioned: list[tuple[int, str]] = []
    for word, positions in value.items():
        if not isinstance(word, str) or not isinstance(positions, list):
            continue
        for position in positions:
            if isinstance(position, int) and position >= 0:
                positioned.append((position, word))
    if not positioned:
        return None
    positioned.sort()
    return _bounded_text(" ".join(word for _position, word in positioned), 3000)


def _doi_key(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.casefold().strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
            break
    return normalized or None


class _DuckDuckGoParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict[str, str]] = []
        self._active: str | None = None
        self._href: str | None = None
        self._text: list[str] = []
        self._pending: dict[str, str] | None = None

    @staticmethod
    def _classes(attributes: list[tuple[str, str | None]]) -> set[str]:
        value = next((value for name, value in attributes if name == "class"), "")
        return set((value or "").split())

    def handle_starttag(
        self,
        tag: str,
        attributes: list[tuple[str, str | None]],
    ) -> None:
        classes = self._classes(attributes)
        if tag == "a" and "result__a" in classes:
            if self._pending is not None:
                self.results.append(self._pending)
            self._pending = {}
            self._active = "title"
            self._href = next(
                (value for name, value in attributes if name == "href" and value),
                None,
            )
            self._text = []
        elif "result__snippet" in classes:
            self._active = "snippet"
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._active is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._active == "title" and tag == "a":
            assert self._pending is not None
            self._pending["title"] = _compact_space("".join(self._text))
            if self._href is not None:
                self._pending["url"] = self._decode_url(self._href)
            self._active = None
            self._text = []
            self._href = None
        elif self._active == "snippet" and tag in {"a", "div"}:
            if self._pending is not None:
                self._pending["snippet"] = _compact_space("".join(self._text))
            self._active = None
            self._text = []

    def close(self) -> None:
        super().close()
        if self._pending is not None:
            self.results.append(self._pending)
            self._pending = None

    @staticmethod
    def _decode_url(value: str) -> str:
        candidate = value
        if candidate.startswith("//"):
            candidate = "https:" + candidate
        parsed = urlparse(candidate)
        redirect = parse_qs(parsed.query).get("uddg")
        if parsed.netloc.endswith("duckduckgo.com") and redirect:
            return unquote(redirect[0])
        return candidate


class PublicLiteratureSearchClient:
    """Search papers and the public web through fixed, uncredentialed services."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("literature search timeout must be positive")
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    @property
    def identity(self) -> dict[str, Any]:
        return {
            "name": "public-literature-search",
            "version": "1",
            "providers": ["openalex", "crossref", "duckduckgo_html"],
            "network_location": "host",
            "sandbox_network_enabled": False,
            "credentials_required": False,
        }

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=self.timeout_seconds,
            follow_redirects=True,
            transport=self.transport,
            headers={
                "User-Agent": "simjecture/0.1 literature reconnaissance",
                "Accept": "application/json, text/html;q=0.9, */*;q=0.5",
            },
        )

    @staticmethod
    def _openalex_sources(payload: dict[str, Any]) -> list[LiteratureSource]:
        sources: list[LiteratureSource] = []
        for item in payload.get("results") or []:
            if not isinstance(item, dict) or not item.get("title") or not item.get("id"):
                continue
            authors = tuple(
                _bounded_text(authorship.get("author", {}).get("display_name"), 300)
                for authorship in item.get("authorships") or []
                if isinstance(authorship, dict)
                and isinstance(authorship.get("author"), dict)
                and authorship["author"].get("display_name")
            )[:50]
            primary = item.get("primary_location") or {}
            best = item.get("best_oa_location") or {}
            content_urls = item.get("content_urls") or {}
            doi = _doi_key(item.get("doi"))
            url = (
                (f"https://doi.org/{doi}" if doi else None)
                or primary.get("landing_page_url")
                or best.get("landing_page_url")
                or str(item["id"])
            )
            full_text_url = (
                content_urls.get("grobid_xml")
                or content_urls.get("pdf")
                or best.get("pdf_url")
                or primary.get("pdf_url")
            )
            source = primary.get("source") or {}
            open_access = item.get("open_access") or {}
            sources.append(
                LiteratureSource(
                    id="openalex:" + str(item["id"]).rstrip("/").rsplit("/", 1)[-1],
                    kind="paper",
                    provider="openalex",
                    title=_bounded_text(item["title"], 1000),
                    authors=authors,
                    publication_year=item.get("publication_year"),
                    doi=doi,
                    url=str(url),
                    full_text_url=(str(full_text_url) if full_text_url else None),
                    abstract=_abstract_from_inverted_index(
                        item.get("abstract_inverted_index")
                    ),
                    source_name=(
                        str(source.get("display_name"))
                        if source.get("display_name")
                        else None
                    ),
                    cited_by_count=item.get("cited_by_count"),
                    open_access=(
                        bool(open_access.get("is_oa"))
                        if "is_oa" in open_access
                        else None
                    ),
                )
            )
        return sources

    @staticmethod
    def _crossref_sources(payload: dict[str, Any]) -> list[LiteratureSource]:
        sources: list[LiteratureSource] = []
        message = payload.get("message") or {}
        for item in message.get("items") or []:
            titles = item.get("title") or []
            doi = _doi_key(item.get("DOI"))
            if not titles or not doi:
                continue
            authors = tuple(
                _bounded_text(
                    " ".join(
                        part
                        for part in (author.get("given"), author.get("family"))
                        if part
                    ),
                    300,
                )
                for author in item.get("author") or []
                if isinstance(author, dict)
            )[:50]
            date_parts = (item.get("published") or {}).get("date-parts") or []
            year = None
            if date_parts and date_parts[0] and isinstance(date_parts[0][0], int):
                year = date_parts[0][0]
            containers = item.get("container-title") or []
            sources.append(
                LiteratureSource(
                    id="crossref:" + doi,
                    kind="paper",
                    provider="crossref",
                    title=_bounded_text(titles[0], 1000),
                    authors=authors,
                    publication_year=year,
                    doi=doi,
                    url=str(item.get("URL") or f"https://doi.org/{doi}"),
                    abstract=(
                        _bounded_text(item["abstract"], 3000)
                        if item.get("abstract")
                        else None
                    ),
                    source_name=(str(containers[0]) if containers else None),
                    cited_by_count=item.get("is-referenced-by-count"),
                )
            )
        return sources

    @staticmethod
    def _web_sources(text: str) -> list[LiteratureSource]:
        parser = _DuckDuckGoParser()
        parser.feed(text)
        parser.close()
        sources: list[LiteratureSource] = []
        for index, item in enumerate(parser.results):
            title = item.get("title")
            url = item.get("url")
            if not title or not url or not url.startswith(("http://", "https://")):
                continue
            digest = hashlib.sha256(url.encode()).hexdigest()[:16]
            sources.append(
                LiteratureSource(
                    id=f"web:{digest}:{index}",
                    kind="web",
                    provider="duckduckgo_html",
                    title=title,
                    url=url,
                    snippet=item.get("snippet") or None,
                    source_name=urlparse(url).netloc or None,
                )
            )
        return sources

    @staticmethod
    def _deduplicate(
        sources: list[LiteratureSource],
        *,
        maximum: int,
    ) -> tuple[LiteratureSource, ...]:
        unique: list[LiteratureSource] = []
        seen: set[str] = set()
        for source in sources:
            key = (
                "doi:" + source.doi
                if source.doi
                else "url:" + source.url.casefold().rstrip("/")
            )
            title_key = "title:" + source.title.casefold()
            if key in seen or title_key in seen:
                continue
            seen.update((key, title_key))
            unique.append(source)

        papers = [item for item in unique if item.kind == "paper"]
        web = [item for item in unique if item.kind == "web"]
        web_budget = min(len(web), max(1, maximum // 3)) if maximum >= 2 else 0
        paper_budget = min(len(papers), maximum - web_budget)
        result = [*papers[:paper_budget], *web[:web_budget]]
        selected = {item.id for item in result}
        for source in unique:
            if len(result) >= maximum:
                break
            if source.id not in selected:
                result.append(source)
                selected.add(source.id)
        return tuple(result)

    def search(
        self,
        *,
        hypothesis: str,
        query: str,
        purpose: str,
        max_results: int,
    ) -> LiteratureSearchRecord:
        query = _compact_space(query)
        purpose = _compact_space(purpose)
        if len(query) < 3 or len(query) > 500:
            raise ValueError("literature query must contain 3 to 500 characters")
        if len(purpose) < 3 or len(purpose) > 1000:
            raise ValueError("literature search purpose must contain 3 to 1000 characters")
        if not 1 <= max_results <= 20:
            raise ValueError("literature search max_results must lie in [1, 20]")

        providers: dict[str, str] = {}
        errors: list[str] = []
        sources: list[LiteratureSource] = []
        with self._client() as client:
            requests: tuple[
                tuple[str, str, dict[str, str | int], Any], ...
            ] = (
                (
                    "openalex",
                    "https://api.openalex.org/works",
                    {
                        "search": query,
                        "per-page": max_results,
                        "select": (
                            "id,doi,title,publication_year,authorships,cited_by_count,"
                            "primary_location,best_oa_location,open_access,"
                            "abstract_inverted_index,content_urls"
                        ),
                    },
                    self._openalex_sources,
                ),
                (
                    "crossref",
                    "https://api.crossref.org/works",
                    {
                        "query.bibliographic": query,
                        "rows": max_results,
                        "select": (
                            "DOI,title,published,author,URL,is-referenced-by-count,"
                            "type,container-title,abstract"
                        ),
                    },
                    self._crossref_sources,
                ),
            )
            for name, url, parameters, parser in requests:
                try:
                    response = client.get(url, params=parameters)
                    response.raise_for_status()
                    found = parser(response.json())
                    sources.extend(found)
                    providers[name] = f"ok:{len(found)}"
                except Exception as error:  # provider failure is a recorded waiver
                    detail = f"{name}: {type(error).__name__}: {error}"[:500]
                    errors.append(detail)
                    providers[name] = f"error:{type(error).__name__}"
            try:
                response = client.get(
                    "https://html.duckduckgo.com/html/",
                    params={"q": query},
                    headers={"Accept": "text/html"},
                )
                response.raise_for_status()
                found = self._web_sources(response.text)
                sources.extend(found)
                providers["duckduckgo_html"] = f"ok:{len(found)}"
            except Exception as error:  # provider failure is a recorded waiver
                detail = f"duckduckgo_html: {type(error).__name__}: {error}"[:500]
                errors.append(detail)
                providers["duckduckgo_html"] = f"error:{type(error).__name__}"

        any_available = any(value.startswith("ok:") for value in providers.values())
        searched_at = utc_now()
        identity_material = "\n".join(
            (
                hashlib.sha256(hypothesis.strip().encode()).hexdigest(),
                query,
                searched_at.isoformat(),
            )
        )
        return LiteratureSearchRecord(
            id="literature_search_"
            + hashlib.sha256(identity_material.encode()).hexdigest()[:16],
            hypothesis_sha256=hashlib.sha256(hypothesis.strip().encode()).hexdigest(),
            query=query,
            purpose=purpose,
            requested_results=max_results,
            status=(
                LiteratureSearchStatus.COMPLETED
                if any_available
                else LiteratureSearchStatus.UNAVAILABLE
            ),
            sources=self._deduplicate(sources, maximum=max_results),
            provider_status=providers,
            errors=tuple(errors),
            searched_at=searched_at,
        )
