import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

from src.util.logging import logger

KEEP_TMP = os.environ.get("KEEP_TMP", False)


@contextmanager
def TempDir():
    if KEEP_TMP and KEEP_TMP.lower() != "true":
        tmp_root = Path(KEEP_TMP)
        tmp_root.mkdir(parents=True, exist_ok=True)
        root = Path(tempfile.mkdtemp(dir=tmp_root))

        latest = tmp_root / "latest"
        latest.unlink(missing_ok=True)
        latest.symlink_to(root.name)
    else:
        root = Path(tempfile.mkdtemp())

    logger.debug(f"Created temp dir {root}")

    try:
        yield root
    finally:
        if not KEEP_TMP:
            logger.debug(f"Cleaning up {root}")
            shutil.rmtree(root)
