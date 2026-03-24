// アプリケーション設定。環境変数と既定値から生成する。
package config

import (
	"os"
	"strconv"
)

// Config はアプリ全体の設定値を保持する。
type Config struct {
	AnthropicAPIKey  string
	UseAnthropic     bool
	OllamaBaseURL    string
	OllamaModel      string
	RecordOnly       bool
	AnalysisHour     int
	AnalysisMinute   int
	DBPath           string
	PollIntervalSec  int
	IdleThresholdSec int
}

// Load は環境変数と既定値から Config を生成する。
func Load() *Config {
	return &Config{
		AnthropicAPIKey:  os.Getenv("ANTHROPIC_API_KEY"),
		UseAnthropic:     envBool("USE_ANTHROPIC", true),
		OllamaBaseURL:    envStr("OLLAMA_BASE_URL", "http://localhost:11434"),
		OllamaModel:      envStr("OLLAMA_MODEL", "llama3.2"),
		RecordOnly:       envBool("RECORD_ONLY", false),
		AnalysisHour:     envInt("ANALYSIS_HOUR", 0),
		AnalysisMinute:   envInt("ANALYSIS_MINUTE", 0),
		DBPath:           envStr("DB_PATH", "data/activity.db"),
		PollIntervalSec:  envInt("POLL_INTERVAL_SEC", 1),
		IdleThresholdSec: envInt("IDLE_THRESHOLD_SEC", 300),
	}
}

func envStr(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func envInt(key string, def int) int {
	if v := os.Getenv(key); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			return n
		}
	}
	return def
}

func envBool(key string, def bool) bool {
	v := os.Getenv(key)
	if v == "" {
		return def
	}
	b, err := strconv.ParseBool(v)
	if err != nil {
		return def
	}
	return b
}
