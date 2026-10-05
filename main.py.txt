
import sqlite3
from datetime import datetime
from pathlib import Path
from math import ceil

from kivy.app import App
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout

KV = r"""
#:import dp kivy.metrics.dp

<SubjectRow@BoxLayout>:
    subject_id: 0
    name: ""
    size_hint_y: None
    height: dp(68)
    spacing: dp(8)
    padding: dp(8)
    canvas.before:
        Color:
            rgba: .12, .14, .18, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [12]
    Label:
        text: root.name
        text_size: self.size
        halign: "left"
        valign: "middle"
    Button:
        text: "✓ Present"
        size_hint_x: .25
        on_release: app.mark_attendance(root.subject_id, 1)
    Button:
        text: "✗ Absent"
        size_hint_x: .25
        on_release: app.mark_attendance(root.subject_id, 0)

<MainScreen>:
    BoxLayout:
        orientation: "vertical"
        padding: dp(12)
        spacing: dp(10)
        canvas.before:
            Color:
                rgba: .055, .065, .085, 1
            Rectangle:
                pos: self.pos
                size: self.size

        Label:
            text: "Attendance Tracker"
            font_size: "24sp"
            bold: True
            size_hint_y: None
            height: dp(45)

        BoxLayout:
            size_hint_y: None
            height: dp(90)
            spacing: dp(8)
            Label:
                text: "Overall\\n" + app.overall_text
                font_size: "17sp"
                halign: "center"
                valign: "middle"
            Label:
                text: "Present / Total\\n" + app.overall_counts
                font_size: "17sp"
                halign: "center"
                valign: "middle"

        Label:
            text: "Today's Lectures — tap Present or Absent"
            size_hint_y: None
            height: dp(35)
            bold: True

        ScrollView:
            do_scroll_x: False
            GridLayout:
                id: subject_list
                cols: 1
                spacing: dp(8)
                padding: dp(2)
                size_hint_y: None
                height: self.minimum_height

        BoxLayout:
            size_hint_y: None
            height: dp(48)
            spacing: dp(8)
            Button:
                text: "Refresh"
                on_release: app.refresh()
            Button:
                text: "Subjects"
                on_release: app.show_subjects()
            Button:
                text: "History"
                on_release: app.show_history()
            Button:
                text: "Add Subject"
                on_release: app.add_subject_popup()

<SubjectsScreen>:
    BoxLayout:
        orientation: "vertical"
        padding: dp(12)
        spacing: dp(10)
        Label:
            text: "Subjects"
            font_size: "24sp"
            size_hint_y: None
            height: dp(45)
        ScrollView:
            do_scroll_x: False
            GridLayout:
                id: subjects_list
                cols: 1
                spacing: dp(8)
                size_hint_y: None
                height: self.minimum_height
        Button:
            text: "Back"
            size_hint_y: None
            height: dp(48)
            on_release: app.go_home()

<HistoryScreen>:
    BoxLayout:
        orientation: "vertical"
        padding: dp(12)
        spacing: dp(8)
        Label:
            text: "Attendance History"
            font_size: "24sp"
            size_hint_y: None
            height: dp(45)
        ScrollView:
            do_scroll_x: False
            GridLayout:
                id: history_list
                cols: 1
                spacing: dp(5)
                size_hint_y: None
                height: self.minimum_height
        Button:
            text: "Back"
            size_hint_y: None
            height: dp(48)
            on_release: app.go_home()
"""

class MainScreen(Screen):
    pass

class SubjectsScreen(Screen):
    pass

class HistoryScreen(Screen):
    pass

