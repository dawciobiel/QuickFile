from PyQt6.QtCore import QObject, QEvent, Qt


class GlobalEventFilter(QObject):
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress:
            print(f"GlobalEventFilter: KeyPress event detected. Key: {event.key()}, Text: {event.text()}, Source: {watched.objectName() if watched.objectName() else watched.__class__.__name__}")
            # Zwróć False, aby pozwolić zdarzeniu propagować dalej do innych filtrów i docelowego widżetu
            return False
        return super().eventFilter(watched, event)
