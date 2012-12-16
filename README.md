#videoAirPi

##Introduction
Video AirPlay on the Raspberry Pi

##Before you install

	sudo apt-get update && sudo apt-get upgrade
	sudo apt-get install avahi-daemon
	sudo apt-get install python-pip
	sudo pip install pexpect
	sudo apt-get install python-avahi
	sudo apt-get install git


##Install
	cd ~   (to your home directory or wherever you want this installed)
	git clone https://github.com/ryatkins/videoAirPi.git

##Usage
Defaults to audio over HDMI:

	python airplay.py

Audio over 3.5 jack:

	python airplay.py jack

##Issues
- Seeking does not work at the beginning or during (omxplayer does not support seeking in HLS streams)
- Controls don't work from the iPad to Pause / Play
- Random exceptions are thrown

##Help

Video keeps playing after I hit CTRL+c, use this kill command:

	kill $(ps aux | grep '[/]usr/bin/omxplayer.bin' | awk '{print $2}')

##Contributors
Code largely borrowed from Totem AirPlay Plugin: https://github.com/dveeden/totem-plugin-airplay

OMXplayer interface from: https://github.com/megawubs/pyplex && https://github.com/jbaiter/pyomxplayer.git

