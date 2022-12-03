import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import http.client
import json, time, traceback

#3 second window for sending score update requests
input_window = 3

ENDPOINT = "/updateplayer1"

rfid = SimpleMFRC522()

client = http.client.HTTPConnection('192.168.0.133', 8080, timeout=3)
headers = {'Content-type': 'application/json'}

last_id = (0, 0.0)

def get_endpoint(id):
  global last_id
  print(last_id)
  previous_id, previous_timestamp = last_id
  current_time = time.time()
  if id != previous_id:
    last_id = (id, current_time)
    return ENDPOINT
  
  if id == previous_id and (current_time - input_window) > previous_timestamp:
    # Only send something when past window to avoid accidental multiple taps
    last_id = (id, current_time)
    return ENDPOINT
  
  return None


while True:
  id, text = rfid.read()
  print(id)
  try:
    data = {"id": id}
    json_data = json.dumps(data)
    endpoint = get_endpoint(id)
    print(endpoint)
    if endpoint != None:
      client.request("POST", endpoint, json_data, headers)
      response = client.getresponse()
      print(response.read().decode())
  except:
    print("Failed to update server info")
    traceback.print_exc()
    
