"""Tests for responses/pagination.py — link extraction."""

import httpx

from enverus_developer_api.responses.pagination import _parse_body_links, extract_links


class TestExtractLinks:
    def test_from_link_header(self):
        response = httpx.Response(
            200,
            json=[{"id": 1}],
            headers={"Link": '</wells?page=2>; rel="next"'},
        )
        links = extract_links(response)
        assert links is not None
        assert links.next is not None
        assert links.next.url == "/wells?page=2"

    def test_no_links_returns_none(self):
        response = httpx.Response(200, json=[{"id": 1}])
        links = extract_links(response)
        assert links is None

    def test_from_body(self):
        body = {
            "data": [{"id": 1}],
            "links": {
                "next": "</wells?action=next&next_page=2&pagesize=50>; rel='next'"
            },
        }
        response = httpx.Response(200, json=body)
        links = extract_links(response, from_body=True)
        assert links is not None
        assert links.next is not None
        assert "/wells?" in links.next.url

    def test_from_body_no_links_key(self):
        response = httpx.Response(200, json=[{"id": 1}])
        links = extract_links(response, from_body=True)
        assert links is None

    def test_from_body_null_next(self):
        body = {"data": [{"id": 1}], "links": {"next": None}}
        response = httpx.Response(200, json=body)
        links = extract_links(response, from_body=True)
        assert links is None


class TestParseBodyLinks:
    def test_next_link(self):
        links_obj = {
            "next": "</economics?action=next&next_page=WellID+%3C+840600005436298&pagesize=50>; rel='next'"
        }
        result = _parse_body_links(links_obj)
        assert result is not None
        assert result.next is not None
        assert (
            result.next.url
            == "/economics?action=next&next_page=WellID+%3C+840600005436298&pagesize=50"
        )

    def test_no_next_link(self):
        result = _parse_body_links({"next": None})
        assert result is None

    def test_empty_dict(self):
        result = _parse_body_links({})
        assert result is None
