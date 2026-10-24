# Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
"""Real Infinity keyword pagination; only creates/drops uniquely named test tables.

Run against an isolated Infinity 0.7.3 instance:
INFINITY_HOST=127.0.0.1 python -m pytest test/integration/test_infinity_keyword_list.py
Uses the existing INFINITY_HOST / INFINITY_THRIFT_PORT settings (port defaults to 23817).
No RAGFlow database, tokenizer models or LLM is needed.
"""

import importlib.util
import logging
import os
import sys
import uuid
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


@pytest.fixture(scope="module")
def store():
    host = os.environ.get("INFINITY_HOST")
    if not host:
        pytest.skip("Set INFINITY_HOST to an isolated test instance")

    import infinity
    from infinity.common import NetworkAddress
    from infinity.index import IndexInfo, IndexType

    import common

    root = Path(__file__).parents[2]
    with pytest.MonkeyPatch.context() as patch:
        settings = ModuleType("common.settings")
        nlp = ModuleType("rag.nlp")
        nlp.is_english = lambda text: True
        patch.setattr(common, "settings", settings, raising=False)
        patch.setitem(sys.modules, "common.settings", settings)
        patch.setitem(sys.modules, "rag.nlp", nlp)
        for name, relative in [
            ("common.doc_store.infinity_conn_base", "common/doc_store/infinity_conn_base.py"),
            ("keyword_test_infinity", "rag/utils/infinity_conn.py"),
        ]:
            spec = importlib.util.spec_from_file_location(name, root / relative)
            module = importlib.util.module_from_spec(spec)
            patch.setitem(sys.modules, name, module)
            spec.loader.exec_module(module)

        cls = next(cell.cell_contents for cell in module.InfinityConnection.__closure__ if isinstance(cell.cell_contents, type))
        native = infinity.connect(NetworkAddress(host, int(os.environ.get("INFINITY_THRIFT_PORT", "23817"))))
        db = native.get_database("default_db")
        index = f"ragflow_keyword_test_{uuid.uuid4().hex}"
        tables = []
        rows = []
        conn = cls.__new__(cls)
        conn.dbName = "default_db"
        conn.logger = logging.getLogger(__name__)
        conn.connPool = SimpleNamespace(get_conn=lambda: native, release_conn=lambda connection: None)
        try:
            for kb, count in [("kb", 435), ("otherkb", 17)]:
                table = db.create_table(
                    f"{index}_{kb}",
                    {
                        "id": {"type": "varchar"},
                        "doc_id": {"type": "varchar"},
                        "content": {"type": "varchar"},
                        "available_int": {"type": "integer"},
                        "compile_kwd": {"type": "varchar", "default": ""},
                        "pagerank_fea": {"type": "integer", "default": 0},
                    },
                )
                tables.append(f"{index}_{kb}")
                for granularity in ["coarse", "fine"]:
                    table.create_index(f"ft_content_rag_{granularity}", IndexInfo("content", IndexType.FullText, {"ANALYZER": f"rag-{granularity}"}))
                batch = [{"id": f"{kb}-{i:04}", "doc_id": "doc", "content": "alpha beta", "available_int": 1, "pagerank_fea": i % 3} for i in range(count)]
                if kb == "kb":
                    batch += [{"id": f"zh-{i:04}", "doc_id": "chinese", "content": "温控器 热计量" if i < 189 else "热计量", "available_int": 1} for i in range(434)]
                    batch += [{"id": f"disabled-{i:04}", "doc_id": "doc", "content": "alpha beta", "available_int": 0} for i in range(120)]
                    batch += [{"id": f"small-{i}", "doc_id": "doc", "content": "smallonly", "available_int": 1} for i in range(3)]
                    batch += [{"id": f"exact-{i:04}", "doc_id": "doc", "content": "exactonly", "available_int": 1} for i in range(100)]
                    batch += [
                        {"id": "wrong-doc", "doc_id": "other", "content": "alpha beta", "available_int": 1},
                        {"id": "compiled", "doc_id": "doc", "content": "alpha beta", "available_int": 1, "compile_kwd": "page_index"},
                        {"id": "partial", "doc_id": "doc", "content": "alpha", "available_int": 1},
                    ]
                table.insert(batch)
                rows.extend({"kb": kb, **row} for row in batch)
                if kb == "kb":
                    for start in range(0, 9005, 1000):
                        table.insert([{"id": f"large-{i:05}", "doc_id": "large", "content": "largekeyword", "available_int": 1} for i in range(start, min(start + 1000, 9005))])
                    table.insert(
                        [
                            {"id": "precision-a", "doc_id": "precision", "content": "precisionneedle " + "padding " * 10002, "available_int": 1, "pagerank_fea": 100},
                            {"id": "precision-b", "doc_id": "precision", "content": "precisionneedle " + "padding " * 10000, "available_int": 1, "pagerank_fea": 100},
                            {"id": "precision-c", "doc_id": "precision", "content": "precisionneedle " + "padding " * 10001, "available_int": 1, "pagerank_fea": 100},
                        ]
                    )
            yield SimpleNamespace(conn=conn, index=index, rows=rows)
        finally:
            for name in tables:
                db.drop_table(name)
            native.disconnect()


def read(store, text="alpha beta", offset=0, size=100, available=1, datasets=None, keyword_list=True):
    from common.doc_store.doc_store_base import MatchTextExpr, OrderByExpr

    matches = [MatchTextExpr(["content_ltks"], text, 100, {"minimum_should_match": 1.0})] if text else []
    return store.conn.search(
        ["id", "content_with_weight"],
        [],
        {"doc_id": ["doc"], "available_int": available, "must_not": {"exists": "compile_kwd"}},
        matches,
        OrderByExpr().asc("id") if not text else OrderByExpr(),
        offset,
        size,
        store.index,
        datasets or ["kb"],
        keyword_list=keyword_list and bool(text),
    )


