import logging
import os
import webbrowser
from urllib.parse import urlencode

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QDialog, QMessageBox, QMenu

from plugins.base import UiExtensionPlugin
from app.translation_manager import translation_manager
from feedback_dialog import FeedbackDialog

class FeedbackPlugin(UiExtensionPlugin):
    GITHUB_REPO_URL = "https://github.com/dawciobiel/QuickFile/issues/new"

    @property
    def name(self) -> str:
        return "Feedback System"

    @property
    def description(self) -> str:
        return "A plugin to collect feedback and bug reports from users via GitHub issues."

    def initialize(self, main_window):
        self.main_window = main_window
        
        help_menu = None
        expected_menu_title = translation_manager.translate("MenuPanel", "&Help")

        for menu in self.main_window.menuBar().findChildren(QMenu):
            if menu.title() == expected_menu_title:
                help_menu = menu
                break
        
        if help_menu:
            feedback_action = QAction(translation_manager.translate("FeedbackPlugin", "Submit Feedback..."), self.main_window)
            feedback_action.triggered.connect(self.show_feedback_dialog)
            
            if help_menu.actions():
                help_menu.addSeparator()
                
            help_menu.addAction(feedback_action)
        else:
            logging.warning(f"Could not find 'Help' menu ('{expected_menu_title}') to add feedback action.")

    def show_feedback_dialog(self):
        dialog = FeedbackDialog(self.main_window)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            feedback_data = dialog.get_feedback_data()
            if not feedback_data["title"] or not feedback_data["description"]:
                QMessageBox.warning(self.main_window, "Missing Information", "Please provide both a title and a description.")
                return
            self.create_github_issue(feedback_data)

    def _read_log_files(self, attach_actions, attach_main):
        log_content = ""
        try:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
            main_log_path = os.path.join(project_root, "logs", "main.log")
            actions_log_path = os.path.join(project_root, "logs", "actions.log")

            if attach_main and os.path.exists(main_log_path):
                with open(main_log_path, 'r') as f:
                    log_content += "### main.log\n```\n" + f.read() + "\n```\n\n"
            
            if attach_actions and os.path.exists(actions_log_path):
                with open(actions_log_path, 'r') as f:
                    log_content += "### actions.log (anonymized)\n```\n" + f.read() + "\n```\n"
        except Exception as e:
            logging.error(f"Error reading log files: {e}")
            log_content += f"\n*Error reading logs: {e}*"
        
        return log_content

    def create_github_issue(self, data):
        issue_body = data["description"]
        
        attach_actions = data.get("attach_actions_log", False)
        attach_main = data.get("attach_main_log", False)

        if attach_actions or attach_main:
            issue_body += """\n\n---
<details>
<summary>Attached Logs</summary>

"""
            issue_body += self._read_log_files(attach_actions, attach_main)
            issue_body += "\n</details>"

        params = {
            "title": data["title"],
            "body": issue_body,
            "labels": "bug" if data["type"] == "bug" else "enhancement"
        }
        
        url = self.GITHUB_REPO_URL + "?" + urlencode(params)
        
        try:
            webbrowser.open(url)
        except Exception as e:
            logging.error(f"Failed to open web browser: {e}")
            QMessageBox.critical(self.main_window, "Error", f"Could not open web browser. Please create the issue manually at:\n{self.GITHUB_REPO_URL}")
