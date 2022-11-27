import json
from io import open
from http.server import BaseHTTPRequestHandler, HTTPServer

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

class LocalServer(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept")
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(bytes(json.dumps(read_file(), ensure_ascii=False), 'utf-8'))

    def do_POST(self):
        self.send_response(200, "ok")
        self.send_header("Content-type", "application/json")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        length = int(self.headers['Content-Length'])
        payload = self.rfile.read(length).decode('utf-8')
        with open(stream_control_file, 'w', encoding="utf-8") as json_file:
            json_file.write(payload)

        json_data = json.loads(payload)
        write_to_file(player_1, "p1Name", json_data)
        write_to_file(player_2, "p2Name", json_data)
        write_to_file(next_player_1, "nextplayer1", json_data)
        write_to_file(next_player_2, "nextplayer2", json_data)
        write_to_file(result1, "resultscore1", json_data)
        write_to_file(result2, "resultscore2", json_data)
        write_to_file(result_name_1, "resultplayer1", json_data)
        write_to_file(result_name_2, "resultplayer2", json_data)


def write_to_file(file_name, data_key, json_data):
    file = open(file_name, "w")
    file.write(json_data[data_key])
    file.close()


def read_file():
    with open(stream_control_file) as json_file:
        line = json_file.readline()
        result = json.loads(line)
        json_file.close()
        return result


if __name__ == "__main__":
    webServer = HTTPServer((hostName, serverPort), LocalServer)
    try:
        print("Now we talk'n, server started ...")
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass
    webServer.server_close()
