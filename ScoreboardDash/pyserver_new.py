import json
from io import open
from flask import Flask
from flask import request
from flask_cors import CORS

hostName = "localhost"
serverPort = 8080

stream_control_file = "../scoreboard/sc/streamcontrol.json"
player_1 = "../data/player1.txt"
player_2 = "../data/player2.txt"
next_player_1 = "../data/nextplayer1.txt"
next_player_2 = "../data/nextplayer2.txt"
result1 = "../data/result1.txt"
result2 = "../data/result2.txt"
result_name_1 = "../data/resultname1.txt"
result_name_2 = "../data/resultname2.txt"

api = Flask(__name__)
CORS(api)

@api.route('/getdata', methods=['GET'])
def get_data():
    return json.dumps(read_file(stream_control_file), ensure_ascii=False), 200

@api.route('/updatealldata', methods=['POST'])
def update_all_data():
    json_data = request.get_json()
    with open(stream_control_file, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(json_data))
    write_to_file(player_1, "p1Name", json_data)
    write_to_file(player_2, "p2Name", json_data)
    write_to_file(next_player_1, "nextplayer1", json_data)
    write_to_file(next_player_2, "nextplayer2", json_data)
    write_to_file(result1, "resultscore1", json_data)
    write_to_file(result2, "resultscore2", json_data)
    write_to_file(result_name_1, "resultplayer1", json_data)
    write_to_file(result_name_2, "resultplayer2", json_data)
    return "200"


@api.route('/updateplayer1', methods=['POST'])
def update_player1():
    json_data = request.get_json()
    write_to_file(player_1, "p1Name", json_data)
    full_data = json.loads(read_file(stream_control_file))
    full_data["p1Name"] = get_name_from_id_map(json_data["id"])
    with open(stream_control_file, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(full_data, ensure_ascii=False))
    return "200"    
    

@api.route('/updateplayer2', methods=['POST'])
def update_player2():
    json_data = request.get_json()
    write_to_file(player_2, "p2Name", json_data)
    full_data = json.loads(read_file(stream_control_file))
    full_data["p2Name"] = get_name_from_id_map(json_data["id"])
    with open(stream_control_file, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(full_data, ensure_ascii=False))
    return "200"


def write_to_file(file_name, data_key, json_data):
    file = open(file_name, "w")
    file.write(json_data[data_key])
    file.close()


def get_name_from_id_map(id):
    id_map = read_file("id_map.txt")
    name = id_map[str(id)]
    if name:
        return name
    print("No name associated with id: " + str(id))    
    return str(id)
    

def read_file(file_name):
    with open(file_name) as json_file:
        line = json_file.readline()
        result = json.loads(line)
        json_file.close()
        return result


if __name__ == "__main__":
    try:
        print("Now we talk'n, server started ...")
        api.run(host=hostName, port=serverPort)
    except KeyboardInterrupt:
        pass