@pytest.mark.parametrize("available,total", [(1, 435), (0, 120)])
@pytest.mark.parametrize("page_size", [1, 20, 99, 100])
def test_all_keyword_pages_have_stable_total_order_and_complete_ids(store, available, total, page_size):
    reference, reference_total = read(store, size=10000, available=available)
    assert reference_total == total
    assert reference["pagerank_fea"].tolist() == sorted(reference["pagerank_fea"].tolist(), reverse=True)
    expected = {row["id"] for row in store.rows if row["kb"] == "kb" and row["doc_id"] == "doc" and row["available_int"] == available and row["content"] == "alpha beta" and not row.get("compile_kwd")}
    ids = []
    for offset in range(0, total + page_size + 1, page_size):
        frame, count = read(store, offset=offset, size=page_size, available=available)
        assert count == total
        assert len(frame) <= page_size
        ids.extend(frame["id"])
    assert len(ids) == len(set(ids)) == total
    assert set(ids) == expected
    assert ids == reference["id"].tolist()
    assert set(reference["content"]) == {"alpha beta"}


@pytest.mark.parametrize("text,total", [("smallonly", 3), ("exactonly", 100), ("nonexistent", 0)])
def test_short_exact_and_empty_keyword_lists_preserve_total_on_empty_pages(store, text, total):
    for offset in [0, 100, 10000]:
        frame, count = read(store, text=text, offset=offset)
        assert count == total
        assert len(frame) == max(0, min(100, total - offset))


def test_multiple_datasets_are_sorted_and_paged_after_merging(store):
    reference, total = read(store, size=10000, datasets=["kb", "otherkb"])
    assert total == 452
    ids = []
    for offset in range(0, 500, 20):
        frame, count = read(store, offset=offset, size=20, datasets=["kb", "otherkb"])
        assert count == total
        ids.extend(frame["id"])
    assert ids == reference["id"].tolist()
    assert len(set(ids)) == total


@pytest.mark.parametrize("keyword,total", [("温控器", 189), ("热计量", 434)])
def test_chinese_weighted_phrase_queries_count_the_same_predicate_as_pagination(store, keyword, total):
    from common.doc_store.doc_store_base import MatchTextExpr, OrderByExpr

    # Shape emitted by FulltextQueryer.question(), including phrase/proximity clauses.
    query = f'(({keyword} OR "{keyword}" OR ("{keyword}"~2)^0.5)^1.0)'

    def page(offset, size):
        return store.conn.search(
            ["id", "content_with_weight"],
            [],
            {"doc_id": ["chinese"], "available_int": 1},
            [MatchTextExpr(["content_ltks^2", "content_sm_ltks"], query, 100, {"minimum_should_match": 0.3})],
            OrderByExpr(),
            offset,
            size,
            store.index,
            ["kb"],
            keyword_list=True,
        )

    reference, count = page(0, 10000)
    assert count == total
    for size in [1, 20, 99, 100]:
        ids = []
        for offset in range(0, total + size + 1, size):
            frame, count = page(offset, size)
            assert count == total
            ids.extend(frame["id"])
        assert ids == reference["id"].tolist()
        assert len(set(ids)) == total


def test_unmarked_retrieval_retains_its_candidate_window(store):
    frame, total = read(store, keyword_list=False)
    assert total == len(frame) == 100


def test_plain_lists_remain_complete(store):
    reference, total = read(store, text="", size=10000)
    assert total == 539
    ids = []
    for offset in range(0, 601, 100):
        frame, count = read(store, text="", offset=offset)
        assert count == total
        ids.extend(frame["id"])
    assert ids == reference["id"].tolist()
    assert len(set(ids)) == total


def test_segmented_fulltext_counts_include_matches_after_the_first_segment(store):
    from common.doc_store.doc_store_base import MatchTextExpr, OrderByExpr

    def page(offset, size=100, ids=None):
        condition = {"doc_id": ["large"], "available_int": 1}
        if ids:
            condition["id"] = ids
        return store.conn.search(
            ["id"],
            [],
            condition,
            [MatchTextExpr(["content_ltks"], "largekeyword", 100, {})],
            OrderByExpr(),
            offset,
            size,
            store.index,
            ["kb"],
            keyword_list=True,
        )

    for size in [1, 20, 99, 100]:
        for offset in [0, 8191, 8192, 9004, 9005, 10000]:
            frame, total = page(offset, size)
            assert total == 9005
            assert frame["id"].tolist() == [f"large-{i:05}" for i in range(offset, min(offset + size, 9005))]
    frame, total = page(0, ids=["large-09004"])
    assert total == 1
    assert frame["id"].tolist() == ["large-09004"]


def test_integer_pagerank_and_fractional_scores_use_one_order_before_pagination(store):
    from common.doc_store.doc_store_base import MatchTextExpr, OrderByExpr

    def page(offset, size):
        return store.conn.search(
            ["id"],
            [],
            {"doc_id": ["precision"]},
            [MatchTextExpr(["content_ltks"], "precisionneedle", 100, {})],
            OrderByExpr(),
            offset,
            size,
            store.index,
            ["kb"],
            keyword_list=True,
        )

    reference, total = page(0, 100)
    assert total == 3
    assert reference["id"].tolist() == ["precision-b", "precision-a", "precision-c"]
    assert reference["_score"].iloc[0] > reference["_score"].iloc[1] == reference["_score"].iloc[2]
    for size in [1, 2, 20, 99, 100]:
        ids = []
        for offset in range(0, total, size):
            frame, count = page(offset, size)
            assert count == total
            ids.extend(frame["id"])
        assert ids == reference["id"].tolist()
