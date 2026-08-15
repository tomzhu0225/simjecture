from __future__ import annotations

import httpx
import pytest
from pydantic import ValidationError

from conjecture_solver.literature import (
    LiteratureSearchRecord,
    LiteratureSearchStatus,
    PublicLiteratureSearchClient,
)


def _openalex_payload() -> dict[str, object]:
    return {
        "results": [
            {
                "id": "https://openalex.org/W1",
                "doi": "https://doi.org/10.1234/example",
                "title": "A reference simulation",
                "publication_year": 2024,
                "authorships": [
                    {"author": {"display_name": "Ada Researcher"}},
                ],
                "cited_by_count": 7,
                "primary_location": {
                    "landing_page_url": "https://doi.org/10.1234/example",
                    "source": {"display_name": "Journal of Tests"},
                },
                "best_oa_location": {
                    "pdf_url": "https://example.org/reference.pdf",
                },
                "open_access": {"is_oa": True},
                "abstract_inverted_index": {
                    "Reference": [0],
                    "observable": [1],
                },
                "content_urls": {},
            }
        ]
    }


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.host == "api.openalex.org":
        return httpx.Response(200, json=_openalex_payload())
    if request.url.host == "api.crossref.org":
        return httpx.Response(
            200,
            json={
                "message": {
                    "items": [
                        {
                            "DOI": "10.1234/example",
                            "title": ["A reference simulation"],
                            "published": {"date-parts": [[2024]]},
                            "author": [{"given": "Ada", "family": "Researcher"}],
                            "URL": "https://doi.org/10.1234/example",
                            "is-referenced-by-count": 7,
                            "container-title": ["Journal of Tests"],
                        }
                    ]
                }
            },
        )
    if request.url.host == "html.duckduckgo.com":
        return httpx.Response(
            200,
            text=(
                '<a class="result__a" href="https://docs.example.org/demo">'
                "Reference demo</a>"
                '<div class="result__snippet">An official implementation example.</div>'
            ),
        )
    raise AssertionError(f"unexpected search provider {request.url}")


def test_public_search_deduplicates_papers_and_preserves_web_results() -> None:
    client = PublicLiteratureSearchClient(
        timeout_seconds=1,
        transport=httpx.MockTransport(_handler),
    )
    record = client.search(
        hypothesis="A declared numerical scaling holds in a bounded domain.",
        query="declared numerical scaling reference benchmark",
        purpose="Find a published benchmark and an implementation example.",
        max_results=4,
    )

    assert record.status is LiteratureSearchStatus.COMPLETED
    assert len(record.sources) == 2
    paper, web = record.sources
    assert paper.doi == "10.1234/example"
    assert paper.abstract == "Reference observable"
    assert web.kind == "web"
    assert web.url == "https://docs.example.org/demo"
    assert not record.scientific_evidence_eligible


def test_total_provider_failure_is_a_recorded_nonblocking_outcome() -> None:
    def fail(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    record = PublicLiteratureSearchClient(
        timeout_seconds=1,
        transport=httpx.MockTransport(fail),
    ).search(
        hypothesis="A hypothesis still needs a bounded startup attempt.",
        query="bounded startup reference",
        purpose="Attempt reconnaissance before computation.",
        max_results=3,
    )

    assert record.status is LiteratureSearchStatus.UNAVAILABLE
    assert record.sources == ()
    assert len(record.errors) == 3
    assert not record.scientific_evidence_eligible


def test_search_record_cannot_be_reclassified_as_scientific_evidence() -> None:
    record = PublicLiteratureSearchClient(
        timeout_seconds=1,
        transport=httpx.MockTransport(_handler),
    ).search(
        hypothesis="Reference material is not experimental evidence.",
        query="reference benchmark",
        purpose="Find prior work.",
        max_results=2,
    )

    tampered = record.model_dump(mode="json")
    tampered["scientific_evidence_eligible"] = True
    with pytest.raises(ValidationError):
        LiteratureSearchRecord.model_validate(tampered)
