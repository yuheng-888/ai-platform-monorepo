package util

import "strings"

var projectedAuthMetadataKeys = map[string]struct{}{
	"api_key":      {},
	"auth_kind":    {},
	"base_url":     {},
	"compat_name":  {},
	"email":        {},
	"provider_key": {},
}

// MergeAuthMetadataAttributes projects selected auth JSON metadata fields into
// runtime attributes so executors can consume file-uploaded credentials in the
// same shape as config-generated credentials.
func MergeAuthMetadataAttributes(dst map[string]string, metadata map[string]any) map[string]string {
	if dst == nil {
		dst = make(map[string]string)
	}
	if len(metadata) == 0 {
		return dst
	}
	for key, rawValue := range metadata {
		trimmedKey := strings.TrimSpace(key)
		if trimmedKey == "" {
			continue
		}
		lowerKey := strings.ToLower(trimmedKey)
		_, allowed := projectedAuthMetadataKeys[lowerKey]
		if !allowed && !strings.HasPrefix(lowerKey, "header:") {
			continue
		}
		stringValue, ok := rawValue.(string)
		if !ok {
			continue
		}
		trimmedValue := strings.TrimSpace(stringValue)
		if trimmedValue == "" {
			continue
		}
		dst[trimmedKey] = trimmedValue
	}
	return dst
}
