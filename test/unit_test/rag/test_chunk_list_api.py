# Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
"""Execute the real handler bodies with service doubles, without app bootstrap.

These tests cover response assembly and ownership gates, not HTTP authentication.
"""

import ast
import re
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest


@pytest.fixture
def api(monkeypatch):
    path = Path(__file__).parents[3] / "api/apps/restful_apis/chunk_api.py"
    names = {"_get_query_id_list", "_strip_chunk_runtime_fields", "list_chunks", "get_chunk"}
    bodies = [node for node in ast.parse(path.read_text(encoding="utf-8")).body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
    for node in bodies:
        node.decorator_list = []
    nlp = ModuleType("rag.nlp")
    nlp.search = SimpleNamespace(index_name=lambda tenant: "ragflow_" + tenant)
    monkeypatch.setitem(sys.modules, "rag.nlp", nlp)
    original = "第一段完整原文\n第二段温控器说明\n第三段审核信息"
    chunk = {"id": "chunk", "content_with_weight": original, "doc_id": "doc", "docnm_kwd": "source", "kb_id": "kb", "available_int": 1}
    result = SimpleNamespace(total=1, ids=["chunk"], highlight={"chunk": "<em>温控器</em>说明"}, field={"chunk": chunk})
    settings = SimpleNamespace(
        docStoreConn=SimpleNamespace(index_exist=Mock(return_value=True), get=Mock(side_effect=lambda *args: dict(chunk))), retriever=SimpleNamespace(search=AsyncMock(return_value=result))
    )
    namespace = {
        "re": re,
        "KnowledgebaseService": SimpleNamespace(accessible=Mock(return_value=True)),
        "_get_dataset_tenant_id": Mock(return_value="tenant"),
        "DocumentService": SimpleNamespace(query=Mock(return_value=[SimpleNamespace()])),
        "request": SimpleNamespace(args={"keywords": "温控器", "available": "true"}),
        "validate_rest_api_page": int,
        "validate_rest_api_page_size": int,
        "DEFAULT_PAGE": 1,
        "DEFAULT_PAGE_SIZE": 100,
        "validate_rest_api_ids": lambda *args: None,
        "_map_doc": lambda doc: {},
        "settings": settings,
        "get_result": lambda **kwargs: kwargs,
        "get_error_data_result": lambda **kwargs: {"code": 102, **kwargs},
        "RetCode": SimpleNamespace(DATA_ERROR=102, ARGUMENT_ERROR=101),
        "Chunk": lambda **kwargs: None,
    }
    exec(compile(ast.Module(body=bodies, type_ignores=[]), str(path), "exec"), namespace)  # noqa: S102 -- named repository functions only
    return SimpleNamespace(ns=namespace, settings=settings, result=result, chunk=chunk, original=original)


@pytest.mark.asyncio
async def test_keyword_list_preserves_full_source_even_when_highlight_is_a_snippet(api):
    response = await api.ns["list_chunks"]("tenant", "kb", "doc")
    assert response["data"]["chunks"][0]["content"] == api.original
    args, kwargs = api.settings.retriever.search.call_args
    assert args[0]["keyword_list"] is True
    assert args[0]["doc_ids"] == ["doc"]
    assert args[1:] == ("ragflow_tenant", ["kb"])
    assert kwargs == {"emb_mdl": None, "highlight": False}


@pytest.mark.asyncio
async def test_empty_page_retains_the_retrievers_full_total(api):
    api.result.total = 435
    api.result.ids = []
    response = await api.ns["list_chunks"]("tenant", "kb", "doc")
    assert response["data"]["total"] == 435
    assert response["data"]["chunks"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("available,expected", [("true", 1), ("false", 0)])
async def test_list_forwards_availability_ids_and_pagination(api, available, expected):
    api.ns["request"].args = {"keywords": "温控器", "available": available, "chunk_ids": "first,second,first", "page": "2", "page_size": "99"}
    await api.ns["list_chunks"]("tenant", "kb", "doc")
    query = api.settings.retriever.search.call_args.args[0]
    assert query["available_int"] == expected
    assert query["id"] == ["first", "second"]
    assert (query["page"], query["size"]) == (2, 99)
    assert query["must_not"] == {"exists": "compile_kwd"}


@pytest.mark.asyncio
@pytest.mark.parametrize("gate", ["dataset", "tenant", "document"])
async def test_ownership_failures_do_not_query_the_store(api, gate):
    if gate == "dataset":
        api.ns["KnowledgebaseService"].accessible.return_value = False
    elif gate == "tenant":
        api.ns["_get_dataset_tenant_id"].return_value = None
    else:
        api.ns["DocumentService"].query.return_value = []
    response = await api.ns["list_chunks"]("tenant", "kb", "doc")
    assert response["code"] == 102
    api.settings.retriever.search.assert_not_called()
    api.settings.docStoreConn.index_exist.assert_not_called()


@pytest.mark.asyncio
async def test_list_by_id_and_detail_keep_full_original_text(api):
    api.ns["request"].args["id"] = "chunk"
    listed = await api.ns["list_chunks"]("tenant", "kb", "doc")
    detail = await api.ns["get_chunk"]("tenant", "kb", "doc", "chunk")
    assert listed["data"]["chunks"][0]["content"] == detail["data"]["content_with_weight"] == api.original
    api.settings.retriever.search.assert_not_called()
