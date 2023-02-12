# stream_overlay
For twitch stream overlays with player score updating

Includes code for scoreboard UI, overlay for OBS, and backend server processing.

Needed dependencies to be installed:
sudo pip install PyAutoGUI
sudo pip install Pillow --upgrade
sudo pip install -U flask-cors
sudo pip install opencv-python

#Pi Reader Instructions:

Go to terminal and type: sudo raspi-config
Enable SPI under config menu

Install following packages:
sudo pip install mfrc522
sudo pip install RPi.GPIO
sudo pip install python-http-client

Add python run path to /etc/profile to run script on start up
