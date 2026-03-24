// アクティブウィンドウを監視し、変化を DB に記録する。
// GetActiveWindow はプラットフォームごとに detector_darwin.go / detector_windows.go で実装する。
package detector

import (
	"sync"
	"time"

	"github.com/Hari-Nezu/AISupportSuggest/internal/database"
)

// EventDetector はポーリングループでアクティブウィンドウを監視する。
type EventDetector struct {
	db           *database.DB
	pollInterval time.Duration
	idleLimit    time.Duration

	mu            sync.Mutex
	stop          chan struct{}
	currentApp    string
	currentWindow string
	stateStart    time.Time
	lastEventID   int64
	idle          bool
	noChangeSec   float64
}

// New は新しい EventDetector を返す。
func New(db *database.DB, pollIntervalSec, idleThresholdSec int) *EventDetector {
	return &EventDetector{
		db:           db,
		pollInterval: time.Duration(pollIntervalSec) * time.Second,
		idleLimit:    time.Duration(idleThresholdSec) * time.Second,
		stop:         make(chan struct{}),
	}
}

// Start は監視ループを goroutine で起動する。
func (d *EventDetector) Start() {
	go d.run()
}

// Stop は監視を停止し、最後のイベントの duration を確定させる。
func (d *EventDetector) Stop() {
	close(d.stop)
	d.closeCurrentEvent()
}

func (d *EventDetector) run() {
	ticker := time.NewTicker(d.pollInterval)
	defer ticker.Stop()
	for {
		select {
		case <-d.stop:
			return
		case <-ticker.C:
			_ = d.tick()
		}
	}
}

func (d *EventDetector) tick() error {
	app, window := GetActiveWindow()
	now := time.Now()
	ts := now.Format("2006-01-02T15:04:05")

	d.mu.Lock()
	defer d.mu.Unlock()

	appChanged := app != d.currentApp
	winChanged := window != d.currentWindow

	if !appChanged && !winChanged {
		// 状態変化なし → idle チェック
		d.noChangeSec += d.pollInterval.Seconds()
		if !d.idle && d.noChangeSec >= d.idleLimit.Seconds() {
			d.idle = true
			d.closeCurrentEventLocked()
			id, err := d.db.InsertEvent(ts, "idle_start", app, window)
			if err != nil {
				return err
			}
			d.lastEventID = id
			d.stateStart = now
		}
		return nil
	}

	// idle から復帰
	if d.idle {
		d.idle = false
		d.closeCurrentEventLocked()
		_, _ = d.db.InsertEvent(ts, "idle_end", app, window)
	}

	d.noChangeSec = 0
	d.closeCurrentEventLocked()

	eventType := "window_change"
	if appChanged {
		eventType = "app_switch"
	}

	id, err := d.db.InsertEvent(ts, eventType, app, window)
	if err != nil {
		return err
	}
	d.lastEventID = id
	d.currentApp = app
	d.currentWindow = window
	d.stateStart = now
	return nil
}

func (d *EventDetector) closeCurrentEvent() {
	d.mu.Lock()
	defer d.mu.Unlock()
	d.closeCurrentEventLocked()
}

// closeCurrentEventLocked は mu を保持した状態で呼び出すこと。
func (d *EventDetector) closeCurrentEventLocked() {
	if d.lastEventID == 0 || d.stateStart.IsZero() {
		return
	}
	dur := time.Since(d.stateStart).Seconds()
	_ = d.db.UpdateEventDuration(d.lastEventID, dur)
	d.lastEventID = 0
	d.stateStart = time.Time{}
}
