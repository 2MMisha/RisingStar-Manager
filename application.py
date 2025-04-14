import sys
import json
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QListWidget, QListWidgetItem, QLineEdit,
    QLabel, QDialog, QFormLayout, QInputDialog, QTextEdit
)
from PyQt6.QtCore import Qt, QProcess
from PyQt6.QtGui import QIcon

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RSM Server")
        self.setWindowIcon(QIcon('server.ico'))
        self.setGeometry(100, 100, 700, 500)

        self.process = None  # QProcess для сервера

        tabs = QTabWidget()
        tabs.addTab(self.create_contestants_tab(), "Participants")
        tabs.addTab(self.create_judges_tab(), "Judges")
        tabs.addTab(self.create_criteria_tab(), "Criteria")
        tabs.addTab(self.create_server_tab(), "Server")

        self.setCentralWidget(tabs)

    # ===== Judges Tab =====
    def create_judges_tab(self):
        judges_tab = QWidget()
        layout = QVBoxLayout()

        self.judges_list = QListWidget()
        self.judges_list.itemDoubleClicked.connect(self.edit_judge)
        self.load_judges()

        self.add_judge_input = QLineEdit()
        self.add_judge_button = QPushButton("Add Judge")
        self.add_judge_button.clicked.connect(self.add_judge)

        self.remove_judge_button = QPushButton("Remove Selected Judge")
        self.remove_judge_button.clicked.connect(self.remove_judge)

        layout.addWidget(QLabel("Judges:"))
        layout.addWidget(self.judges_list)
        layout.addWidget(self.add_judge_input)
        layout.addWidget(self.add_judge_button)
        layout.addWidget(self.remove_judge_button)

        judges_tab.setLayout(layout)
        return judges_tab

    def load_judges(self):
        self.judges_list.clear()
        try:
            with open("data.json", "r") as f:
                data = json.load(f)
                for name in data.get("judges", []):
                    self.judges_list.addItem(name)
        except FileNotFoundError:
            pass

    def add_judge(self):
        name = self.add_judge_input.text().strip()
        if not name:
            return
        with open("data.json", "r+") as f:
            data = json.load(f)
            data.setdefault("judges", []).append(name)
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=4)
        self.load_judges()
        self.add_judge_input.clear()

    def remove_judge(self):
        selected = self.judges_list.currentItem()
        if selected:
            name = selected.text()
            with open("data.json", "r+") as f:
                data = json.load(f)
                data["judges"] = [j for j in data.get("judges", []) if j != name]
                f.seek(0)
                f.truncate()
                json.dump(data, f, indent=4)
            self.load_judges()

    def edit_judge(self, item):
        old_name = item.text()
        new_name, ok = QInputDialog.getText(self, "Edit Judge", "Edit judge name:", text=old_name)
        if ok and new_name.strip():
            with open("data.json", "r+") as f:
                data = json.load(f)
                if "judges" in data and old_name in data["judges"]:
                    index = data["judges"].index(old_name)
                    data["judges"][index] = new_name.strip()
                    f.seek(0)
                    f.truncate()
                    json.dump(data, f, indent=4)
            self.load_judges()

    # ===== Server Tab =====
    def create_server_tab(self):
        server_tab = QWidget()
        layout = QVBoxLayout()

        self.server_output = QTextEdit()
        self.server_output.setReadOnly(True)

        self.server_button = QPushButton("Start Server")
        self.server_button.clicked.connect(self.toggle_server)

        layout.addWidget(self.server_output)
        layout.addWidget(self.server_button)
        server_tab.setLayout(layout)
        return server_tab

    def toggle_server(self):
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()
            self.process = None
            self.server_button.setText("Start Server")
            self.server_output.append("Server stopped.")
        else:
            self.process = QProcess(self)
            self.process.readyReadStandardOutput.connect(self.handle_stdout)
            self.process.readyReadStandardError.connect(self.handle_stderr)
            self.process.finished.connect(self.server_finished)
            self.process.start("python", ["main.py"])
            self.server_button.setText("Stop Server")
            self.server_output.append("Server started...")

    def handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode()
        self.server_output.append(data)

    def handle_stderr(self):
        data = self.process.readAllStandardError().data().decode()
        self.server_output.append(f"[MESSAGE] {data}")

    def server_finished(self):
        self.server_output.append("Server finished.")
        self.server_button.setText("Start Server")
        self.process = None
    # ===== Participants Tab =====
    def create_contestants_tab(self):
        contestants_tab = QWidget()
        layout = QVBoxLayout()

        self.contestants_list = QListWidget()
        self.contestants_list.itemDoubleClicked.connect(self.edit_contestant)
        self.load_contestants()

        self.add_contestant_number = QLineEdit()
        self.add_contestant_name = QLineEdit()
        self.add_contestant_category = QLineEdit()
        self.add_contestant_button = QPushButton("Add Contestant")
        self.add_contestant_button.clicked.connect(self.add_contestant)

        self.remove_contestant_button = QPushButton("Remove Selected Contestant")
        self.remove_contestant_button.clicked.connect(self.remove_contestant)

        layout.addWidget(QLabel("Contestants:"))
        layout.addWidget(self.contestants_list)
        layout.addWidget(QLabel("Number:"))
        layout.addWidget(self.add_contestant_number)
        layout.addWidget(QLabel("Name:"))
        layout.addWidget(self.add_contestant_name)
        layout.addWidget(QLabel("Category:"))
        layout.addWidget(self.add_contestant_category)
        layout.addWidget(self.add_contestant_button)
        layout.addWidget(self.remove_contestant_button)

        contestants_tab.setLayout(layout)
        return contestants_tab

    def load_contestants(self):
        self.contestants_list.clear()
        try:
            with open("data.json", "r") as f:
                data = json.load(f)
                for c in data.get("contestants", []):
                    self.contestants_list.addItem(f"{c['number']}: {c['name']} ({c['category']})")
        except FileNotFoundError:
            pass

    def add_contestant(self):
        number = self.add_contestant_number.text().strip()
        name = self.add_contestant_name.text().strip()
        category = self.add_contestant_category.text().strip()

        if not number or not name or not category:
            return

        with open("data.json", "r+") as f:
            data = json.load(f)
            data.setdefault("contestants", []).append({
                "number": number,
                "name": name,
                "category": category
            })
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=4)
        self.load_contestants()
        self.add_contestant_number.clear()
        self.add_contestant_name.clear()
        self.add_contestant_category.clear()

    def remove_contestant(self):
        selected = self.contestants_list.currentItem()
        if selected:
            number = selected.text().split(":")[0].strip()
            with open("data.json", "r+") as f:
                data = json.load(f)
                data["contestants"] = [c for c in data.get("contestants", []) if str(c["number"]) != number]
                f.seek(0)
                f.truncate()
                json.dump(data, f, indent=4)
            self.load_contestants()

    def edit_contestant(self, item):
        number = item.text().split(":")[0].strip()
        with open("data.json", "r+") as f:
            data = json.load(f)
            for i, c in enumerate(data.get("contestants", [])):
                if str(c["number"]) == number:
                    dialog = QDialog(self)
                    dialog.setWindowTitle("Edit Contestant")
                    layout = QFormLayout(dialog)

                    number_input = QLineEdit(str(c["number"]))
                    name_input = QLineEdit(c["name"])
                    category_input = QLineEdit(c["category"])

                    layout.addRow("Number:", number_input)
                    layout.addRow("Name:", name_input)
                    layout.addRow("Category:", category_input)

                    save_button = QPushButton("Save")
                    save_button.clicked.connect(dialog.accept)
                    layout.addWidget(save_button)
                    dialog.setLayout(layout)

                    if dialog.exec():
                        new_number = number_input.text().strip()
                        new_name = name_input.text().strip()
                        new_category = category_input.text().strip()
                        if new_number and new_name and new_category:
                            data["contestants"][i] = {
                                "number": new_number,
                                "name": new_name,
                                "category": new_category
                            }
                            f.seek(0)
                            f.truncate()
                            json.dump(data, f, indent=4)
                            self.load_contestants()
                    break

    # ===== Criteria Tab =====
    def create_criteria_tab(self):
        criteria_tab = QWidget()
        layout = QVBoxLayout()

        self.criteria_list = QListWidget()
        self.criteria_list.itemDoubleClicked.connect(self.edit_criteria)
        self.load_criteria()

        self.add_criteria_name = QLineEdit()
        self.add_criteria_weight = QLineEdit()
        self.add_criteria_min = QLineEdit()
        self.add_criteria_max = QLineEdit()
        self.add_criteria_button = QPushButton("Add Criterion")
        self.add_criteria_button.clicked.connect(self.add_criterion)

        self.remove_criteria_button = QPushButton("Remove Selected Criterion")
        self.remove_criteria_button.clicked.connect(self.remove_criterion)

        layout.addWidget(QLabel("Criteria:"))
        layout.addWidget(self.criteria_list)
        layout.addWidget(QLabel("Name:"))
        layout.addWidget(self.add_criteria_name)
        layout.addWidget(QLabel("Weight:"))
        layout.addWidget(self.add_criteria_weight)
        layout.addWidget(QLabel("Min Score:"))
        layout.addWidget(self.add_criteria_min)
        layout.addWidget(QLabel("Max Score:"))
        layout.addWidget(self.add_criteria_max)
        layout.addWidget(self.add_criteria_button)
        layout.addWidget(self.remove_criteria_button)

        criteria_tab.setLayout(layout)
        return criteria_tab

    def load_criteria(self):
        self.criteria_list.clear()
        try:
            with open("data.json", "r") as f:
                data = json.load(f)
                for c in data.get("criteria", []):
                    self.criteria_list.addItem(f"{c['name']} (Weight: {c['weight']}, {c['min_score']}-{c['max_score']})")
        except FileNotFoundError:
            pass

    def add_criterion(self):
        name = self.add_criteria_name.text().strip()
        weight = self.add_criteria_weight.text().strip()
        min_score = self.add_criteria_min.text().strip()
        max_score = self.add_criteria_max.text().strip()

        if not name or not weight or not min_score or not max_score:
            return

        with open("data.json", "r+") as f:
            data = json.load(f)
            data.setdefault("criteria", []).append({
                "name": name,
                "weight": int(weight),
                "min_score": int(min_score),
                "max_score": int(max_score)
            })
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=4)
        self.load_criteria()
        self.add_criteria_name.clear()
        self.add_criteria_weight.clear()
        self.add_criteria_min.clear()
        self.add_criteria_max.clear()

    def remove_criterion(self):
        selected = self.criteria_list.currentItem()
        if selected:
            name = selected.text().split(" (")[0].strip()
            with open("data.json", "r+") as f:
                data = json.load(f)
                data["criteria"] = [c for c in data.get("criteria", []) if c["name"] != name]
                f.seek(0)
                f.truncate()
                json.dump(data, f, indent=4)
            self.load_criteria()

    def edit_criteria(self, item):
        name = item.text().split(" (")[0].strip()
        with open("data.json", "r+") as f:
            data = json.load(f)
            for i, c in enumerate(data.get("criteria", [])):
                if c["name"] == name:
                    dialog = QDialog(self)
                    dialog.setWindowTitle("Edit Criterion")
                    layout = QFormLayout(dialog)

                    name_input = QLineEdit(c["name"])
                    weight_input = QLineEdit(str(c["weight"]))
                    min_input = QLineEdit(str(c["min_score"]))
                    max_input = QLineEdit(str(c["max_score"]))

                    layout.addRow("Name:", name_input)
                    layout.addRow("Weight:", weight_input)
                    layout.addRow("Min Score:", min_input)
                    layout.addRow("Max Score:", max_input)

                    save_button = QPushButton("Save")
                    save_button.clicked.connect(dialog.accept)
                    layout.addWidget(save_button)
                    dialog.setLayout(layout)

                    if dialog.exec():
                        new_name = name_input.text().strip()
                        new_weight = int(weight_input.text().strip())
                        new_min = int(min_input.text().strip())
                        new_max = int(max_input.text().strip())

                        if new_name:
                            data["criteria"][i] = {
                                "name": new_name,
                                "weight": new_weight,
                                "min_score": new_min,
                                "max_score": new_max
                            }
                            f.seek(0)
                            f.truncate()
                            json.dump(data, f, indent=4)
                            self.load_criteria()
                    break


# ===== Запуск приложения =====
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
