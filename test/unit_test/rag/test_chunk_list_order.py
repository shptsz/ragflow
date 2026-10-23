#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
"""Chunk-list ordering contracts, using an in-memory store that changes tie order.

These tests exercise Dealer, not the Infinity server's sort implementation.
"""

import importlib.util
import random
import sys
import types
from pathlib import Path

import pytest

from common.doc_store.doc_store_base import MatchTextExpr


@pytest.fixture
def search_module(monkeypatch):
    # Avoid tokenizer models and live service configuration when loading Dealer.
    fake_nlp = types.ModuleType("rag.nlp")
    fake_nlp.__path__ = []
    fake_nlp.rag_tokenizer = types.SimpleNamespace(fine_grained_tokenize=lambda text: text)

    class Queryer:
        def question(self, text, min_match):
            return MatchTextExpr(["content_ltks"], text, 10, {}), [text]

    fake_nlp.query = types.SimpleNamespace(FulltextQueryer=Queryer)
    fake_settings = types.ModuleType("common.settings")
    for engine in ("INFINITY", "OCEANBASE", "SERENEDB", "GAUSSDB"):
        setattr(fake_settings, f"DOC_ENGINE_{engine}", engine == "INFINITY")

    import common

    monkeypatch.setattr(common, "settings", fake_settings, raising=False)
    monkeypatch.setitem(sys.modules, "common.settings", fake_settings)
    monkeypatch.setitem(sys.modules, "rag.nlp", fake_nlp)
    path = Path(__file__).parents[3] / "rag" / "nlp" / "search.py"
    spec = importlib.util.spec_from_file_location("rag.nlp.search", path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


class _ReorderingStore:
    """Apply the requested sort before slicing, with no implicit ID tie-breaker."""

    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def search(self, fields, highlight, condition, matches, order_by, offset, limit, indexes, datasets, **kwargs):
        self.calls.append({"order": list(order_by.fields), "condition": condition, "matches": matches, "offset": offset, "limit": limit, "indexes": indexes, "datasets": datasets})
        rows = [row for row in self.rows if self._matches(row, condition)]
        # Independent requests may return equal-key records in different orders.
        random.Random(len(self.calls)).shuffle(rows)
        for field, descending in reversed(order_by.fields):
            rows.sort(key=lambda row: row[field], reverse=bool(descending))
        return {"total": len(rows), "rows": rows[offset : offset + limit]}

    @staticmethod
    def _matches(row, condition):
        for field, value in condition.items():
            if field == "must_not":
                if value.get("exists") in row:
                    return False
            elif row.get(field) not in (value if isinstance(value, list) else [value]):
                return False
        return True

    def get_total(self, result):
        return result["total"]

    def get_doc_ids(self, result):
        return [row["id"] for row in result["rows"]]

    def get_fields(self, result, fields):
        return {row["id"]: row for row in result["rows"]}

    def get_highlight(self, result, keywords, field):
        return {}

    def get_aggregation(self, result, field):
        return []


def _chunk(chunk_id, **overrides):
    return {"id": chunk_id, "doc_id": "doc", "kb_id": "kb", "available_int": 1, "chunk_order_int": 0, "page_num_int": 0, "top_int": 0, "create_timestamp_flt": 1792728064.0, **overrides}


@pytest.mark.asyncio
@pytest.mark.parametrize("page_size", [20, 99, 100])
@pytest.mark.parametrize("available", [None, 0, 1])
async def test_tied_chunks_are_complete_and_stable_across_pages(search_module, page_size, available):
    rows = [_chunk(f"{i:032x}", available_int=i % 2) for i in range(2303)]
    rows += [_chunk("other-doc", doc_id="other"), _chunk("compiled", compile_kwd="page_index")]
    store = _ReorderingStore(rows)
    dealer = search_module.Dealer(store)
    expected = sorted(row["id"] for row in rows if row["doc_id"] == "doc" and "compile_kwd" not in row and (available is None or row["available_int"] == available))
    request = {"doc_ids": ["doc"], "question": "", "sort": True, "must_not": {"exists": "compile_kwd"}}
    if available is not None:
        request["available_int"] = available

    for _ in range(3):
        ids = []
        for page in range(1, (len(expected) + page_size - 1) // page_size + 2):
            result = await dealer.search({**request, "page": page, "size": page_size}, "ragflow_tenant", ["kb"])
            assert result.total == len(expected)
            ids.extend(result.ids)
        assert len(ids) == len(set(ids)) == len(expected)
        assert ids == expected

    assert store.calls[0]["condition"] == {"doc_id": ["doc"], "must_not": {"exists": "compile_kwd"}, **({"available_int": available} if available is not None else {})}
    assert all(call["indexes"] == "ragflow_tenant" and call["datasets"] == ["kb"] for call in store.calls)


@pytest.mark.asyncio
async def test_pageindex_chunk_order_retains_original_priorities(search_module):
    # Same request contract as the PageIndex structure graph's chunk-order load.
    rows = [
        _chunk("z-first", chunk_order_int=0, page_num_int=9, top_int=9, create_timestamp_flt=1),
        _chunk("y-page", chunk_order_int=1, page_num_int=0, top_int=9, create_timestamp_flt=1),
        _chunk("x-top", chunk_order_int=1, page_num_int=1, top_int=0, create_timestamp_flt=1),
        _chunk("w-newer", chunk_order_int=1, page_num_int=1, top_int=1, create_timestamp_flt=3),
        _chunk("b-tie", chunk_order_int=1, page_num_int=1, top_int=1, create_timestamp_flt=2),
        _chunk("a-tie", chunk_order_int=1, page_num_int=1, top_int=1, create_timestamp_flt=2),
        _chunk("0-compiled", compile_kwd="page_index"),
    ]
    dealer = search_module.Dealer(_ReorderingStore(rows))
    result = await dealer.search(
        {"doc_ids": ["doc"], "page": 1, "size": 10000, "question": "", "sort": True, "must_not": {"exists": "compile_kwd"}}, "ragflow_tenant", ["kb"], emb_mdl=None, highlight=True
    )
    assert result.ids == ["z-first", "y-page", "x-top", "w-newer", "a-tie", "b-tie"]
    assert result.total == 6


@pytest.mark.asyncio
@pytest.mark.parametrize("sort", [False, None])
async def test_unsorted_requests_do_not_gain_id_order(search_module, sort):
    store = _ReorderingStore([_chunk("chunk")])
    await search_module.Dealer(store).search({"sort": sort}, "ragflow_tenant", ["kb"])
    assert store.calls[0]["order"] == []


@pytest.mark.asyncio
async def test_non_infinity_retains_original_order(search_module):
    search_module.settings.DOC_ENGINE_INFINITY = False
    store = _ReorderingStore([_chunk("chunk")])
    await search_module.Dealer(store).search({"sort": True}, "ragflow_tenant", ["kb"])
    assert store.calls[0]["order"] == [("chunk_order_int", 0), ("page_num_int", 0), ("top_int", 0), ("create_timestamp_flt", 1)]


@pytest.mark.asyncio
@pytest.mark.parametrize("hybrid", [False, True])
async def test_keyword_and_hybrid_search_do_not_gain_id_order(search_module, hybrid):
    class EmbeddingModel:
        def encode_queries(self, text):
            return [0.1, 0.2], None

    store = _ReorderingStore([_chunk("chunk")])
    await search_module.Dealer(store).search({"question": "keyword", "sort": True}, "ragflow_tenant", ["kb"], emb_mdl=EmbeddingModel() if hybrid else None)
    assert store.calls[0]["order"] == []
    assert len(store.calls[0]["matches"]) == (3 if hybrid else 1)
