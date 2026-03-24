// SQLite データベース操作。複数 goroutine から安全に使用できる。
package database

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"

	_ "modernc.org/sqlite"
)

const schema = `
CREATE TABLE IF NOT EXISTS events (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp        TEXT    NOT NULL,
    event_type       TEXT    NOT NULL DEFAULT 'app_switch',
    app_name         TEXT    NOT NULL DEFAULT 'Unknown',
    window_title     TEXT    DEFAULT '',
    duration_seconds REAL,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS daily_analysis (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    date          TEXT    NOT NULL,
    phase         TEXT    NOT NULL DEFAULT 'semantic',
    event_count   INTEGER DEFAULT 0,
    app_summary   TEXT,
    analysis_text TEXT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE(date, phase)
);

CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
`

// Event は events テーブルの1行を表す。
type Event struct {
	ID              int64
	Timestamp       string
	EventType       string
	AppName         string
	WindowTitle     string
	DurationSeconds float64
}

// DB はスレッドセーフな SQLite ラッパー。
type DB struct {
	db *sql.DB
	mu sync.Mutex
}

// Open はデータベースを開き、スキーマを初期化して返す。
func Open(path string) (*DB, error) {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return nil, fmt.Errorf("DB ディレクトリ作成失敗: %w", err)
	}
	sqlDB, err := sql.Open("sqlite", path+"?_journal_mode=WAL&_busy_timeout=5000")
	if err != nil {
		return nil, fmt.Errorf("DB オープン失敗: %w", err)
	}
	// SQLite は並列書き込み不可のため接続を1本に制限する
	sqlDB.SetMaxOpenConns(1)
	if _, err = sqlDB.Exec(schema); err != nil {
		return nil, fmt.Errorf("スキーマ初期化失敗: %w", err)
	}
	return &DB{db: sqlDB}, nil
}

// Close はデータベース接続を閉じる。
func (d *DB) Close() error { return d.db.Close() }

// ── イベント操作 ──────────────────────────────────────────────────────────────

// InsertEvent は新しいイベントを記録し、その ID を返す。
func (d *DB) InsertEvent(ts, eventType, appName, windowTitle string) (int64, error) {
	d.mu.Lock()
	defer d.mu.Unlock()
	res, err := d.db.Exec(
		`INSERT INTO events (timestamp, event_type, app_name, window_title)
		 VALUES (?, ?, ?, ?)`,
		ts, eventType, appName, windowTitle,
	)
	if err != nil {
		return 0, err
	}
	return res.LastInsertId()
}

// UpdateEventDuration は指定イベントの duration を更新する。
func (d *DB) UpdateEventDuration(id int64, seconds float64) error {
	d.mu.Lock()
	defer d.mu.Unlock()
	_, err := d.db.Exec(
		`UPDATE events SET duration_seconds = ? WHERE id = ?`,
		seconds, id,
	)
	return err
}

// GetEventsByDate は指定日（YYYY-MM-DD）のイベント一覧を返す。
func (d *DB) GetEventsByDate(date string) ([]Event, error) {
	rows, err := d.db.Query(
		`SELECT id, timestamp, event_type, app_name, window_title,
		        COALESCE(duration_seconds, 0)
		 FROM events WHERE date(timestamp) = ? ORDER BY timestamp`,
		date,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var events []Event
	for rows.Next() {
		var e Event
		if err := rows.Scan(
			&e.ID, &e.Timestamp, &e.EventType,
			&e.AppName, &e.WindowTitle, &e.DurationSeconds,
		); err != nil {
			return nil, err
		}
		events = append(events, e)
	}
	return events, rows.Err()
}

// GetTodayEvents は今日のイベントを返す。
func (d *DB) GetTodayEvents() ([]Event, error) {
	return d.GetEventsByDate(time.Now().Format("2006-01-02"))
}

// GetTodayEventCount は今日のイベント件数を返す。
func (d *DB) GetTodayEventCount() (int, error) {
	var n int
	err := d.db.QueryRow(
		`SELECT COUNT(*) FROM events WHERE date(timestamp) = date('now','localtime')`,
	).Scan(&n)
	return n, err
}

// GetAppSummary は指定日のアプリ別合計使用秒数を返す。
func (d *DB) GetAppSummary(date string) (map[string]float64, error) {
	rows, err := d.db.Query(
		`SELECT app_name, SUM(COALESCE(duration_seconds, 0))
		 FROM events WHERE date(timestamp) = ?
		 GROUP BY app_name ORDER BY 2 DESC`,
		date,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	result := make(map[string]float64)
	for rows.Next() {
		var app string
		var total float64
		if err := rows.Scan(&app, &total); err != nil {
			return nil, err
		}
		result[app] = total
	}
	return result, rows.Err()
}

// ── 分析結果操作 ──────────────────────────────────────────────────────────────

// SaveAnalysis は分析結果を UPSERT で保存する。再分析時も上書きされる。
func (d *DB) SaveAnalysis(date, phase, analysisText, appSummary string, eventCount int) error {
	d.mu.Lock()
	defer d.mu.Unlock()
	_, err := d.db.Exec(
		`INSERT INTO daily_analysis (date, phase, event_count, app_summary, analysis_text)
		 VALUES (?, ?, ?, ?, ?)
		 ON CONFLICT(date, phase) DO UPDATE SET
		     event_count   = excluded.event_count,
		     app_summary   = excluded.app_summary,
		     analysis_text = excluded.analysis_text,
		     created_at    = datetime('now','localtime')`,
		date, phase, eventCount, appSummary, analysisText,
	)
	return err
}

// GetAnalysis は指定日・フェーズの分析テキストを返す。存在しない場合は空文字。
func (d *DB) GetAnalysis(date, phase string) (string, error) {
	var text string
	err := d.db.QueryRow(
		`SELECT analysis_text FROM daily_analysis WHERE date = ? AND phase = ?`,
		date, phase,
	).Scan(&text)
	if err == sql.ErrNoRows {
		return "", nil
	}
	return text, err
}
