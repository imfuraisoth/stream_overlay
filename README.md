# stream_overlay
For twitch stream overlays with player score updating

Includes code for scoreboard UI, overlay for OBS, and backend server processing.

Needed dependencies to be installed:
pip install PyAutoGUI
pip install Pillow --upgrade
pip install opencv-python

#Pi Reader Instructions
Go to terminal and type: sudo raspi-config
Enable SPI under config menu

Install following packages:
pip install mfrc522
pip install RPi.GPIO
pip install python-http-client

Add python run path to crontab -e to run script on start up
