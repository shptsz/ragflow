#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
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

from api.db import AccessLevel


class AccessDeniedError(Exception):
    """kb_only 用户访问了未授权模块。"""


_READ_ONLY_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

# kb_only 用户允许访问的路径前缀（知识库域 + 登录/基础系统接口）
_KB_ONLY_ALLOW_PREFIXES: tuple[str, ...] = (
    "/api/v1/datasets",
    "/api/v1/documents",
    "/api/v1/retrieval",
    "/api/v1/thumbnails",
    "/api/v1/tasks",
    "/api/v1/files/link-to-datasets",
    "/api/v1/auth/",
    "/api/v1/system/ping",
    "/api/v1/system/version",
    "/api/v1/system/healthz",
    "/api/v1/system/status",
    "/api/v1/system/config",
    "/v1/system/healthz",
)

# 精确匹配：个人资料、遗留上传接口等，不含 models 等子路径
_KB_ONLY_EXACT_PATHS: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/api/v1/users/me"),
        ("HEAD", "/api/v1/users/me"),
        ("OPTIONS", "/api/v1/users/me"),
        ("PATCH", "/api/v1/users/me"),
        ("POST", "/v1/document/upload_info"),
    }
)

# 仅允许只读方法访问的路径（知识库配置所需的模型列表）
_KB_ONLY_READ_ONLY_PATHS: frozenset[str] = frozenset(
    {
        "/api/v1/models",
        "/api/v1/models/default",
    }
)


def normalize_access_level(value: str | None) -> str:
    if value == AccessLevel.KB_ONLY:
        return AccessLevel.KB_ONLY
    return AccessLevel.FULL


def _normalize_path(path: str) -> str:
    return path.split("?", 1)[0].rstrip("/") or "/"


def is_path_allowed_for_kb_only(method: str, path: str) -> bool:
    method = method.upper()
    path = _normalize_path(path)

    if (method, path) in _KB_ONLY_EXACT_PATHS:
        return True

    if method in _READ_ONLY_METHODS and path in _KB_ONLY_READ_ONLY_PATHS:
        return True

    for prefix in _KB_ONLY_ALLOW_PREFIXES:
        if path == prefix.rstrip("/") or path.startswith(prefix):
            return True

    return False


def ensure_request_allowed(access_level: str | None, method: str, path: str) -> None:
    if normalize_access_level(access_level) != AccessLevel.KB_ONLY:
        return
    if not is_path_allowed_for_kb_only(method, path):
        raise AccessDeniedError(f"kb_only 用户无权访问 {method} {path}")
