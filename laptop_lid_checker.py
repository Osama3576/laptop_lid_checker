import ctypes
import queue
import sys
import threading
import traceback
import uuid
import winreg
from ctypes import wintypes
from pathlib import Path

from PySide6.QtCore import QPoint, QRectF, QSettings, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QWidget


# -----------------------------
# App settings
# -----------------------------
APP_NAME = "Lid State Banner"
STARTUP_VALUE_NAME = "LidStateBanner"
DEFAULT_X = 24
DEFAULT_Y = 24
AUTO_ENABLE_STARTUP = True


# -----------------------------
# Win32 constants
# -----------------------------
WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_POWERBROADCAST = 0x0218
PBT_POWERSETTINGCHANGE = 0x8013
DEVICE_NOTIFY_WINDOW_HANDLE = 0x00000000
CS_VREDRAW = 0x0001
CS_HREDRAW = 0x0002


# -----------------------------
# Win32 type helpers
# -----------------------------
HANDLE = wintypes.HANDLE
HINSTANCE = HANDLE
HMODULE = HANDLE
HICON = HANDLE
HCURSOR = HANDLE
HBRUSH = HANDLE
HMENU = HANDLE
LPVOID = ctypes.c_void_p

if ctypes.sizeof(ctypes.c_void_p) == ctypes.sizeof(ctypes.c_longlong):
    LONG_PTR = ctypes.c_longlong
else:
    LONG_PTR = ctypes.c_long

LRESULT = LONG_PTR
WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)


# -----------------------------
# Win32 structures
# -----------------------------
class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class POWERBROADCAST_SETTING(ctypes.Structure):
    _fields_ = [
        ("PowerSetting", GUID),
        ("DataLength", wintypes.DWORD),
        ("Data", ctypes.c_ubyte * 1),
    ]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", HINSTANCE),
        ("hIcon", HICON),
        ("hCursor", HCURSOR),
        ("hbrBackground", HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_long),
        ("y", ctypes.c_long),
    ]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", POINT),
    ]


# -----------------------------
# Win32 setup
# -----------------------------
user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

RegisterClassW = user32.RegisterClassW
RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
RegisterClassW.restype = ctypes.c_ushort

CreateWindowExW = user32.CreateWindowExW
CreateWindowExW.argtypes = [
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    HMENU,
    HINSTANCE,
    LPVOID,
]
CreateWindowExW.restype = wintypes.HWND

DefWindowProcW = user32.DefWindowProcW
DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
DefWindowProcW.restype = LRESULT

DestroyWindow = user32.DestroyWindow
DestroyWindow.argtypes = [wintypes.HWND]
DestroyWindow.restype = wintypes.BOOL

PostMessageW = user32.PostMessageW
PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
PostMessageW.restype = wintypes.BOOL

