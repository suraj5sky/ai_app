from pathlib import Path
import os

class PathManager:
    def __init__(self, base_dir=None):
        """Initialize with a base directory (default: project root)."""
        self.base_dir = Path(base_dir) if base_dir else self._get_project_root()

    @staticmethod
    def _get_project_root():
        """Get the project root directory (where app.py is located)."""
        return Path(__file__).parent.parent  # Adjust based on your project structure

    def get_path(self, *path_parts, ensure_exists=False):
        """Construct an absolute path and optionally ensure it exists."""
        full_path = self.base_dir.joinpath(*path_parts)
        if ensure_exists:
            full_path.parent.mkdir(parents=True, exist_ok=True)
        return full_path

    def resolve_path(self, path):
        """Convert string/Path to absolute Path."""
        path = Path(path) if isinstance(path, str) else path
        if not path.is_absolute():
            path = self.base_dir / path
        return path

# Singleton instance for easy access
path_manager = PathManager()