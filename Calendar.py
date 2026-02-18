import sys
import os
import json
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QGridLayout, QVBoxLayout,
    QHBoxLayout, QDialog, QLineEdit, QTimeEdit, QFormLayout, QListWidget,
    QDialogButtonBox, QSystemTrayIcon, QMenu
)
from PySide6.QtCore import Qt, QTimer, QTime
from PySide6.QtGui import QFont, QIcon, QAction
import winsound

# ----------------- Paths -----------------
BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
APPDATA_DIR = os.path.join(os.getenv("APPDATA"), "StudyCalendar")
os.makedirs(APPDATA_DIR, exist_ok=True)
TASKS_FILE = os.path.join(APPDATA_DIR, "tasks.json")
APP_ICON = os.path.join(BASE_DIR, "calendar.ico")
ALARM_FILE = os.path.join(BASE_DIR, "alarm.wav")  # optional mp3 sound

# ----------------- Winotify Notifications -----------------
from winotify import Notification, audio
def notify(task_name):
    try:
        toast = Notification(
            app_id="Study Calendar",
            title="⏰ Task Reminder",
            msg=task_name,
            icon=APP_ICON if os.path.exists(APP_ICON) else None,
            duration="short"
        )
        if os.path.exists(ALARM_FILE): 
            winsound.PlaySound(ALARM_FILE, winsound.SND_FILENAME | winsound.SND_ASYNC)
        toast.set_audio(audio.Default, loop=False)
        toast.show()
    except Exception:
        pass

