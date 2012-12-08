#Courtesy of https://github.com/jbaiter/pyomxplayer.git

import pexpect
import re

from threading import Thread
from time import sleep

class OMXPlayer(object):

    _FILEPROP_REXP = re.compile(r".*audio streams (\d+) video streams (\d+) chapters (\d+) subtitles (\d+).*")
    _VIDEOPROP_REXP = re.compile(r".*Video codec ([\w-]+) width (\d+) height (\d+) profile (\d+) fps ([\d.]+).*")
    _AUDIOPROP_REXP = re.compile(r"Audio codec (\w+) channels (\d+) samplerate (\d+) bitspersample (\d+).*")
    _STATUS_REXP = re.compile(r"V :\s*([\d.]+).*")
    _DONE_REXP = re.compile(r"have a nice day.*")

    _LAUNCH_CMD = '/usr/bin/omxplayer -s %s %s'
    _PAUSE_CMD = 'p'
    _TOGGLE_SUB_CMD = 's'
    _QUIT_CMD = 'q'
    _INCREASE_SPEED = '2'
    _DECREASE_SPEED = '1'
    _JUMP_600_REV = '\x1b\x5b\x42'
    _JUMP_600_FWD = '\x1b\x5b\x41'
    _JUMP_30_FWD = '\x1b\x5b\x43'
    _JUMP_30_REV = '\x1b\x5b\x44'

    paused = False
    subtitles_visible = True

    def __init__(self, mediafile, args=None, start_playback=False):
        self.position = 0
        if not args:
            args = ""
        cmd = self._LAUNCH_CMD % (mediafile, args)
        self._process = pexpect.spawn(cmd)
        
        #Set defaults, just in case we dont get them
        self.video = dict()
        self.audio = dict()
        self.video['decoder'] = "unknown"
        self.video['dimensions'] = (0,0)
        self.video['profile'] = 0
        self.video['fps'] = 0
        self.video['streams'] = 0
        self.audio['decoder'] = "unknown"
        self.audio['channels'] = 0
        self.audio['rate'] = 0
        self.audio['bps'] = 0
        self.audio['streams'] = 0
        self.chapters = 0
        self.subtitles = 0
        prop_matches = 0
        self.finished = False

        for i in range (0, 6):
            line = self._process.readline()
            file_props_match = self._FILEPROP_REXP.match(line)
            video_props_match = self._VIDEOPROP_REXP.match(line)
            audio_props_match = self._AUDIOPROP_REXP.match(line)
            status_match = self._STATUS_REXP.match(line)
            if(file_props_match):
                # Get file properties
                file_props = file_props_match.groups()
                (self.audio['streams'], self.video['streams'],
                 self.chapters, self.subtitles) = [int(x) for x in file_props]
                prop_matches += 1
            if(video_props_match):
                # Get video properties
                video_props = video_props_match.groups()
                self.video['decoder'] = video_props[0]
                self.video['dimensions'] = tuple(int(x) for x in video_props[1:3])
                self.video['profile'] = int(video_props[3])
                self.video['fps'] = float(video_props[4])
                prop_matches += 1
            if(audio_props_match):
                # Get audio properties
                audio_props = audio_props_match.groups()
                self.audio['decoder'] = audio_props[0]
                (self.audio['channels'], self.audio['rate'],
                 self.audio['bps']) = [int(x) for x in audio_props[1:]]
                prop_matches += 1
            if(prop_matches >= 3):
                break

        if self.audio['streams'] > 0:
            self.current_audio_stream = 1
            self.current_volume = 0.0

        self._position_thread = Thread(target=self._get_position)
        self._position_thread.start()

        if not start_playback:
            self.toggle_pause()
        self.toggle_subtitles()
        self._playback_speed = 1


    def _get_position(self):
        while True:
            index = self._process.expect([self._STATUS_REXP,
                                            pexpect.TIMEOUT,
                                            pexpect.EOF,
                                            self._DONE_REXP])
            if index == 1: continue
            elif index in (2, 3):
                self.finished = True
                break
            else:
                self.position = float(self._process.match.group(1))
            sleep(0.05)

    def toggle_pause(self):
        if self._process.send(self._PAUSE_CMD):
            self.paused = not self.paused

    def toggle_subtitles(self):
        if self._process.send(self._TOGGLE_SUB_CMD):
            self.subtitles_visible = not self.subtitles_visible
    def stop(self):
        self._process.send(self._QUIT_CMD)
        self._process.terminate(force=True)

    def jump_fwd_30(self):
        self._process.send(self._JUMP_30_FWD)

    def jump_fwd_600(self):
        self._process.send(self._JUMP_600_FWD)

    def jump_rev_30(self):
        self._process.send(self._JUMP_30_REV)

    def jump_rev_600(self):
        self._process.send(self._JUMP_600_REV)

    def increase_speed(self):
        self._process.send(self._INCREASE_SPEED)
        self._playback_speed += 1

    def decrease_speed(self):
        self._process.send(self._DECREASE_SPEED)
        self._playback_speed -= 1
        if (self._playback_speed < 0):
            self._playback_speed = 0

    def set_speed(self, desired):
        if((desired < 0) or (desired > 4)):
            return 0
        if (self._playback_speed > desired):
            function = self.decrease_speed
        elif (self._playback_speed == desired):
            return 0
        else:
            function = self.increase_speed
        while (self._playback_speed != desired):
            function()
        return 1

    def set_audiochannel(self, channel_idx):
        raise NotImplementedError

    def set_subtitles(self, sub_idx):
        raise NotImplementedError

    def set_chapter(self, chapter_idx):
        raise NotImplementedError

    def set_volume(self, volume):
        raise NotImplementedError

    def seek(self, minutes):
        raise NotImplementedError
