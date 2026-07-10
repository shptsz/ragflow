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

import re

from api.db import AccessLevel


class AccessDeniedError(Exception):
    """kb_only 用户访问了未授权模块。"""


_READ_ONLY_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

# kb_only 用户允许访问的路径前缀（知识库域 + 团队 + 登录/基础系统接口）
_KB_ONLY_ALLOW_PREFIXES: tuple[str, ...] = (
    "/api/v1/datasets",
    "/api/v1/documents",
    "/api/v1/retrieval",
    "/api/v1/thumbnails",
    "/api/v1/tasks",
    "/api/v1/files/link-to-datasets",
    "/api/v1/tenants",
    "/api/v1/auth/",
    "/api/v1/system/ping",
    "/api/v1/system/version",
    "/api/v1/system/healthz",
    "/api/v1/system/status",
    "/v1/system/healthz",
)

# 精确匹配：个人资料、公开系统配置、遗留上传接口等（避免 /system/config 前缀误放行 configs/log）
_KB_ONLY_EXACT_PATHS: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/api/v1/users/me"),
        ("HEAD", "/api/v1/users/me"),
        ("OPTIONS", "/api/v1/users/me"),
        ("PATCH", "/api/v1/users/me"),
        # 登录后拉取租户默认模型（只读）；禁止 PATCH 改模型配置
        ("GET", "/api/v1/users/me/models"),
        ("HEAD", "/api/v1/users/me/models"),
        ("OPTIONS", "/api/v1/users/me/models"),
        ("GET", "/api/v1/system/config"),
        ("HEAD", "/api/v1/system/config"),
        ("OPTIONS", "/api/v1/system/config"),
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

# 知识库本体资源：/api/v1/datasets/<id>（不含更深子路径）
_DATASET_RESOURCE_RE = re.compile(r"^/api/v1/datasets/[^/]+$")


def normalize_access_level(value: str | None) -> str:
    if value == AccessLevel.KB_ONLY:
        return AccessLevel.KB_ONLY
    return AccessLevel.FULL


def _normalize_path(path: str) -> str:
    return path.split("?", 1)[0].rstrip("/") or "/"


def _is_dataset_resource_mutation(method: str, path: str) -> bool:
    """kb_only 禁止创建/删除/改配置知识库本体；文档等子资源仍放行。"""
    if path == "/api/v1/datasets" and method in {"POST", "DELETE"}:
        return True
    if _DATASET_RESOURCE_RE.match(path) and method in {"POST", "PUT", "PATCH", "DELETE"}:
        return True
    return False


def is_path_allowed_for_kb_only(method: str, path: str) -> bool:
    method = method.upper()
    path = _normalize_path(path)

    if _is_dataset_resource_mutation(method, path):
        return False

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
