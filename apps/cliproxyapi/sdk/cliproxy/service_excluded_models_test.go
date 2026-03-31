package cliproxy

import (
	"strings"
	"testing"

	"github.com/router-for-me/CLIProxyAPI/v6/internal/registry"
	coreauth "github.com/router-for-me/CLIProxyAPI/v6/sdk/cliproxy/auth"
	"github.com/router-for-me/CLIProxyAPI/v6/sdk/config"
)

func TestRegisterModelsForAuth_UsesPreMergedExcludedModelsAttribute(t *testing.T) {
	service := &Service{
		cfg: &config.Config{
			OAuthExcludedModels: map[string][]string{
				"gemini-cli": {"gemini-2.5-pro"},
			},
		},
	}
	auth := &coreauth.Auth{
		ID:       "auth-gemini-cli",
		Provider: "gemini-cli",
		Status:   coreauth.StatusActive,
		Attributes: map[string]string{
			"auth_kind":       "oauth",
			"excluded_models": "gemini-2.5-flash",
		},
	}

	registry := GlobalModelRegistry()
	registry.UnregisterClient(auth.ID)
	t.Cleanup(func() {
		registry.UnregisterClient(auth.ID)
	})

	service.registerModelsForAuth(auth)

	models := registry.GetAvailableModelsByProvider("gemini-cli")
	if len(models) == 0 {
		t.Fatal("expected gemini-cli models to be registered")
	}

	for _, model := range models {
		if model == nil {
			continue
		}
		modelID := strings.TrimSpace(model.ID)
		if strings.EqualFold(modelID, "gemini-2.5-flash") {
			t.Fatalf("expected model %q to be excluded by auth attribute", modelID)
		}
	}

	seenGlobalExcluded := false
	for _, model := range models {
		if model == nil {
			continue
		}
		if strings.EqualFold(strings.TrimSpace(model.ID), "gemini-2.5-pro") {
			seenGlobalExcluded = true
			break
		}
	}
	if !seenGlobalExcluded {
		t.Fatal("expected global excluded model to be present when attribute override is set")
	}
}

func TestRegisterModelsForAuth_GeminiBusinessUsesGeminiCLIModels(t *testing.T) {
	service := &Service{cfg: &config.Config{}}
	auth := &coreauth.Auth{
		ID:       "auth-gemini-business",
		Provider: "gemini-business",
		Status:   coreauth.StatusActive,
		Attributes: map[string]string{
			"auth_kind": "api_key",
			"api_key":   "gemini-admin-key",
			"base_url":  "http://127.0.0.1:39001/gemini/v1",
		},
	}

	globalRegistry := registry.GetGlobalRegistry()
	globalRegistry.UnregisterClient(auth.ID)
	t.Cleanup(func() {
		globalRegistry.UnregisterClient(auth.ID)
	})

	service.registerModelsForAuth(auth)

	models := globalRegistry.GetModelsForClient(auth.ID)
	if len(models) == 0 {
		t.Fatal("expected gemini-business models to be registered")
	}

	available := globalRegistry.GetAvailableModelsByProvider("gemini-business")
	if len(available) == 0 {
		t.Fatal("expected gemini-business provider models to be queryable")
	}

	expected := registry.GetGeminiCLIModels()
	if len(expected) == 0 {
		t.Fatal("expected static gemini-cli models to exist")
	}

	if strings.TrimSpace(models[0].ID) == "" {
		t.Fatal("expected first gemini-business model to have an id")
	}
}

func TestRegisterModelsForAuth_GeminiBusinessWithoutAPIAttrsStillUsesGeminiCLIModels(t *testing.T) {
	service := &Service{cfg: &config.Config{}}
	auth := &coreauth.Auth{
		ID:       "auth-gemini-business-minimal",
		Provider: "gemini-business",
		Status:   coreauth.StatusActive,
		Metadata: map[string]any{
			"email": "gemini-business@example.com",
		},
	}

	globalRegistry := registry.GetGlobalRegistry()
	globalRegistry.UnregisterClient(auth.ID)
	t.Cleanup(func() {
		globalRegistry.UnregisterClient(auth.ID)
	})

	service.registerModelsForAuth(auth)

	models := globalRegistry.GetModelsForClient(auth.ID)
	if len(models) == 0 {
		t.Fatal("expected gemini-business models to be registered for minimal auth payload")
	}
}