GetMessageW = user32.GetMessageW
GetMessageW.argtypes = [ctypes.POINTER(MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
GetMessageW.restype = ctypes.c_int

TranslateMessage = user32.TranslateMessage
TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
TranslateMessage.restype = wintypes.BOOL

DispatchMessageW = user32.DispatchMessageW
DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
DispatchMessageW.restype = LRESULT

PostQuitMessage = user32.PostQuitMessage
PostQuitMessage.argtypes = [ctypes.c_int]
PostQuitMessage.restype = None

RegisterPowerSettingNotification = user32.RegisterPowerSettingNotification
RegisterPowerSettingNotification.argtypes = [
    HANDLE,
    ctypes.POINTER(GUID),
    wintypes.DWORD,
]
RegisterPowerSettingNotification.restype = HANDLE

UnregisterPowerSettingNotification = user32.UnregisterPowerSettingNotification
UnregisterPowerSettingNotification.argtypes = [HANDLE]
UnregisterPowerSettingNotification.restype = wintypes.BOOL

GetModuleHandleW = kernel32.GetModuleHandleW
GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
GetModuleHandleW.restype = HMODULE


# -----------------------------
# Startup helpers
# -----------------------------
def get_script_path() -> Path:
    """Return the current script file path."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return Path(__file__).resolve()


def get_launch_command() -> str:
    """Build the best launch command for Windows startup."""
    script_path = get_script_path()

    if getattr(sys, "frozen", False):
        return f'"{script_path}"'

    current_python = Path(sys.executable).resolve()
    pythonw_path = current_python.with_name("pythonw.exe")
    python_to_use = pythonw_path if pythonw_path.exists() else current_python

    return f'"{python_to_use}" "{script_path}"'


def enable_startup() -> None:
    """Register the app under HKCU Run so it starts when the user logs in."""
    command = get_launch_command()
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        winreg.SetValueEx(key, STARTUP_VALUE_NAME, 0, winreg.REG_SZ, command)


# -----------------------------
# Utility helpers
# -----------------------------
def guid_from_string(guid_text: str) -> GUID:
    """Convert a GUID string into a Win32 GUID structure."""
    parsed = uuid.UUID(guid_text)
    guid = GUID()
    guid.Data1 = parsed.fields[0]
    guid.Data2 = parsed.fields[1]
    guid.Data3 = parsed.fields[2]
    tail = parsed.bytes[8:]
    for index, value in enumerate(tail):
        guid.Data4[index] = value
    return guid


def guid_equals(left: GUID, right: GUID) -> bool:
    """Compare two GUID structures using their raw bytes."""
    return bytes(left) == bytes(right)


GUID_LIDSWITCH_STATE_CHANGE = guid_from_string("BA3E0F4D-B817-4094-A2D1-D56379E6A0F3")


class LidMonitorThread(threading.Thread):
    """Background thread with a hidden native window for lid notifications."""

    def __init__(self, output_queue: queue.Queue):
        super().__init__(daemon=True)
        self.output_queue = output_queue
        self.class_name = f"LidMonitorWindow_{uuid.uuid4()}"
        self.hinstance = GetModuleHandleW(None)
        self.hwnd = None
        self.notify_handle = None
        self._wndproc_ref = None
        self._started_event = threading.Event()
        self._stopped = False

    def run(self) -> None:
        """Create the hidden window and process lid notification messages."""
        try:
            self._create_hidden_window()
            self._started_event.set()

            msg = MSG()
            while not self._stopped:
                result = GetMessageW(ctypes.byref(msg), None, 0, 0)
                if result == -1:
                    raise ctypes.WinError(ctypes.get_last_error())
                if result == 0:
                    break
                TranslateMessage(ctypes.byref(msg))
                DispatchMessageW(ctypes.byref(msg))
        except Exception:
            self.output_queue.put(("ERROR", traceback.format_exc()))
            self._started_event.set()

    def _create_hidden_window(self) -> None:
        """Register a native class and create the hidden listener window."""
        self._wndproc_ref = WNDPROC(self._window_proc)

        wndclass = WNDCLASSW()
        wndclass.style = CS_HREDRAW | CS_VREDRAW
        wndclass.lpfnWndProc = self._wndproc_ref
        wndclass.cbClsExtra = 0
        wndclass.cbWndExtra = 0
        wndclass.hInstance = self.hinstance
        wndclass.hIcon = None
        wndclass.hCursor = None
        wndclass.hbrBackground = None
        wndclass.lpszMenuName = None
        wndclass.lpszClassName = self.class_name

        atom = RegisterClassW(ctypes.byref(wndclass))
        if not atom:
            raise ctypes.WinError(ctypes.get_last_error())

        self.hwnd = CreateWindowExW(
            0,
            self.class_name,
            self.class_name,
            0,
            0,
            0,
            0,
            0,
            None,
            None,
            self.hinstance,
            None,
        )
        if not self.hwnd:
            raise ctypes.WinError(ctypes.get_last_error())

        self.notify_handle = RegisterPowerSettingNotification(
            self.hwnd,
            ctypes.byref(GUID_LIDSWITCH_STATE_CHANGE),
            DEVICE_NOTIFY_WINDOW_HANDLE,
        )
        if not self.notify_handle:
            raise ctypes.WinError(ctypes.get_last_error())

        # Use a practical default state until the first lid event arrives.
        self.output_queue.put(("STATE_TEXT", "Open"))

    def _window_proc(self, hwnd, msg, wparam, lparam):
        """Receive lid notifications and forward state changes to the UI."""
        if msg == WM_POWERBROADCAST and wparam == PBT_POWERSETTINGCHANGE and lparam:
            settings = ctypes.cast(lparam, ctypes.POINTER(POWERBROADCAST_SETTING)).contents
            if guid_equals(settings.PowerSetting, GUID_LIDSWITCH_STATE_CHANGE):
                base_addr = ctypes.cast(lparam, ctypes.c_void_p).value
                data_addr = base_addr + POWERBROADCAST_SETTING.Data.offset
                state_value = ctypes.cast(data_addr, ctypes.POINTER(wintypes.DWORD)).contents.value
                self.output_queue.put(("STATE", state_value))
                return 1

        if msg == WM_CLOSE:
            if self.notify_handle:
                UnregisterPowerSettingNotification(self.notify_handle)
                self.notify_handle = None
            DestroyWindow(hwnd)
            return 0

        if msg == WM_DESTROY:
            PostQuitMessage(0)
            return 0

        return DefWindowProcW(hwnd, msg, wparam, lparam)

    def wait_until_ready(self, timeout: float = 5.0) -> None:
        """Wait until the hidden listener window is ready."""
        self._started_event.wait(timeout)

    def stop(self) -> None:
        """Stop the message loop and close the hidden listener window."""
        self._stopped = True
        if self.hwnd:
            PostMessageW(self.hwnd, WM_CLOSE, 0, 0)


class LidBanner(QWidget):
    """Small floating widget that shows the laptop lid state."""

    def __init__(self) -> None:
        super().__init__()

        self.widget_width = 70
        self.widget_height = 30
        self.corner_radius = 14

        self.colors = {
            "background": QColor("#f8fafc"),
            "border": QColor("#cbd5e1"),
            "text": QColor("#334155"),
            "open": QColor("#22c55e"),
            "close": QColor("#fb7185"),
            "unknown": QColor("#f59e0b"),
        }

        self.state_text = "Open"
        self.dot_color = self.colors["open"]

        self.drag_offset = QPoint()
        self.is_dragging = False

        self.settings = QSettings("LidStateBanner", "LidStateBanner")

        self.queue = queue.Queue()
        self.monitor = LidMonitorThread(self.queue)

        self._configure_window()
        self._restore_position()

        self.monitor.start()
        self.monitor.wait_until_ready(timeout=5.0)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll_queue)
        self.timer.start(120)

        if AUTO_ENABLE_STARTUP:
            try:
                enable_startup()
            except Exception:
                pass

    def _configure_window(self) -> None:
        """Configure the frameless always-on-top floating window."""
        self.setWindowTitle(APP_NAME)
        self.setFixedSize(self.widget_width, self.widget_height)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

    def _restore_position(self) -> None:
        """Restore the saved widget position."""
        x = self.settings.value("x", DEFAULT_X, int)
        y = self.settings.value("y", DEFAULT_Y, int)
        self.move(x, y)

    def _save_position(self) -> None:
        """Save the current widget position."""
        self.settings.setValue("x", self.x())
        self.settings.setValue("y", self.y())
        self.settings.sync()

    def _set_state(self, text: str, dot_color: QColor) -> None:
        """Update the visible state label and dot color."""
        self.state_text = text
        self.dot_color = dot_color
        self.update()

    def _poll_queue(self) -> None:
        """Pull updates from the monitor thread and refresh the UI."""
        try:
            while True:
                item_type, payload = self.queue.get_nowait()
                if item_type == "STATE":
                    if payload == 1:
                        self._set_state("Open", self.colors["open"])
                    elif payload == 0:
                        self._set_state("Close", self.colors["close"])
                    else:
                        self._set_state("UNKNOWN", self.colors["unknown"])
                elif item_type == "STATE_TEXT":
                    if payload == "OPEN":
                        self._set_state("OPEN", self.colors["open"])
                    else:
                        self._set_state(payload, self.colors["unknown"])
                elif item_type == "ERROR":
                    self._set_state("ERROR", self.colors["close"])
                    print(payload)
        except queue.Empty:
            pass

    def paintEvent(self, event) -> None:
        """Paint the rounded widget body, centered status dot, and centered label."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        body_rect = QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0)
        path = QPainterPath()
        path.addRoundedRect(body_rect, self.corner_radius, self.corner_radius)

        painter.fillPath(path, self.colors["background"])

        border_pen = QPen(self.colors["border"])
        border_pen.setWidth(1)
        painter.setPen(border_pen)
        painter.drawPath(path)

        # Prepare font for text measurement and drawing
        font = QFont("Segoe UI", 9)
        font.setBold(True)
        painter.setFont(font)

        metrics = painter.fontMetrics()

        # Dot size and spacing between dot and text
        dot_size = 8
        gap = 8

        # Measure text width
        text_width = metrics.horizontalAdvance(self.state_text)
        text_height = metrics.height()

        # Total width of dot + gap + text
        content_width = dot_size + gap + text_width

        # Center the whole content group horizontally
        start_x = int((self.width() - content_width) / 2)

        # Center dot vertically
        dot_x = start_x
        dot_y = int((self.height() - dot_size) / 2)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.dot_color)
        painter.drawEllipse(dot_x, dot_y, dot_size, dot_size)

        # Center text vertically
        text_x = dot_x + dot_size + gap
        text_y = int((self.height() + metrics.ascent() - metrics.descent()) / 2)

        painter.setPen(QPen(self.colors["text"]))
        painter.drawText(text_x, text_y, self.state_text)

        painter.end()

    def mousePressEvent(self, event) -> None:
        """Start dragging when the left mouse button is pressed."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """Move the widget while dragging."""
        if self.is_dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            new_pos = event.globalPosition().toPoint() - self.drag_offset
            self.move(new_pos)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        """Stop dragging and save the final position."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self._save_position()
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def closeEvent(self, event) -> None:
        """Save state and stop the monitor thread when closing."""
        self._save_position()

        try:
            self.monitor.stop()
        except Exception:
            pass

        super().closeEvent(event)

    def keyPressEvent(self, event) -> None:
        """Allow closing the widget with the Escape key."""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            event.accept()
            return

        super().keyPressEvent(event)


def main() -> int:
    """Start the PySide6 application."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    banner = LidBanner()
    banner.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())