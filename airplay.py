# -*- coding: utf-8 -*-

import totem
import platform
import time
from AirPlayService import AirPlayService

class AirPlayPlugin (totem.Plugin):
	def __init__ (self):
		totem.Plugin.__init__ (self)
		self.totem = None

	def activate (self, totem_object):
		self.service = AirPlayTotemPlayer(totem=totem_object,name="Totem on %s" % (platform.node()))

	def deactivate (self, totem_object):
		self.service.__del__()

class AirPlayTotemPlayer(AirPlayService):
	def __init__(self, totem, name=None, host="0.0.0.0", port=22555):
		self.location = None
		self.totem = totem
		AirPlayService.__init__(self, name, host, port)

	def __del__(self):
		self.totem.action_stop()
		AirPlayService.__del__(self)

	# this returns current media duration and current seek time
	def get_scrub(self):
		# return self.totem.stream-length, self.totem.current-time
		duration = float(self.totem.get_property('stream-length') / 1000)
		position = float(self.totem.get_property('current-time') / 1000)
		return duration, position

	# this must seek to a certain time
	def set_scrub(self, position):
		if self.totem.is_seekable():
			self.totem.action_seek_time(int(float(position) * 1000))

	# this only sets the location and start position, it does not yet start to play
	def play(self, location, position):
		# start position is in percent
		self.location	= [location, position]

	# stop the playback completely
	def stop(self, info):
		self.totem.action_stop()

	# reverse HTTP to PTTH
	def reverse(self, info):
		pass

	# playback rate, 0.0 - 1.0
	def rate(self, speed):
		if (int(float(speed)) >= 1):
			if self.location is not None:
				# start playback and loading of media
				self.totem.add_to_playlist_and_play(self.location[0], "AirPlay Video", False)
				# wait until stream-length is loaded and is not zero
				duration = 0
				while (int(duration) == 0):
					duration = float(self.totem.get_property('stream-length') / 1000)
					time.sleep(1)
				# we also get a start time from the device
				targetoffset = float(duration * float(self.location[1]))
				position = float(self.totem.get_property('current-time') / 1000)
				# only seek to it if it's above current time, since the video is already playing
				if (targetoffset > position):
					self.set_scrub(targetoffset)

			if (not self.totem.is_playing()):
				self.totem.action_play()

			del self.location
			self.location = None
		else:
			self.totem.action_pause()