class AttendanceApp(App):
    overall_text = StringProperty("0.00%")
    overall_counts = StringProperty("0 / 0")
    db = None

    def build(self):
        self.title = "Attendance Tracker"
        Builder.load_string(KV)
        self.db = self.open_db()
        self.ensure_defaults()
        return Builder.load_string(
            '<ScreenManager>:\n'
            '    MainScreen:\n'
            '    SubjectsScreen:\n'
            '    HistoryScreen:\n'
        )

    def open_db(self):
        data_dir = Path(self.user_data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(str(data_dir / "attendance.db"))
        db.execute("""CREATE TABLE IF NOT EXISTS subjects(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS attendance(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            present INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY(subject_id) REFERENCES subjects(id)
        )""")
        db.commit()
        return db

    def ensure_defaults(self):
        defaults = [
            "Engineering Mechanics",
            "Fundamental Programming Language (FPL)",
            "Basic Electrical Engineering (BEE)",
            "Engineering Physics",
            "Mathematics-I (M1)",
        ]
        cur = self.db.cursor()
        for name in defaults:
            cur.execute("INSERT OR IGNORE INTO subjects(name) VALUES(?)", (name,))
        self.db.commit()
        self.refresh()

    def refresh(self):
        try:
            home = self.root.get_screen("MainScreen")
            box = home.ids.subject_list
            box.clear_widgets()
            rows = self.db.execute("SELECT id,name FROM subjects ORDER BY id").fetchall()
            for sid, name in rows:
                from kivy.factory import Factory
                row = Factory.SubjectRow(subject_id=sid, name=name)
                box.add_widget(row)
            self.update_overall()
        except Exception:
            pass

    def update_overall(self):
        total, present = self.db.execute(
            "SELECT COUNT(*), COALESCE(SUM(present),0) FROM attendance"
        ).fetchone()
        pct = (present / total * 100) if total else 0
        self.overall_text = f"{pct:.2f}%"
        self.overall_counts = f"{present} / {total}"

    def mark_attendance(self, subject_id, present):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.db.execute(
            "INSERT INTO attendance(subject_id,present,timestamp) VALUES(?,?,?)",
            (subject_id, present, ts)
        )
        self.db.commit()
        self.refresh()
        self.show_message("Saved", "Attendance recorded successfully.")

    def show_subjects(self):
        self.root.current = "SubjectsScreen"
        self.populate_subjects()

    def populate_subjects(self):
        box = self.root.get_screen("SubjectsScreen").ids.subjects_list
        box.clear_widgets()
        rows = self.db.execute("SELECT id,name FROM subjects ORDER BY id").fetchall()
        for sid, name in rows:
            total, present = self.db.execute(
                "SELECT COUNT(*), COALESCE(SUM(present),0) FROM attendance WHERE subject_id=?",
                (sid,)
            ).fetchone()
            pct = present / total * 100 if total else 0
            row = BoxLayout(size_hint_y=None, height=dp(70), spacing=dp(6))
            row.add_widget(Label(text=f"{name}\n{present}/{total}  ({pct:.1f}%)"))
            b = __import__("kivy.uix.button", fromlist=["Button"]).Button(text="Delete")
            b.bind(on_release=lambda _, x=sid: self.delete_subject(x))
            row.add_widget(b)
            box.add_widget(row)

    def delete_subject(self, sid):
        self.db.execute("DELETE FROM attendance WHERE subject_id=?", (sid,))
        self.db.execute("DELETE FROM subjects WHERE id=?", (sid,))
        self.db.commit()
        self.populate_subjects()
        self.refresh()

    def add_subject_popup(self):
        from kivy.uix.textinput import TextInput
        from kivy.uix.button import Button
        layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        inp = TextInput(hint_text="Subject name", multiline=False)
        btn = Button(text="Add", size_hint_y=None, height=dp(45))
        layout.add_widget(inp)
        layout.add_widget(btn)
        popup = Popup(title="Add Subject", content=layout, size_hint=(.85,.35))
        def add(_):
            name = inp.text.strip()
            if name:
                try:
                    self.db.execute("INSERT INTO subjects(name) VALUES(?)", (name,))
                    self.db.commit()
                    popup.dismiss()
                    self.refresh()
                except sqlite3.IntegrityError:
                    self.show_message("Already exists", "That subject is already in the list.")
        btn.bind(on_release=add)
        popup.open()

    def show_history(self):
        self.root.current = "HistoryScreen"
        box = self.root.get_screen("HistoryScreen").ids.history_list
        box.clear_widgets()
        rows = self.db.execute("""
            SELECT attendance.id, subjects.name, attendance.present, attendance.timestamp
            FROM attendance JOIN subjects ON subjects.id=attendance.subject_id
            ORDER BY attendance.id DESC
        """).fetchall()
        if not rows:
            box.add_widget(Label(text="No attendance recorded yet.", size_hint_y=None, height=dp(50)))
            return
        from kivy.uix.button import Button
        for aid, name, present, ts in rows:
            row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(5))
            row.add_widget(Label(text=f"{ts}  |  {name}  |  {'PRESENT' if present else 'ABSENT'}"))
            b = Button(text="Delete", size_hint_x=.22)
            b.bind(on_release=lambda _, x=aid: self.delete_record(x))
            row.add_widget(b)
            box.add_widget(row)

    def delete_record(self, aid):
        self.db.execute("DELETE FROM attendance WHERE id=?", (aid,))
        self.db.commit()
        self.show_history()
        self.refresh()

    def go_home(self):
        self.root.current = "MainScreen"
        self.refresh()

    def show_message(self, title, message):
        Popup(title=title, content=Label(text=message), size_hint=(.8,.3)).open()

if __name__ == "__main__":
    AttendanceApp().run()
