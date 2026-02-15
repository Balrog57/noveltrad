from abc import ABC, abstractmethod

class FormatHandler(ABC):
    @abstractmethod
    def read(self, file_path):
        """Reads the file and returns a list of text segments."""
        pass

    @abstractmethod
    def write(self, file_path, segments, original_file_path=None):
        """Writes the segments to the file, preserving format if possible."""
        pass

    @abstractmethod
    def get_supported_extensions(self):
        """Returns a list of supported file extensions (e.g. ['.epub', '.zip'])."""
        pass
