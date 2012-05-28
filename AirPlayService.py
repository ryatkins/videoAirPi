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

import sys
import asyncore
import platform
import socket
import threading
import time
import uuid
import re
from datetime import datetime, date
from urlparse import urlparse
from biplist import readPlistFromString
from ZeroconfService import ZeroconfService

__all__ = ["BaseAirPlayRequest", "AirPlayService", "AirPlayProtocolHandler"]

class BaseAirPlayRequest(object):
	def read_from_socket(self, socket):
		data = socket.recv(1024)
		if not data:
			return False

		# we split the message into HTTP headers and content body
		message = data.split("\r\n\r\n", 1)
		headers = message[0]
		headerlines = headers.splitlines()

		# parse request headers
		command = headerlines[0].split()
		self.type = command[0]
		self.uri = command[1]
		self.version = command[2]
		del headerlines[0]
		self.headers = self.parse_headers(headerlines)

		# parse any uri query parameters
		self.params = None
		if (self.uri.find('?')):
			url = urlparse(self.uri)
			if (url[4] is not ""):
				self.params = dict([part.split('=') for part in url[4].split('&') if part.count('=') > 0])
				self.uri = url[2]

		# parse message body
		if (int(self.headers['Content-Length']) > 0):
			self.body = message[1]
			# read more data if we have to
			if len(self.body) < int(self.headers['Content-Length']):
				while 1:
					data = socket.recv(8192)
					if not data:
						break
					self.body = self.body + data

		return True

	def parse_headers(self, lines):
		headers = {}
		plist = []
		for line in lines:
			match = re.search(r'bplist|\x00', line)
			if match:
				plist.append(line)
			else:
				if line:
					name, value = line.split(": ", 1)
					headers[name.strip()] = value.strip()
		if len(plist):
			try:
				values = readPlistFromString('\r'.join(plist))
				for key in values:
					headers[key] = values[key]
			except (Exception), e:
				print "Not a plist:", e
		return headers

class AirPlayProtocolHandler(asyncore.dispatcher_with_send):
	def __init__(self, socket, service):
		asyncore.dispatcher_with_send.__init__(self, socket)
		self.service = service

	def handle_read(self):
		# read from the socket and parse a HTTP request
		request = BaseAirPlayRequest()
		if (not request.read_from_socket(self)):
			return

		answer = ""

		# process the request and run the appropriate callback
		if (request.uri.find('/playback-info')>-1):
			self.playback_info()
			content = '<?xml version="1.0" encoding="UTF-8"?>\
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\
<plist version="1.0">\
<dict>\
<key>duration</key>\
<real>%f</real>\
<key>position</key>\
<real>%f</real>\
<key>rate</key>\
<real>%f</real>\
<key>playbackBufferEmpty</key>\
<%s/>\
<key>playbackBufferFull</key>\
<false/>\
<key>playbackLikelyToKeepUp</key>\
<true/>\
<key>readyToPlay</key>\
<%s/>\
<key>loadedTimeRanges</key>\
<array>\
    <dict>\
        <key>duration</key>\
        <real>%f</real>\
        <key>start</key>\
        <real>0.000000</real>\
    </dict>\
</array>\
<key>seekableTimeRanges</key>\
<array>\
    <dict>\
        <key>duration</key>\
        <real>%f</real>\
        <key>start</key>\
        <real>0.000000</real>\
    </dict>\
</array>\
</dict>\
</plist>'
			d, p = self.service.get_scrub()
			if (d+p == 0):
				playbackBufferEmpty = 'true'
				readyToPlay = 'false'
			else:
				playbackBufferEmpty = 'false'
				readyToPlay = 'true'

			content = content % (float(d), float(p), int(self.service.is_playing()), playbackBufferEmpty, readyToPlay, float(d), float(d))
			answer = self.create_request(200, "Content-Type: text/x-apple-plist+xml", content)
		elif (request.uri.find('/play')>-1):
			parsedbody = request.parse_headers(request.body.splitlines())
			self.service.play(parsedbody['Content-Location'], float(parsedbody['Start-Position']))
			answer = self.create_request()
		elif (request.uri.find('/stop')>-1):
			self.service.stop(request.headers)
			answer = self.create_request()
		elif (request.uri.find('/scrub')>-1):
			if request.type == 'GET':
				d, p = self.service.get_scrub()
				content = "duration: " + str(float(d))
				content += "\nposition: " + str(float(p))
				answer = self.create_request(200, "", content)
			elif request.type == 'POST':
				self.service.set_scrub(float(request.params['position']))
				answer = self.create_request()
		elif (request.uri.find('/reverse')>-1):
			self.service.reverse(request.headers)
			answer = self.create_request(101)
		elif (request.type == 'POST' and request.uri.find('/rate')>-1):
			self.service.rate(float(request.params['value']))
			answer = self.create_request()
		elif (request.type == 'PUT' and request.uri.find('/photo')>-1):
			self.photo(request.body, request.headers['X-Apple-Transition'])
			answer = self.create_request()
		elif (request.uri.find('/slideshow-features')>-1):
			answer = self.create_request(404)
		elif (request.type == 'GET' and request.uri.find('/server-info')>-1):
			self.server_info()
			content = '<?xml version="1.0" encoding="UTF-8"?>\
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\
<plist version="1.0">\
<dict>\
<key>deviceid</key>\
<string>%s</string>\
<key>features</key>\
<integer>%d</integer>\
<key>model</key>\
<string>%s</string>\
<key>protovers</key>\
<string>1.0</string>\
<key>srcvers</key>\
<string>101.10</string>\
</dict>\
</plist>'
			content = content % (self.service.deviceid, self.service.features, self.service.model)
			answer = self.create_request(200, "Content-Type: text/x-apple-plist+xml", content)
		elif (request.uri.find("/setProperty")>-1):
			anert = self.create_request()
		else:
			print >> sys.stderr, "ERROR: AirPlay - Unable to handle request \"%s\"" % (request.uri)
			answer = self.create_request(404)

		if(answer is not ""):
			self.send(answer)

	def get_datetime(self):
		today = datetime.now()
		datestr = today.strftime("%a, %d %b %Y %H:%M:%S")
		return datestr+" GMT"

	def create_request(self, status = 200, header = "", body = ""):
		clength = len(bytes(body))
		if (status == 200):
			answer = "HTTP/1.1 200 OK"
		elif (status == 404):
			answer = "HTTP/1.1 404 Not Found"
		elif (status == 101):
			answer = "HTTP/1.1 101 Switching Protocols"
			answer += "\nUpgrade: PTTH/1.0"
			answer += "\nConnection: Upgrade"
		answer += "\nDate: " + self.get_datetime()
		answer += "\nContent-Length: " + str(clength)
		if (header != ""):
			answer += "\n" + header
		answer +="\n\n"
		answer += body
		return answer

	def get_scrub(self):
		return False

	def set_scrub(self, position):
		return False

	def server_info(self):
		return False

	def playback_info(self):
		return False

	def play(self, location, position):
		return False

	def stop(self, info):
		return False

	def reverse(self, info):
		return True

	def slideshow_features(self):
		return False

	def photo(self, data, transition):
		return False

	def rate(self, speed):
		return False

	def volume(self, info):
		return False

	def authorize(self, info):
		return False

	def event(self, info):
		return False

