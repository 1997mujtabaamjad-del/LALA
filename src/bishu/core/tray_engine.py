"""Tray engine for system tray icon and context menu."""

from PyQt5.QtCore import QObject, pyqtSignal

try:
    from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
    from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
    HAS_TRAY = True
except ImportError as err:
    print(f"[TrayEngine] Tray UI components disabled ({err}).")
    HAS_TRAY = False


class TraySignals(QObject):
    """Qt Signals emitted by system tray actions."""

    show = pyqtSignal()
    hide = pyqtSignal()
    reload = pyqtSignal()
    exit_app = pyqtSignal()


class TrayEngine:
    """System tray integration engine."""

    def __init__(self, signals: TraySignals):
        self.signals = signals
        self.tray_icon = None

    def start(self):
        if not HAS_TRAY or not QSystemTrayIcon.isSystemTrayAvailable():
            print("[TrayEngine] System tray not available on this platform.")
            return

        try:
            pixmap = QPixmap(32, 32)
            pixmap.fill(QColor(0, 0, 0, 0))
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QColor(0, 180, 255))
            painter.setPen(QColor(255, 255, 255))
            painter.drawEllipse(2, 2, 28, 28)
            painter.end()

            icon = QIcon(pixmap)

            menu = QMenu()
            show_action = QAction("Show Orb", menu)
            show_action.triggered.connect(self.signals.show.emit)
            menu.addAction(show_action)

            hide_action = QAction("Hide Orb", menu)
            hide_action.triggered.connect(self.signals.hide.emit)
            menu.addAction(hide_action)

            reload_action = QAction("Reload Schedule", menu)
            reload_action.triggered.connect(self.signals.reload.emit)
            menu.addAction(reload_action)

            menu.addSeparator()

            exit_action = QAction("Exit", menu)
            exit_action.triggered.connect(self.signals.exit_app.emit)
            menu.addAction(exit_action)

            self.tray_icon = QSystemTrayIcon(icon)
            self.tray_icon.setContextMenu(menu)
            self.tray_icon.setToolTip("Laalaa Assistant")
            self.tray_icon.show()
            print("[TrayEngine] System tray icon initialized.")
        except Exception as e:
            print(f"[TrayEngine] System tray initialization failed: {e}")
