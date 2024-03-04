import os
import shutil
import tempfile
from pathlib import Path
from src.util.logging import logger

KEEP_TMP = os.environ.get("KEEP_TMP", False)


class TempDir:
    def __init__(self):
        if KEEP_TMP and KEEP_TMP.lower() != "true":
            tmp_root = Path(KEEP_TMP)
            tmp_root.mkdir(parents=True, exist_ok=True)
            self.dir = tempfile.mkdtemp(dir=tmp_root)
        else:
            self.dir = tempfile.mkdtemp()

        logger.debug(f"Created temp dir {self.dir}")

    def __enter__(self):
        logger.info(f"Using {self.dir} as temp dir")
        return self.dir

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def cleanup(self):
        if not KEEP_TMP:
            logger.debug(f"Cleaning up {self.dir}")
            shutil.rmtree(self.dir)