class AsyncoreThread(threading.Thread):
	def __init__(self, timeout=30.0, use_poll=0,map=None):
		self.flag = True
		self.timeout = 30.0
		self.use_poll = use_poll
		self.map = map
		threading.Thread.__init__(self, None, None, 'asyncore thread')

	def run(self):
		self.loop()

	def loop(self):
		if self.map is None:
			self.map = asyncore.socket_map

		if self.use_poll:
			if hasattr(select, 'poll'):
				poll_fun = asyncore.poll3
			else:
				poll_fun = asyncore.poll2
		else:
			poll_fun = asyncore.poll

		while self.map and self.flag:
			poll_fun(self.timeout,self.map)

	def end(self):
		self.flag=False
		self.map=None

class AirPlayService(asyncore.dispatcher):
	def __init__(self, name=None, host="0.0.0.0", port=22555):
		# create socket server
		asyncore.dispatcher.__init__(self)
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.set_reuse_addr()
		self.bind((host, port))
		self.listen(5)
		self.remote_clients = []
		macstr = "%012X" % uuid.getnode()
		self.deviceid = ''.join("%s:" % macstr[i:i+2] for i in range(0, len(macstr), 2))[:-1]
		self.features = 0x07 # 0x77 on iOS 4.3.1
		self.model = "AppleTV2,1"

		# create avahi service
		if (name is None):
			name = "Airplay Service on " + platform.node()
		self.zeroconf_service = ZeroconfService(name, port=port, stype="_airplay._tcp", text=["deviceid="+self.deviceid,"features="+hex(self.features),"model="+self.model])

		# publish avahi service
		self.zeroconf_service.publish()

		# do this so we do not block the main thread
		self.thread = AsyncoreThread(timeout=30)
		self.thread.is_finished = False
		self.thread.start()

		print "AirPlayService running"

	def handle_accept(self):
		pair = self.accept()
		if pair is None:
			pass
		else:
			sock, addr = pair
			self.remote_clients.append(AirPlayProtocolHandler(sock, self))

	def handle_close(self):
		self.close()

	def __del__(self):
		self.thread.end()
		self.close()
		del self.thread

		# unpublish avahi service
		self.zeroconf_service.unpublish()

