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

import "testing"

func TestNormalizeAccessLevel(t *testing.T) {
	cases := []struct {
		in, want string
	}{
		{"", AccessLevelFull},
		{"full", AccessLevelFull},
		{"kb_only", AccessLevelKBOnly},
		{"other", AccessLevelFull},
		{"KB_ONLY", AccessLevelFull},
	}
	for _, tc := range cases {
		if got := NormalizeAccessLevel(tc.in); got != tc.want {
			t.Errorf("NormalizeAccessLevel(%q) = %q, want %q", tc.in, got, tc.want)
		}
	}
}

func TestIsPathAllowedForKbOnly_AllowDatasetsAndProfile(t *testing.T) {
	allowed := []struct{ method, path string }{
		{"GET", "/api/v1/datasets"},
		{"POST", "/api/v1/datasets"},
		{"GET", "/api/v1/datasets/abc/documents"},
		{"GET", "/api/v1/users/me"},
		{"PATCH", "/api/v1/users/me"},
		{"GET", "/api/v1/system/ping"},
		{"POST", "/v1/document/upload_info"},
		{"GET", "/api/v1/auth/login"},
	}
	for _, tc := range allowed {
		if !IsPathAllowedForKbOnly(tc.method, tc.path) {
			t.Errorf("expected allow %s %s", tc.method, tc.path)
		}
	}
}

func TestIsPathAllowedForKbOnly_DenyChats(t *testing.T) {
	denied := []struct{ method, path string }{
		{"GET", "/api/v1/chats"},
		{"POST", "/api/v1/chats"},
		{"GET", "/api/v1/agents"},
		{"GET", "/api/v1/users/me/extra"},
	}
	for _, tc := range denied {
		if IsPathAllowedForKbOnly(tc.method, tc.path) {
			t.Errorf("expected deny %s %s", tc.method, tc.path)
		}
	}
}

func TestIsPathAllowedForKbOnly_ReadOnlyModels(t *testing.T) {
	if !IsPathAllowedForKbOnly("GET", "/api/v1/models") {
		t.Error("expected allow GET /api/v1/models")
	}
	if !IsPathAllowedForKbOnly("HEAD", "/api/v1/models/default") {
		t.Error("expected allow HEAD /api/v1/models/default")
	}
	if IsPathAllowedForKbOnly("POST", "/api/v1/models") {
		t.Error("expected deny POST /api/v1/models")
	}
	if IsPathAllowedForKbOnly("PUT", "/api/v1/models/default") {
		t.Error("expected deny PUT /api/v1/models/default")
	}
}

func TestIsPathAllowedForKbOnly_DenyDownloadPath(t *testing.T) {
	// 非白名单下载路径应拒绝（/api/v1/documents 前缀内的下载仍放行）
	denied := []struct{ method, path string }{
		{"GET", "/v1/document/get"},
		{"GET", "/api/v1/files/download"},
		{"GET", "/api/v1/file/download"},
	}
	for _, tc := range denied {
		if IsPathAllowedForKbOnly(tc.method, tc.path) {
			t.Errorf("expected deny %s %s", tc.method, tc.path)
		}
	}
}

func TestIsPathAllowedForKbOnly_SystemConfigExact(t *testing.T) {
	if !IsPathAllowedForKbOnly("GET", "/api/v1/system/config") {
		t.Error("expected allow GET /api/v1/system/config")
	}
	// 前缀过宽会误放行 configs / config/log
	denied := []struct{ method, path string }{
		{"GET", "/api/v1/system/configs"},
		{"GET", "/api/v1/system/config/log"},
		{"PUT", "/api/v1/system/config/log"},
	}
	for _, tc := range denied {
		if IsPathAllowedForKbOnly(tc.method, tc.path) {
			t.Errorf("expected deny %s %s", tc.method, tc.path)
		}
	}
}

func TestEnsureRequestAllowed(t *testing.T) {
	if err := EnsureRequestAllowed("full", "GET", "/api/v1/chats"); err != nil {
		t.Errorf("full user should pass: %v", err)
	}
	if err := EnsureRequestAllowed("", "GET", "/api/v1/chats"); err != nil {
		t.Errorf("empty access_level should pass as full: %v", err)
	}
	if err := EnsureRequestAllowed("kb_only", "GET", "/api/v1/datasets"); err != nil {
		t.Errorf("kb_only datasets should pass: %v", err)
	}
	if err := EnsureRequestAllowed("kb_only", "GET", "/api/v1/chats"); err == nil {
		t.Error("kb_only chats should be denied")
	}
}
