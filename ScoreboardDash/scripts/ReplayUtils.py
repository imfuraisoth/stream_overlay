from datetime import datetime
import os
import time

date_time_format = "%Y-%m-%d %H-%M-%S"
last_replay_delete_time = 0
enable_auto_delete = True


def get_replay_videos(prefix, replays_folder):
    global last_replay_delete_time
    videos = [filename for filename in os.listdir(replays_folder) if filename.startswith(prefix)]
    current_time_in_ms = int(time.time() * 1000)
    if last_replay_delete_time == 0:
        last_replay_delete_time = current_time_in_ms
        # First time checking, just return the videos
        return videos
    files_to_delete = []
    result = []
    for video in videos:
        if convert_file_name_to_epoc_time(video, prefix) < last_replay_delete_time:
            # replay too old, delete it
            files_to_delete.append(video)
        else:
            result.append(video)
    delete_replays(files_to_delete, replays_folder, prefix)
    last_replay_delete_time = current_time_in_ms
    return result


def convert_file_name_to_epoc_time(file_name, prefix):
    global date_time_format
    # Convert to datetime object using the correct format
    name_without_ext, _ = os.path.splitext(file_name)
    try:
        dt = datetime.strptime(name_without_ext.removeprefix(prefix).lstrip(), date_time_format)

        # Convert to epoch time in milliseconds
        return int(dt.timestamp() * 1000)
    except Exception as e:
        print(f"Failed to convert file to epoch time: {name_without_ext}. Reason: {e}")
        global last_replay_delete_time
        return last_replay_delete_time


def delete_replays(videos, replays_folder, prefix):
    global enable_auto_delete
    if not enable_auto_delete:
        return

    for filename in videos:
        file_path = os.path.join(replays_folder, filename)
        try:
            if filename.startswith(prefix) and os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")
