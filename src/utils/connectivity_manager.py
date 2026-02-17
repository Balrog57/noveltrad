import socket
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

class ConnectivityManager(QObject):
    """
    Monitors internet connectivity and notifies the application.
    Used for implementing the Offline 'Rescue' Mode.
    """
    status_changed = pyqtSignal(bool) # True = Online, False = Offline
    
    def __init__(self, check_interval=30000, parent=None):
        super().__init__(parent)
        self.is_online = True
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_connectivity)
        self.timer.start(check_interval)
        
        # Initial check
        self.check_connectivity()

    def check_connectivity(self):
        """
        Perform a quick check to see if internet is available.
        Standard approach: try to resolve a major DNS address.
        """
        try:
            # We use Cloudflare's 1.1.1.1 or Google's 8.8.8.8
            # socket.create_connection is more reliable than gethostbyname sometimes
            socket.create_connection(("1.1.1.1", 53), timeout=3)
            new_status = True
        except (socket.error, OSError):
            new_status = False
            
        if new_status != self.is_online:
            self.is_online = new_status
            self.status_changed.emit(self.is_online)
            
        return self.is_online
