"""Qt stylesheet for a compact, readable RepoScope desktop window."""

APP_STYLE = """
QMainWindow, QWidget { background: #f5f7fb; color: #172033; font-size: 13px; }
QLabel#title { font-size: 24px; font-weight: 700; color: #14213d; }
QLabel#subtitle { color: #657089; }
QLineEdit { background: white; border: 1px solid #cbd3e1; border-radius: 6px; padding: 7px 9px; }
QPushButton { background: #2563eb; color: white; border: 0; border-radius: 6px; padding: 8px 14px; font-weight: 600; }
QPushButton:hover { background: #1d4ed8; }
QPushButton:disabled { background: #9aa8bf; }
QListWidget { background: #eaf0fb; border: 0; padding: 8px; outline: 0; }
QListWidget::item { padding: 12px 10px; border-radius: 6px; }
QListWidget::item:selected { background: #2563eb; color: white; }
QFrame#card { background: white; border: 1px solid #e1e6ef; border-radius: 8px; }
QLabel#cardValue { font-size: 22px; font-weight: 700; color: #1d4ed8; }
QTableView { background: white; alternate-background-color: #f8fafc; border: 1px solid #dbe2ee; gridline-color: #e6ebf2; selection-background-color: #dbeafe; selection-color: #172033; }
QHeaderView::section { background: #edf2f9; color: #334155; border: 0; border-bottom: 1px solid #dbe2ee; padding: 8px; font-weight: 600; }
QStatusBar { background: #eaf0fb; color: #526079; }
"""
