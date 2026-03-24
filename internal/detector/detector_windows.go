//go:build windows

// Windows のアクティブウィンドウ取得。Win32 API を syscall 経由で呼び出す。
package detector

import (
	"strings"
	"syscall"
	"unsafe"
)

var (
	user32  = syscall.NewLazyDLL("user32.dll")
	psapi   = syscall.NewLazyDLL("psapi.dll")
	kernel32 = syscall.NewLazyDLL("kernel32.dll")

	procGetForegroundWindow      = user32.NewProc("GetForegroundWindow")
	procGetWindowTextW           = user32.NewProc("GetWindowTextW")
	procGetWindowTextLengthW     = user32.NewProc("GetWindowTextLengthW")
	procGetWindowThreadProcessId = user32.NewProc("GetWindowThreadProcessId")
	procOpenProcess              = kernel32.NewProc("OpenProcess")
	procCloseHandle              = kernel32.NewProc("CloseHandle")
	procGetModuleFileNameExW     = psapi.NewProc("GetModuleFileNameExW")
)

const (
	processQueryInformation = 0x0400
	processVMRead           = 0x0010
)

// GetActiveWindow は Windows でフォアグラウンドウィンドウの情報を返す。
func GetActiveWindow() (app, window string) {
	hwnd, _, _ := procGetForegroundWindow.Call()
	if hwnd == 0 {
		return "Unknown", ""
	}

	// ウィンドウタイトル取得
	length, _, _ := procGetWindowTextLengthW.Call(hwnd)
	if length > 0 {
		buf := make([]uint16, length+1)
		procGetWindowTextW.Call(hwnd, uintptr(unsafe.Pointer(&buf[0])), length+1)
		window = syscall.UTF16ToString(buf)
	}

	// プロセス名取得
	var pid uint32
	procGetWindowThreadProcessId.Call(hwnd, uintptr(unsafe.Pointer(&pid)))
	hProcess, _, _ := procOpenProcess.Call(
		processQueryInformation|processVMRead, 0, uintptr(pid),
	)
	if hProcess != 0 {
		defer procCloseHandle.Call(hProcess)
		buf := make([]uint16, 260)
		procGetModuleFileNameExW.Call(
			hProcess, 0, uintptr(unsafe.Pointer(&buf[0])), 260,
		)
		path := syscall.UTF16ToString(buf)
		parts := strings.Split(path, `\`)
		app = strings.TrimSuffix(parts[len(parts)-1], ".exe")
	}

	if app == "" {
		app = "Unknown"
	}
	return app, window
}