# =================== JSON Handling =================
def load_events():
    try:
        with open(TASKS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_events(events):
    with open(TASKS_FILE, "w") as f:
        json.dump(events, f, indent=4)

# ----------------- Task Dialog -----------------
class TaskDialog(QDialog):
    def __init__(self, date_str, parent=None, task=None, task_index=None):
        super().__init__(parent)
        self.setWindowTitle(f"Task - {date_str}")
        self.setWindowIcon(QIcon(APP_ICON if os.path.exists(APP_ICON) else ""))
        self.date_str = date_str
        self.task_index = task_index

        layout = QFormLayout()
        self.task_input = QLineEdit()
        self.time_input = QTimeEdit()
        self.time_input.setDisplayFormat("HH:mm")
        layout.addRow("Task:", self.task_input)
        layout.addRow("Alarm Time:", self.time_input)

        if task:
            self.task_input.setText(task["task"])
            h, m = map(int, task["time"].split(":"))
            self.time_input.setTime(QTime(h, m))

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        if task:
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(self.delete_task)
            buttons.addButton(delete_btn, QDialogButtonBox.ActionRole)

        buttons.accepted.connect(self.save_task)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def save_task(self):
        task_name = self.task_input.text()
        task_time = self.time_input.time().toString("HH:mm")
        if not task_name:
            return
        events = load_events()
        if self.date_str not in events:
            events[self.date_str] = []
        if self.task_index is not None:
            events[self.date_str][self.task_index] = {"task": task_name, "time": task_time}
        else:
            events[self.date_str].append({"task": task_name, "time": task_time})
        save_events(events)
        self.accept()
        self.parent().draw_calendar()

    def delete_task(self):
        events = load_events()
        if self.task_index is not None:
            del events[self.date_str][self.task_index]
            if not events[self.date_str]:
                del events[self.date_str]
            save_events(events)
        self.accept()
        self.parent().draw_calendar()

# ----------------- Day Tasks Dialog -----------------
class DayTasksDialog(QDialog):
    def __init__(self, date_str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Tasks - {date_str}")
        self.setWindowIcon(QIcon(APP_ICON if os.path.exists(APP_ICON) else ""))
        self.date_str = date_str

        layout = QVBoxLayout()
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        self.add_btn = QPushButton("+ Add Task")
        self.add_btn.setStyleSheet("background-color:#2980B9; color:white; border-radius:5px;")
        self.add_btn.clicked.connect(self.add_task)
        layout.addWidget(self.add_btn)

        self.populate_tasks()
        self.list_widget.itemDoubleClicked.connect(self.edit_task)
        self.setLayout(layout)

    def populate_tasks(self):
        self.list_widget.clear()
        events = load_events()
        if self.date_str in events:
            for t in events[self.date_str]:
                self.list_widget.addItem(f"{t['time']} - {t['task']}")

    def add_task(self):
        dialog = TaskDialog(self.date_str, parent=self.parent())
        dialog.exec()
        self.populate_tasks()
        self.parent().draw_calendar()

    def edit_task(self, item):
        index = self.list_widget.currentRow()
        events = load_events()
        task = events[self.date_str][index]
        dialog = TaskDialog(self.date_str, parent=self.parent(), task=task, task_index=index)
        dialog.exec()
        self.populate_tasks()
        self.parent().draw_calendar()

# ----------------- Calendar App -----------------
class CalendarApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Study Calendar")
        self.setWindowIcon(QIcon(APP_ICON if os.path.exists(APP_ICON) else ""))
        self.resize(800, 650)
        self.current_date = datetime.today()
        self.finished_today = set()

        main_layout = QVBoxLayout()
        nav_layout = QHBoxLayout()

        self.month_label = QLabel()
        self.month_label.setFont(QFont("Segoe UI", 32, QFont.Bold))
        self.month_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.month_label)

        # Navigation buttons
        self.prev_year_btn = QPushButton("<< Year")
        self.prev_month_btn = QPushButton("< Month")
        self.next_month_btn = QPushButton("Month >")
        self.next_year_btn = QPushButton("Year >>")
        for btn in [self.prev_year_btn, self.prev_month_btn, self.next_month_btn, self.next_year_btn]:
            btn.setStyleSheet("background-color:#2980B9;color:white;border-radius:5px;padding:6px;")
        self.prev_year_btn.clicked.connect(self.prev_year)
        self.prev_month_btn.clicked.connect(self.prev_month)
        self.next_month_btn.clicked.connect(self.next_month)
        self.next_year_btn.clicked.connect(self.next_year)
        nav_layout.addWidget(self.prev_year_btn)
        nav_layout.addWidget(self.prev_month_btn)
        nav_layout.addWidget(self.next_month_btn)
        nav_layout.addWidget(self.next_year_btn)
        main_layout.addLayout(nav_layout)

        self.calendar_grid = QGridLayout()
        main_layout.addLayout(self.calendar_grid)
        self.setLayout(main_layout)

        self.draw_calendar()

        # Reminder timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_notifications)
        self.timer.start(30000)  # every 30 seconds

        # ---------- System Tray Setup ----------
        self.is_quitting = False  # flag to handle proper exit

        # Create the tray icon
        self.tray_icon = QSystemTrayIcon(QIcon(APP_ICON if os.path.exists(APP_ICON) else ""))
        self.tray_icon.setToolTip("Study Calendar")

        # Create tray menu
        tray_menu = QMenu()
        show_action = QAction("Show")
        show_action.triggered.connect(self.show_from_tray)
        tray_menu.addAction(show_action)

        exit_action = QAction("Exit")
        exit_action.triggered.connect(self.exit_app)  # our custom exit method
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)

        # Handle double-click on tray icon
        self.tray_icon.activated.connect(self.on_tray_activated)

        # Show the tray icon
        self.tray_icon.show()

    # ---------- Tray Event Handler ----------
    def on_tray_activated(self, reason):
        """Handle tray icon events."""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_from_tray()  # restore window
        elif reason == QSystemTrayIcon.Context:  # right-click
            self.exit_app()  # fully exit the app
    
    def show_from_tray(self):
        """Restore window from tray."""
        self.show()
        self.raise_()
        self.activateWindow()
    
    def exit_app(self):
        """Exit the app cleanly from tray."""
        self.is_quitting = True
        self.tray_icon.hide()
        QApplication.instance().quit()  # ensures full app exit
    
    # ---------- Override closeEvent ----------
    def closeEvent(self, event):
        """Minimize to tray unless quitting."""
        if self.is_quitting:
            event.accept()  # really close
        else:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Study Calendar",
                "App minimized to tray. Right-click icon to exit.",
                QSystemTrayIcon.Information,
                3000
            )
    



    # ----------------- Calendar -----------------
    def draw_calendar(self):
        for i in reversed(range(self.calendar_grid.count())):
            item = self.calendar_grid.itemAt(i)
            if item.widget():
                item.widget().setParent(None)

        self.month_label.setText(self.current_date.strftime("%B %Y"))

        weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, day in enumerate(weekdays):
            lbl = QLabel(day)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
            self.calendar_grid.addWidget(lbl, 0, i)

        first_day = self.current_date.replace(day=1)
        start_weekday = first_day.weekday()
        next_month = first_day.replace(month=self.current_date.month % 12 + 1, day=1) \
            if self.current_date.month < 12 else first_day.replace(year=self.current_date.year + 1, month=1, day=1)
        days_in_month = (next_month - timedelta(days=1)).day

        events = load_events()
        row, col = 1, start_weekday

        for day in range(1, days_in_month + 1):
            btn = QPushButton(str(day))
            btn.setFixedSize(80, 80)
            btn.setFont(QFont("Segoe UI", 14))
            date_str = self.current_date.replace(day=day).strftime("%Y-%m-%d")

            style = """
            QPushButton {
                border: 1px solid #BDC3C7;
                border-radius: 8px;
                background-color:#313131;
            }
            QPushButton:hover {
                background-color:#1c1c1c;
            }
            """

            if date_str in events and events[date_str]:
                now = datetime.now()
                pending = any(datetime.strptime(f"{date_str} {t['time']}", "%Y-%m-%d %H:%M") > now for t in events[date_str])
                if pending:
                    style = """
                             QPushButton {
                                 border: 1px solid #BDC3C7;
                                 border-radius: 8px;
                                 background-color:#E74C3C;
                             }
                             """
                else:
                    style = """
                            QPushButton {
                                border: 1px solid #BDC3C7;
                                border-radius: 8px;
                                background-color:#2ECC71;
                            }
                            """
                    self.finished_today.add(date_str)
            elif date_str in self.finished_today:
                style = """
                        QPushButton {
                            border: 1px solid #BDC3C7;
                            border-radius: 8px;
                            background-color:#2ECC71;
                        }
                        """

            btn.setStyleSheet(style)
            btn.clicked.connect(lambda checked, ds=date_str: self.open_day_tasks(ds))
            self.calendar_grid.addWidget(btn, row, col)

            col += 1
            if col > 6:
                col = 0
                row += 1

    # ----------------- Navigation -----------------
    def prev_month(self):
        year = self.current_date.year
        month = self.current_date.month - 1
        if month < 1:
            month = 12
            year -= 1
        self.current_date = self.current_date.replace(year=year, month=month)
        self.draw_calendar()

    def next_month(self):
        year = self.current_date.year
        month = self.current_date.month + 1
        if month > 12:
            month = 1
            year += 1
        self.current_date = self.current_date.replace(year=year, month=month)
        self.draw_calendar()

    def prev_year(self):
        self.current_date = self.current_date.replace(year=self.current_date.year - 1)
        self.draw_calendar()

    def next_year(self):
        self.current_date = self.current_date.replace(year=self.current_date.year + 1)
        self.draw_calendar()

    # ----------------- Day Tasks -----------------
    def open_day_tasks(self, date_str):
        dialog = DayTasksDialog(date_str, parent=self)
        dialog.exec()
        self.draw_calendar()

    # ----------------- Reminders -----------------
    def check_notifications(self):
        now = datetime.now()
        events = load_events()
        updated = False

        for date_str in list(events.keys()):
            for i in reversed(range(len(events[date_str]))):
                task = events[date_str][i]
                task_time = datetime.strptime(f"{date_str} {task['time']}", "%Y-%m-%d %H:%M")
                if task_time <= now < (task_time + timedelta(minutes=1)):
                    notify(task['task'])
                    self.finished_today.add(date_str)
                    del events[date_str][i]
                    updated = True
            if date_str in events and not events[date_str]:
                del events[date_str]
                updated = True

        if updated:
            save_events(events)
            self.draw_calendar()

# ----------------- Run -----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CalendarApp()
    window.show()
    sys.exit(app.exec())
