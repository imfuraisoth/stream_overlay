from io import open
from pathlib import Path
import json, os
from filelock import FileLock


# Optional observer: set FileUtils.on_write = fn(file_path) to be
# notified after every successful write (used for live page sync)
class FileUtils:

    on_write = None

    def __init__(self):
        raise Exception("Utility class")

    @staticmethod
    def read_file(file_name):
        file_path = Path(file_name)
        if not file_path.exists():
            file_path.write_text("{}")  # Creates the file
            print(file_name + " file created successfully.")

        try:
            with open(file_name, "r", encoding="utf-8") as json_file:
                return json.load(json_file)
        except Exception as e:
            print("Error opening file", e)
            return {}

    @staticmethod
    def write_file(file_path, data):
        lock = FileLock(file_path + ".lock")
        temp_file = file_path + ".tmp"

        with lock:
            with open(temp_file, "w", encoding="utf-8") as f:
                data_to_write = json.dumps(data, ensure_ascii=False)
                f.write(data_to_write)

            os.replace(temp_file, file_path)
            if FileUtils.on_write:
                try:
                    FileUtils.on_write(file_path)
                except Exception:
                    pass

    @staticmethod
    def list_files(directory):
        files = []
        for entry in os.listdir(directory):
            full_path = os.path.join(directory, entry)
            if os.path.isfile(full_path):
                files.append(full_path)
        return files

    @staticmethod
    def list_files_no_ext(directory):
        return [f.stem for f in Path(directory).iterdir() if f.is_file()]

    @staticmethod
    def find_file_name(directory, name):
        for f in Path(directory).iterdir():
            if f.is_file() and f.stem == name:
                return f.name  # filename with extension
        print("No file found with name: " + name)
        return None