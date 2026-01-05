import os
from PyQt6.QtWidgets import QDialog, QDialogButtonBox
from PyQt6.uic import loadUi

from app.translation_manager import translation_manager
from utils.resource_path import get_resource_path

class FeedbackDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Load the UI file
        # Note: This path is relative to the plugin's directory, not the project root.
        # get_resource_path won't work here unless we adjust it.
        # For plugins, we assume resources are bundled with them.
        ui_path = os.path.join(os.path.dirname(__file__), "feedback_dialog.ui")
        loadUi(ui_path, self)

        self.setWindowTitle(translation_manager.translate("FeedbackDialog", "Submit Feedback"))
        self.typeGroupBox.setTitle(translation_manager.translate("FeedbackDialog", "Type of Feedback"))
        self.bugRadioButton.setText(translation_manager.translate("FeedbackDialog", "Bug Report"))
        self.suggestionRadioButton.setText(translation_manager.translate("FeedbackDialog", "Suggestion"))
        self.titleLabel.setText(translation_manager.translate("FeedbackDialog", "Title"))
        self.descriptionLabel.setText(translation_manager.translate("FeedbackDialog", "Description"))
        self.logsGroupBox.setTitle(translation_manager.translate("FeedbackDialog", "Attach Logs"))
        self.attachActionsLogCheckBox.setText(translation_manager.translate("FeedbackDialog", "Attach anonymized actions log (actions.log)"))
        self.attachMainLogCheckBox.setText(translation_manager.translate("FeedbackDialog", "Attach main application log (main.log)"))

        # Change the "OK" button text
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText(translation_manager.translate("FeedbackDialog", "Create GitHub Issue"))

        # Connect signals to update the UI state
        self.bugRadioButton.toggled.connect(self._update_log_section_state)
        self.suggestionRadioButton.toggled.connect(self._update_log_section_state)

        # Set initial state
        self._update_log_section_state()

    def _update_log_section_state(self):
        """
        Enables or disables the log attachment section based on the feedback type.
        """
        is_suggestion = self.suggestionRadioButton.isChecked()
        self.logsGroupBox.setEnabled(not is_suggestion)

    def get_feedback_data(self):
        """
        Returns a dictionary with the data entered by the user.
        """
        is_suggestion = self.suggestionRadioButton.isChecked()
        return {
            "type": "bug" if not is_suggestion else "suggestion",
            "title": self.titleLineEdit.text(),
            "description": self.descriptionTextEdit.toPlainText(),
            # Only report attaching logs if the section is enabled (i.e., it's a bug report)
            "attach_actions_log": self.attachActionsLogCheckBox.isChecked() and not is_suggestion,
            "attach_main_log": self.attachMainLogCheckBox.isChecked() and not is_suggestion
        }
