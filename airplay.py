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

from gi.repository import GObject
from gi.repository import Totem
from gi.repository import Peas
from gi.repository import Gtk
import platform
import time
from AirPlayService import AirPlayService

class AirPlay (GObject.Object, Peas.Activatable):
	__gtype_name__ = 'AirPlay'

	object = GObject.property(type = GObject.Object)

	def __init__ (self):
		GObject.Object.__init__ (self)
		self.totem = None

	def do_activate (self):
		self.totem = self.object
		self.totem.service = AirPlayTotemPlayer(totem = self.totem, name = "Totem on %s" % (platform.node()))

	def do_deactivate (self):
		self.totem.service.__del__()

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

	def is_playing(self):
		return self.totem.is_playing()

	# this must seek to a certain time
	def set_scrub(self, position):
		if self.totem.is_seekable():
			gobject.idle_add(self.totem.action_seek_time, int(float(position) * 1000), False)

	# this only sets the location and start position, it does not yet start to play
	def play(self, location, position):
		# start position is in percent
		self.location	= [location, position]

	# stop the playback completely
	def stop(self, info):
		gobject.idle_add(self.totem.action_stop)

	# reverse HTTP to PTTH
	def reverse(self, info):
		pass

	# playback rate, 0.0 - 1.0
	def rate(self, speed):
		if (int(float(speed)) >= 1):
			if self.location is not None:
				timeout = 5
				# start playback and loading of media
				gobject.idle_add(self.totem.add_to_playlist_and_play, self.location[0], "AirPlay Video", False)
				# wait until stream-length is loaded and is not zero
				duration = 0
				while (int(duration) == 0 and timeout > 0):
					time.sleep(1)
					duration = float(self.totem.get_property('stream-length') / 1000)
					timeout -= 1
				# we also get a start time from the device
				targetoffset = float(duration * float(self.location[1]))
				position = float(self.totem.get_property('current-time') / 1000)
				# only seek to it if it's above current time, since the video is already playing
				if (targetoffset > position):
					self.set_scrub(targetoffset)

			if (not self.totem.is_playing()):
				gobject.idle_add(self.totem.action_play)

			del self.location
			self.location = None
		else:
			gobject.idle_add(self.totem.action_pause)

