import http.client
from io import open
import json
import argparse

server_info = open('../../config/serverip.txt', 'r').readline().split(':')

hostName = server_info[0]
serverPort = int(server_info[1])

client = http.client.HTTPConnection(hostName, serverPort, timeout=3)
headers = {'Content-type': 'application/json'}


def call_endpoint(endpoint):
    client.request("POST", endpoint, json.dumps("{}"), headers)


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description = 'Scoreboard python client')
        parser.add_argument("-r", "--r", action='store_true', dest='TriggerClientRefresh', help="Triggers a client side refresh")
        parser.add_argument("-a1", "--a1", action='store_true', dest='AddP1Score', help="Add 1 to player 1 score")
        parser.add_argument("-a2", "--a2", action='store_true', dest='AddP2Score', help="Add 1 to player 2 score")
        parser.add_argument("-s1", "--s1", action='store_true', dest='SubP1Score', help="Subtract 1 to player 1 score")
        parser.add_argument("-s2", "--s2", action='store_true', dest='SubP2Score', help="Subtract 1 to player 2 score")
        parser.add_argument("-deleteclips", "--deleteclips", action='store_true', dest='DeleteClips', help="Deletes all the clip files out of the clips directory")
        parser.add_argument("-saveclips", "--saveclips", action='store_true', dest='SaveClips', help="Move all the clip files from the clips directory to another for later use")

    # Read arguments from command line
        args = parser.parse_args()
        if args.TriggerClientRefresh:
            call_endpoint("/triggerClientRefresh")
        elif args.AddP1Score:
            call_endpoint("/addPlayer1Score")
        elif args.AddP2Score:
            call_endpoint("/addPlayer2Score")
        elif args.SubP1Score:
            call_endpoint("/subPlayer1Score")
        elif args.SubP2Score:
            call_endpoint("/subPlayer2Score")
        elif args.DeleteClips:
            call_endpoint("/deleteclips")
        elif args.SaveClips:
            call_endpoint("/saveclips")
    except KeyboardInterrupt:
        pass
