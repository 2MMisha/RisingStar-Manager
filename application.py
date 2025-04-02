import sys
import csv
import subprocess
from PyQt6.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout, QLineEdit, QLabel, QTextEdit, QMessageBox)
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QIcon
import os
import signal

# Worker thread to run the script and capture output
class ScriptRunner(QThread):
    output_signal = pyqtSignal(str)
    
    def __init__(self, script_path):
        super().__init__()
        self.script_path = script_path
        self.process = None
        self.running = False
    
    def run(self):
        self.running = True
        self.process = subprocess.Popen(
            [sys.executable, self.script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        for line in self.process.stdout:
            if not self.running:
                break
            self.output_signal.emit(line.strip())
        
        self.process.stdout.close()
        self.process.wait()
        self.output_signal.emit("Script stopped.")
    
    def stop(self):
        if self.process:
            self.running = False
            # Attempt to terminate the process gracefully first
            try:
                self.process.terminate()
                self.process.wait(timeout=2)  # Give it 2 seconds to terminate
            except subprocess.TimeoutExpired:
                self.process.kill()  # If it doesn't terminate, force kill it
                self.output_signal.emit("Forcefully stopped the script.")
            finally:
                self.wait()

# Main application window
class MainWindow(QWidget):
    def __init__(self, script_path):
        super().__init__()
        self.script_path = script_path
        self.runner = None
        
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("RSM Server")
        self.setGeometry(300, 300, 500, 400)
        self.setWindowIcon(QIcon("icon.ico"))  # Add this line for the icon
        
        self.log_output = QTextEdit(self)
        self.log_output.setReadOnly(True)
        
        self.start_button = QPushButton("Start", self)
        self.start_button.clicked.connect(self.start_script)
        
        self.stop_button = QPushButton("Stop", self)
        self.stop_button.clicked.connect(self.stop_script)
        
        layout = QVBoxLayout()
        layout.addWidget(self.log_output)
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)
        self.setLayout(layout)
    
    def start_script(self):
        if not self.runner or not self.runner.isRunning():
            self.log_output.append("Starting script...")
            self.runner = ScriptRunner(self.script_path)
            self.runner.output_signal.connect(self.log_output.append)
            self.runner.start()
    
    def stop_script(self):
        if self.runner and self.runner.isRunning():
            self.log_output.append("Stopping script...")
            self.runner.stop()

# Login window
class LoginWindow(QWidget):
    def __init__(self, codes_file, script_path):
        super().__init__()
        self.codes_file = codes_file
        self.script_path = script_path
        
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("Enter Access Code")
        self.setGeometry(400, 200, 300, 150)
        self.setWindowIcon(QIcon("icon.svg"))  # Add this line for the icon
        
        self.label = QLabel("Enter Code:", self)
        self.code_input = QLineEdit(self)
        self.submit_button = QPushButton("Submit", self)
        self.submit_button.clicked.connect(self.check_code)
        
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.code_input)
        layout.addWidget(self.submit_button)
        self.setLayout(layout)
    
    def check_code(self):
        entered_code = self.code_input.text().strip()
        if self.validate_code(entered_code):
            self.accept_login()
        else:
            QMessageBox.warning(self, "Error", "Invalid Code!")
    
    def validate_code(self, entered_code):
        try:
            with open(self.codes_file, "r") as file:
                reader = csv.reader(file)
                valid_codes = {row[0] for row in reader}
                return entered_code in valid_codes
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read codes file: {e}")
            return False
    
    def accept_login(self):
        self.hide()
        self.main_window = MainWindow(self.script_path)
        self.main_window.show()

# Main execution
if __name__ == "__main__":
    app = QApplication(sys.argv)
    codes_file = "codes.csv"  # Path to the CSV file with access codes
    script_path = "app.py"  # Path to the Python script to execute
    login_window = LoginWindow(codes_file, script_path)
    login_window.show()
    sys.exit(app.exec())
