import os

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_SMALL_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
FILES_DIR = files_dir = os.path.join(os.path.dirname(__file__), "../../files")