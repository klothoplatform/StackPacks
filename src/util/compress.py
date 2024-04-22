import os
import zipfile
from io import BytesIO
from pathlib import Path

skip_dirs = {
    "secrets",
    "node_modules",
    "logs",
}


def zip_directory_recurse(io: BytesIO, output_dir: str) -> bytes:
    with zipfile.ZipFile(io, mode="w", compression=zipfile.ZIP_DEFLATED) as out_zip:
        for subdir, dirs, files in os.walk(output_dir):
            subdir = Path(subdir)
            if subdir.name in skip_dirs:
                continue
            for file in files:
                srcpath = subdir / file
                dstpath_in_zip = srcpath.relative_to(output_dir)
                out_zip.writestr(str(dstpath_in_zip), srcpath.read_text())
    return io.getvalue()


def write_zip_to_directory(zip_bytes, target_directory):
    # Create a BytesIO object from the zip bytes
    zip_io = BytesIO(zip_bytes)

    # Create a ZipFile object from the BytesIO object
    with zipfile.ZipFile(zip_io, "r") as zip_file:
        # Extract the contents of the zip file to the target directory
        zip_file.extractall(target_directory)
