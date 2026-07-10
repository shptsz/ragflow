from api.common.access_level import (
    AccessDeniedError,
    ensure_request_allowed,
    normalize_access_level,
    is_path_allowed_for_kb_only,
)


def test_normalize_defaults_to_full():
    assert normalize_access_level(None) == "full"
    assert normalize_access_level("") == "full"
    assert normalize_access_level("kb_only") == "kb_only"


def test_kb_only_allows_datasets_and_profile():
    assert is_path_allowed_for_kb_only("GET", "/api/v1/datasets") is True
    assert is_path_allowed_for_kb_only("GET", "/api/v1/datasets/abc/documents") is True
    assert is_path_allowed_for_kb_only("GET", "/api/v1/users/me") is True
    assert is_path_allowed_for_kb_only("HEAD", "/api/v1/users/me") is True
    assert is_path_allowed_for_kb_only("OPTIONS", "/api/v1/users/me") is True
    assert is_path_allowed_for_kb_only("PATCH", "/api/v1/users/me") is True


def test_kb_only_denies_chats_agents_files():
    assert is_path_allowed_for_kb_only("GET", "/api/v1/chats") is False
    assert is_path_allowed_for_kb_only("GET", "/api/v1/agents") is False
    assert is_path_allowed_for_kb_only("GET", "/api/v1/files") is False
    assert is_path_allowed_for_kb_only("GET", "/api/v1/searches") is False
    assert is_path_allowed_for_kb_only("GET", "/api/v1/memories") is False
    assert is_path_allowed_for_kb_only("GET", "/api/v1/tenants/x/users") is False
    assert is_path_allowed_for_kb_only("PATCH", "/api/v1/users/me/models") is False


def test_kb_only_allows_kb_domain_routes():
    assert is_path_allowed_for_kb_only("POST", "/api/v1/documents/upload") is True
    assert is_path_allowed_for_kb_only("POST", "/api/v1/retrieval") is True
    assert is_path_allowed_for_kb_only("GET", "/api/v1/thumbnails") is True
    assert is_path_allowed_for_kb_only("POST", "/api/v1/files/link-to-datasets") is True
    assert is_path_allowed_for_kb_only("POST", "/api/v1/tasks/task-1/cancel") is True
    assert is_path_allowed_for_kb_only("GET", "/api/v1/datasets/abc/documents/doc-1/chunks") is True
    assert is_path_allowed_for_kb_only("GET", "/api/v1/documents/doc-1/preview") is True


def test_kb_only_allows_auth_and_system():
    assert is_path_allowed_for_kb_only("POST", "/api/v1/auth/login") is True
    assert is_path_allowed_for_kb_only("POST", "/api/v1/auth/logout") is True
    assert is_path_allowed_for_kb_only("GET", "/api/v1/system/ping") is True
    assert is_path_allowed_for_kb_only("GET", "/api/v1/system/healthz") is True
    assert is_path_allowed_for_kb_only("GET", "/api/v1/system/config") is True
    assert is_path_allowed_for_kb_only("GET", "/v1/system/healthz") is True


def test_kb_only_allows_read_only_models():
    assert is_path_allowed_for_kb_only("GET", "/api/v1/models") is True
    assert is_path_allowed_for_kb_only("GET", "/api/v1/models/default") is True
    assert is_path_allowed_for_kb_only("HEAD", "/api/v1/models") is True
    assert is_path_allowed_for_kb_only("OPTIONS", "/api/v1/models/default") is True


def test_kb_only_denies_non_kb_modules():
    assert is_path_allowed_for_kb_only("GET", "/api/v1/mcp/servers") is False
    assert is_path_allowed_for_kb_only("GET", "/api/v1/connectors") is False
    assert is_path_allowed_for_kb_only("GET", "/api/v1/providers") is False
    assert is_path_allowed_for_kb_only("PATCH", "/api/v1/models/default") is False
    assert is_path_allowed_for_kb_only("GET", "/api/v1/users/me/models") is False
    assert is_path_allowed_for_kb_only("GET", "/v1/document/download/xyz") is False
    assert is_path_allowed_for_kb_only("POST", "/v1/document/upload_info") is True


def test_ensure_request_allowed_full_access():
    ensure_request_allowed("full", "GET", "/api/v1/chats")
    ensure_request_allowed(None, "GET", "/api/v1/chats")


def test_ensure_request_allowed_kb_only_datasets_ok():
    ensure_request_allowed("kb_only", "GET", "/api/v1/datasets")


def test_ensure_request_allowed_raises_for_kb_only():
    try:
        ensure_request_allowed("kb_only", "GET", "/api/v1/chats")
        assert False, "expected AccessDeniedError"
    except AccessDeniedError:
        pass


def test_login_required_wires_access_level_guard():
    """文档化 login_required 中的 access_level 拦截接线（不加载完整 Quart app）。"""
    from pathlib import Path

    from common.constants import RetCode

    source = Path("api/apps/__init__.py").read_text(encoding="utf-8")
    assert "ensure_request_allowed" in source
    assert "AccessDeniedError" in source
    assert "RetCode.FORBIDDEN" in source
    assert RetCode.FORBIDDEN == 403
