"""Tests for models/pagination.py."""

from enverus_developer_api.models.pagination import LinkInfo, PaginationLinks


class TestPaginationLinks:
    def test_next_only(self):
        pl = PaginationLinks(next=LinkInfo(url="/wells?page=2", rel="next"))
        assert pl.next is not None
        assert pl.next.url == "/wells?page=2"
        assert pl.prev is None

    def test_both_links(self):
        pl = PaginationLinks(
            next=LinkInfo(url="/wells?page=3", rel="next"),
            prev=LinkInfo(url="/wells?page=1", rel="prev"),
        )
        assert pl.next is not None
        assert pl.prev is not None

    def test_empty(self):
        pl = PaginationLinks()
        assert pl.next is None
        assert pl.prev is None
