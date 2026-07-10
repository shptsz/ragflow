//
//  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
//
//  Licensed under the Apache License, Version 2.0 (the "License");
//  you may not use this file except in compliance with the License.
//  You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.
//

package common

import (
	"fmt"
	"strings"
)

// 访问级别常量，与 Python api.db.AccessLevel 对齐
const (
	AccessLevelFull   = "full"
	AccessLevelKBOnly = "kb_only"
)

var readOnlyMethods = map[string]struct{}{
	"GET":     {},
	"HEAD":    {},
	"OPTIONS": {},
}

// kb_only 用户允许访问的路径前缀（知识库域 + 登录/基础系统接口）
var kbOnlyAllowPrefixes = []string{
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
	"/v1/system/healthz",
}

// 精确匹配：个人资料、公开系统配置、遗留上传接口等
// （避免 /system/config 前缀误放行 /configs 或 /config/log）
var kbOnlyExactPaths = map[string]map[string]struct{}{
	"/api/v1/users/me": {
		"GET":     {},
		"HEAD":    {},
		"OPTIONS": {},
		"PATCH":   {},
	},
	"/api/v1/system/config": {
		"GET":     {},
		"HEAD":    {},
		"OPTIONS": {},
	},
	"/v1/document/upload_info": {
		"POST": {},
	},
}

// 仅允许只读方法访问的路径（知识库配置所需的模型列表）
var kbOnlyReadOnlyPaths = map[string]struct{}{
	"/api/v1/models":         {},
	"/api/v1/models/default": {},
}

// NormalizeAccessLevel 将空值或其他未知值归一为 full；仅 kb_only 为受限级别。
func NormalizeAccessLevel(value string) string {
	if value == AccessLevelKBOnly {
		return AccessLevelKBOnly
	}
	return AccessLevelFull
}

func normalizePath(path string) string {
	if i := strings.IndexByte(path, '?'); i >= 0 {
		path = path[:i]
	}
	path = strings.TrimRight(path, "/")
	if path == "" {
		return "/"
	}
	return path
}

// IsPathAllowedForKbOnly 判断 kb_only 用户是否可访问指定 method+path。
// 默认拒绝；仅白名单路径放行。
func IsPathAllowedForKbOnly(method, path string) bool {
	method = strings.ToUpper(method)
	path = normalizePath(path)

	if methods, ok := kbOnlyExactPaths[path]; ok {
		if _, ok := methods[method]; ok {
			return true
		}
	}

	if _, ok := readOnlyMethods[method]; ok {
		if _, ok := kbOnlyReadOnlyPaths[path]; ok {
			return true
		}
	}

	for _, prefix := range kbOnlyAllowPrefixes {
		trimmed := strings.TrimRight(prefix, "/")
		if path == trimmed || strings.HasPrefix(path, prefix) {
			return true
		}
	}

	return false
}

// EnsureRequestAllowed 校验访问级别是否允许该请求；full 用户直接放行。
func EnsureRequestAllowed(accessLevel, method, path string) error {
	if NormalizeAccessLevel(accessLevel) != AccessLevelKBOnly {
		return nil
	}
	if !IsPathAllowedForKbOnly(method, path) {
		return fmt.Errorf("kb_only 用户无权访问 %s %s", strings.ToUpper(method), path)
	}
	return nil
}
