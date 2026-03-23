from scripts.FileUtils import FileUtils

message_data_file = "../data/custom_messages_data.json"


def save_message_data(data):
    FileUtils.write_file(message_data_file, data)


def get_message_data():
    return FileUtils.read_file(message_data_file)
