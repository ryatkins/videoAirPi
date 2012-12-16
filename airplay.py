# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Martin S. <opensuse@sukimashita.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL 
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import platform, sys, signal
import socket, fcntl, struct
import time
from AirPlayService import AirPlayService
from pyomxplayer import OMXPlayer

class AirPlay:

	playing = False
	seekable = False
	action_play = False
	action_play_pause = False
	add_to_playlist_and_play = ""
	action_stop = False
	action_seek_time = 0
	omxArgs = ''

	def __init__ (self):
		args = len(sys.argv)
		if args > 1:
			if sys.argv[1] == "jack":
				self.omxArgs = ''
				print "Audio output over 3,5mm jack"
		else:
			self.omxArgs = '-o hdmi'
			print "Audio output over HDMI"


		self.totem = None
		self.totem = self
		self.omx = None

		self.totem.service = VideoAirPlayPlayer(totem=self.totem,name="AirPi on %s" % (platform.node()), host=self.get_ip_address('eth0'), port=8000)

	def signal_handler(self, signal, frame):
		print '\nQuiting - please wait....'
		self.Stop()
		self.totem.service.exit()
		sys.exit(0)
		
	def get_ip_address(self,ifname):
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		return socket.inet_ntoa(fcntl.ioctl(
			s.fileno(),
			0x8915,  # SIOCGIFADDR
			struct.pack('256s', ifname[:15])
		)[20:24])

	def PlayMedia(self, fullpath, startPosition): #, tag, unknown1, unknown2, unknown3):
		global parsed_path
		global media_key
		global duration
		
		#print startPosition
#		print 'Args'
#		print self.omxArgs
		
		if (startPosition != 0):
			self.omxArgs += " -f " + str(startPosition)
#			print self.omxArgs
		
		if(self.omx):
			self.Stop()
		print fullpath
		self.omx = OMXPlayer(fullpath, args=self.omxArgs, start_playback=True)
	
	def Pause(self, message):
		if(self.omx):
			self.omx.set_speed(1)
			self.omx.toggle_pause()

	def Play(self, message):
		if(self.omx):
			ret = self.omx.set_speed(1)
			if(ret == 0):
				self.omx.toggle_pause()

	def Stop(self, message=""):
		if(self.omx):
			self.omx.stop()
			self.omx = None

	def do_activate (self):
		pass

	def do_deactivate (self):
		self.totem.service.__del__()

	def is_playing (self):
		return self.playing

	def get_property (self, propertyType):
		return 100

	def action_stop (self):
		pass

	def action_play (self):
		pass

	def is_seekable (self):
		return self.seekable

class VideoAirPlayPlayer(AirPlayService):
	def __init__(self, totem, name=None, host="0.0.0.0", port=22555):
		self.location = None
		self.totem = totem
		AirPlayService.__init__(self, name, host, port)
		print "Video AirPlay service started on " + host + ":" + str(port)

	def __del__(self):
		self.totem.action_stop()
		AirPlayService.__del__(self)

	# this returns current media duration and current seek time
	def get_scrub(self):
		# return self.totem.stream-length, self.totem.current-time
		duration = self.totem.omx.length
		position = self.totem.omx._get_position()
		print position
		return duration, position

	def is_playing(self):
		return self.totem.is_playing()

	# this must seek to a certain time
	def set_scrub(self, position):
		if self.totem.is_seekable():
			print 'seekable code'

	# this only sets the location and start position, it does not yet start to play
	def play(self, location, position):
		# start position is in percent
		self.location	= [location, position]

	# stop the playback completely
	def stop(self, info):
		print 'stop code'
		self.totem.omx.stop()

	# reverse HTTP to PTTH
	def reverse(self, info):
		pass

	# playback rate, 0.0 - 1.0
	def rate(self, speed):
		if (int(float(speed)) >= 1):
			if self.location is not None:
				timeout = 5
				# start playback and loading of media


				# wait until stream-length is loaded and is not zero
				duration = 0
				#while (int(duration) == 0 and timeout > 0):
				#	time.sleep(1)
				#	duration = float(self.totem.get_property('stream-length') / 1000)
				#	timeout -= 1
				# we also get a start time from the device
				targetoffset = float(duration * float(self.location[1]))
				#position = self.totem.omx._get_position()
				# only seek to it if it's above current time, since the video is already playing
				#if (targetoffset > position):
					#self.set_scrub(targetoffset)

			if (not self.totem.is_playing()):
				print 'play code'
				print self.location[1]
				self.totem.PlayMedia(self.location[0], self.location[1])


			del self.location
			self.location = None
		else:
			print 'play_pause'
			self.totem.omx.toggle_pause()



myAirplay = AirPlay()

signal.signal(signal.SIGINT, myAirplay.signal_handler)
signal.pause()

