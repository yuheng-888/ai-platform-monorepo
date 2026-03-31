package executor

import (
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/router-for-me/CLIProxyAPI/v6/internal/config"
	cliproxyauth "github.com/router-for-me/CLIProxyAPI/v6/sdk/cliproxy/auth"
	cliproxyexecutor "github.com/router-for-me/CLIProxyAPI/v6/sdk/cliproxy/executor"
	sdktranslator "github.com/router-for-me/CLIProxyAPI/v6/sdk/translator"
)

func TestOpenAICompatExecutorGeminiBusinessPassesForcedAccountHeader(t *testing.T) {
	var gotAuthorization string
	var gotForcedAccountID string
	var gotPath string

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotAuthorization = r.Header.Get("Authorization")
		gotForcedAccountID = r.Header.Get("X-Gemini-Account-ID")
		gotPath = r.URL.Path
		_, _ = io.ReadAll(r.Body)
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"id":"chatcmpl-1","object":"chat.completion","choices":[{"index":0,"message":{"role":"assistant","content":"ok"},"finish_reason":"stop"}]}`))
	}))
	defer server.Close()

	exec := NewOpenAICompatExecutor("gemini-business", &config.Config{})
	auth := &cliproxyauth.Auth{
		Provider: "gemini-business",
		Attributes: map[string]string{
			"base_url":                   server.URL + "/gemini/v1",
			"api_key":                    "gemini-admin-key",
			"header:X-Gemini-Account-ID": "gemini-account-1",
		},
	}

	_, err := exec.Execute(
		context.Background(),
		auth,
		cliproxyexecutor.Request{
			Model:   "gemini-2.5-pro",
			Payload: []byte(`{"model":"gemini-2.5-pro","messages":[{"role":"user","content":"hi"}]}`),
		},
		cliproxyexecutor.Options{
			SourceFormat: sdktranslator.FromString("openai"),
			Stream:       false,
		},
	)
	if err != nil {
		t.Fatalf("Execute error: %v", err)
	}

	if gotAuthorization != "Bearer gemini-admin-key" {
		t.Fatalf("authorization = %q, want %q", gotAuthorization, "Bearer gemini-admin-key")
	}
	if gotForcedAccountID != "gemini-account-1" {
		t.Fatalf("forced account header = %q, want %q", gotForcedAccountID, "gemini-account-1")
	}
	if gotPath != "/gemini/v1/chat/completions" {
		t.Fatalf("path = %q, want %q", gotPath, "/gemini/v1/chat/completions")
	}
}
