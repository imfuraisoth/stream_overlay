# stream_overlay
For twitch stream overlays with player score updating

Includes code for scoreboard UI, overlay for OBS, and backend server processing.

To run, use 'pyserver.bat'


Needed dependencies to be installed:
sudo pip install PyAutoGUI<br />
sudo pip install Pillow --upgrade<br />
sudo pip install -U flask-cors<br />
sudo pip install opencv-python<br />
sudo pip install requests<br />

#Pi Reader Instructions:

Go to terminal and type: sudo raspi-config
Enable SPI under config menu

Install following packages:<br />
sudo pip install mfrc522<br />
sudo pip install RPi.GPIO<br />
sudo pip install python-http-client<br />

Add python run path to /etc/profile to run script on start up
