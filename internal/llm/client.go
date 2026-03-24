// LLM バックエンド統合（Anthropic API / Ollama）。
package llm

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/Hari-Nezu/AISupportSuggest/internal/config"
)

// Client は LLM バックエンドへの統合クライアント。
type Client struct {
	cfg  *config.Config
	http *http.Client
}

// New は新しい LLM クライアントを返す。
func New(cfg *config.Config) *Client {
	return &Client{
		cfg:  cfg,
		http: &http.Client{Timeout: 180 * time.Second},
	}
}

// Query はプロンプトを送信し、レスポンステキストを返す。
func (c *Client) Query(prompt string) (string, error) {
	if c.cfg.UseAnthropic && c.cfg.AnthropicAPIKey != "" {
		return c.queryAnthropic(prompt)
	}
	return c.queryOllama(prompt)
}

// ── Anthropic ─────────────────────────────────────────────────────────────────

type anthropicReq struct {
	Model     string    `json:"model"`
	MaxTokens int       `json:"max_tokens"`
	Messages  []message `json:"messages"`
}

type message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type anthropicResp struct {
	Content []struct {
		Text string `json:"text"`
	} `json:"content"`
	Error *struct {
		Message string `json:"message"`
	} `json:"error,omitempty"`
}

func (c *Client) queryAnthropic(prompt string) (string, error) {
	body, _ := json.Marshal(anthropicReq{
		Model:     "claude-sonnet-4-6",
		MaxTokens: 2048,
		Messages:  []message{{Role: "user", Content: prompt}},
	})
	req, err := http.NewRequest("POST", "https://api.anthropic.com/v1/messages", bytes.NewReader(body))
	if err != nil {
		return "", err
	}
	req.Header.Set("x-api-key", c.cfg.AnthropicAPIKey)
	req.Header.Set("anthropic-version", "2023-06-01")
	req.Header.Set("content-type", "application/json")

	resp, err := c.http.Do(req)
	if err != nil {
		return "", fmt.Errorf("Anthropic API 通信エラー: %w", err)
	}
	defer resp.Body.Close()

	data, _ := io.ReadAll(resp.Body)
	var result anthropicResp
	if err := json.Unmarshal(data, &result); err != nil {
		return "", fmt.Errorf("Anthropic レスポンス解析失敗: %w", err)
	}
	if result.Error != nil {
		return "", fmt.Errorf("Anthropic API エラー: %s", result.Error.Message)
	}
	if len(result.Content) == 0 {
		return "", fmt.Errorf("Anthropic: 空のレスポンス")
	}
	return result.Content[0].Text, nil
}

// ── Ollama ─────────────────────────────────────────────────────────────────────

type ollamaReq struct {
	Model  string `json:"model"`
	Prompt string `json:"prompt"`
	Stream bool   `json:"stream"`
}

type ollamaResp struct {
	Response string `json:"response"`
}

func (c *Client) queryOllama(prompt string) (string, error) {
	body, _ := json.Marshal(ollamaReq{
		Model:  c.cfg.OllamaModel,
		Prompt: prompt,
		Stream: false,
	})
	resp, err := c.http.Post(
		c.cfg.OllamaBaseURL+"/api/generate",
		"application/json",
		bytes.NewReader(body),
	)
	if err != nil {
		return "", fmt.Errorf("Ollama に接続できません。`ollama serve` を実行してから再試行してください。")
	}
	defer resp.Body.Close()

	data, _ := io.ReadAll(resp.Body)
	var result ollamaResp
	if err := json.Unmarshal(data, &result); err != nil {
		return "", fmt.Errorf("Ollama レスポンス解析失敗: %w", err)
	}
	return result.Response, nil
}
