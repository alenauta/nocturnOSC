"""
# Copyright (C) 2009 ST8 <st8@q3f.org>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# For questions regarding this module contact
# ST8 <st8@q3f.org> or visit http://monome.q3f.org
"""

from Program import Program
import Live

class Looper(Program):
    """
    Modifies a loop length and position for a currently playing clip in
    a track. Quantised without needing a fast callback
    """
    name = "Looper"
    
    def __init__(self, parent, width, height):
        self.width = width
        self.height = height    
    
        self.parent = parent
        self.c_instance = parent.c_instance
        self.oscServer = parent.oscServer
        
        self.clisten = {}
        self.slisten = {}        
        
        self._last = 0
        
        self.visible_tracks = {}
        self.reset  = []
        
        self.shift = 1

        self.step   = 0
        self.sindex = [0.25,0.5,1,2,4,6,8,10,12]
        
        self.precords = [0 for i in range(self.height - 2)]
        self.patterns = [{} for i in range(self.height - 2)]
        
        self.do_refresh_state()

        self.song().add_is_playing_listener(self.reset_pos)
        self.get_time = self.c_instance.song().get_current_beats_song_time

    def rem_listeners(self):
        self.log("** Remove Listeners **")
    
        for slot in self.slisten:
            if slot != None:
                if slot.has_clip_has_listener(self.slisten[slot]) == 1:
                    slot.remove_has_clip_listener(self.slisten[slot])
    
        self.slisten = {}
        
        for clip in self.clisten:
            if clip != None:
                if clip.playing_status_has_listener(self.clisten[clip]) == 1:
                    clip.remove_playing_status_listener(self.clisten[clip])
                
        self.clisten = {}
        
    def reset_pos(self):
        if self.c_instance != None:
            if self.song().is_playing == 0:
                for i in range(len(self.visible_tracks)):
                    self.visible_tracks[i].stime = self._last
        
    def add_listeners(self):
        self.rem_listeners()
        tracks = self.getslots()
    
        for track in range(len(tracks)):
            for clip in range(len(tracks[track])):
                c = tracks[track][clip]
                if c.clip != None:
                    self.add_cliplistener(c.clip, track, clip)
                else:
                    self.add_slotlistener(c, track, clip)
        
    def add_cliplistener(self, clip, tid, cid):
        cb = lambda :self.clip_changestate(clip, tid, cid)
        
        if self.clisten.has_key(clip) != 1:
            clip.add_playing_status_listener(cb)
            self.clisten[clip] = cb
        
    def add_slotlistener(self, slot, tid, cid):
        cb = lambda :self.slot_changestate(slot, tid, cid)
        
        if self.slisten.has_key(slot) != 1:
            slot.add_has_clip_listener(cb)
            self.slisten[slot] = cb
        
    def slot_changestate(self, slot, tid, cid):
        lcd = 0
        # Added new clip
        if slot.clip != None:
            if slot.clip.is_playing == 1:
                self.visible_tracks[tid].update(cid, self._last, slot.clip.looping, slot.clip.loop_start, slot.clip.loop_end - slot.clip.loop_start, str(slot.clip.name))
                lcd = 1
            self.add_cliplistener(slot.clip, tid, cid)
        else:
            if self.visible_tracks[tid].cid == cid:
                self.visible_tracks[tid].update()
                lcd = 1
        
            if self.clisten.has_key(slot.clip) == 1:
                slot.clip.remove_playing_status_listener(self.clisten[slot.clip])
                
        if lcd == 1:
            self.build_lcd()
        
    def clip_changestate(self, clip, tid, cid):
        lcd = 0
        if clip.is_triggered != 1:
            if clip.is_playing == 1:
                if self.visible_tracks[tid].cid != cid and self.visible_tracks[tid].looping == 0 and self.visible_tracks[tid].cid > -1:
                    self.reset.append([tid, self.visible_tracks[tid].cid, self.visible_tracks[tid].start, self.visible_tracks[tid].length])  
                
                if self.visible_tracks[tid].cid != cid:
                    self.visible_tracks[tid].update(cid, self._last, clip.looping, clip.loop_start, clip.loop_end - clip.loop_start, str(clip.name))
        
            elif clip.is_playing == 0 and clip.looping == 1:
                if self.visible_tracks[tid].cid == cid and self.visible_tracks[tid].current_step > -1:
                    self.reset.append([tid, cid, self.visible_tracks[tid].start, self.visible_tracks[tid].length])                
                
                self.visible_tracks[tid].update()
            
            self.build_lcd()
        
        self.log("clip: " + str(cid) + " playing: " + str(clip.is_playing) + " trig: " + str(clip.is_triggered))
            
    def do_refresh_state(self):
        self.limits()
        tracks = self.getslots()
    
        for track in range(len(tracks)):
            # Reset old tracks
            if self.visible_tracks.has_key(track):
                if self.visible_tracks[track].cid > -1:
                    self.reset.append([track, self.visible_tracks[track].cid, self.visible_tracks[track].start, self.visible_tracks[track].length])
            
            self.visible_tracks[track] = Track()
            
            for clip in range(len(tracks[track])):
                c = tracks[track][clip]
                if c.clip != None:
                    if c.clip.is_playing == 1:
                        self.visible_tracks[track].update(clip, 0, c.clip.looping, c.clip.loop_start, c.clip.loop_end - c.clip.loop_start, str(c.clip.name))
                    
        self.add_listeners()
        
    def do_update_display(self):
        cols = []
        time = self.song().get_current_beats_song_time()
        beat = time.beats
        sub  = time.sub_division
        
        for y in range(self.width):
            tr = y + self.track
            
            if y == self.width - 1:
                if self.step == 1:
                    cols.append(1 << self.height - 2)
            
            if y < self.twidth and self.visible_tracks.has_key(tr):
                if self.visible_tracks[tr].cid > -1:
                    clip = self.song().visible_tracks[tr].clip_slots[self.visible_tracks[tr].cid].clip
                else:
                    clip = None
                
                if self.step == 1:
                    byte = 1 << self.visible_tracks[tr].step_size
                    if clip != None:
                        if clip.is_playing == 1 and sub % 3 == 1:
                            byte += 1 << self.height - 1
                        elif clip.is_playing == 0 and beat % 2 == 0:
                            byte += 1 << self.height - 1
                        
                    cols.append(byte)
                else:
                    byte = 0

                    if self.visible_tracks[tr].cid > -1:
                        if self.visible_tracks[tr].length == clip.length:
                        #if self.visible_tracks[tr].current_step == -1:
                            if self.visible_tracks[tr].looping == 1 and self.visible_tracks[tr].start != 0:
                                if self._last > (self.visible_tracks[tr].stime + self.visible_tracks[tr].start):
                                    pos = int((((self._last - self.visible_tracks[tr].stime - self.visible_tracks[tr].start) % self.visible_tracks[tr].length) / self.visible_tracks[tr].length) * self.height)
                                else:
                                    pos = int((((self._last - self.visible_tracks[tr].stime) % self.visible_tracks[tr].start) / self.visible_tracks[tr].start) * self.height)
                            else:
                                pos = int((((self._last - self.visible_tracks[tr].stime) % self.visible_tracks[tr].length) / self.visible_tracks[tr].length) * self.height)
                                    
                            byte = 1 << pos
                        else:
                            dif = 0
                            if (self.visible_tracks[tr].looping == 1) and (self.visible_tracks[tr].start != 0):
                                dif = self.visible_tracks[tr].start
                                
                            pos = int(((clip.loop_start - dif) / self.visible_tracks[tr].length) * self.height)
                            pos = (pos < 0) and 0 or pos
                            if sub % 3 == 1:
                                byte = 1 << pos
                        
                    cols.append(byte)
                
            else:
                cols.append(0)
            
        return cols

    def do_button_press(self, x, y, v):
        # Change loop lengths
        if x == self.width - 1 and y == self.height - 2:
            self.step = v
            
            if v == 1:
                self.update_selection()
                
            if v == 0:
                self.reset_lcd = 1
        
        elif v == 1:
            tr = x + self.track
        
            # Make all step lengths 1 step shorter
            if x == self.width - 1 and y == self.height - 3:
                if self.step == 1:
                    self.track_right()
                
                else:
                    self.log("down")
                    for i in range(len(self.visible_tracks)):
                        if self.visible_tracks[i].cid > -1:
                            if self.visible_tracks[i].step_size > 0:
                                self.visible_tracks[i].step_size -= 1
                        
                                self.log(str(i) + " " + str(self.visible_tracks[i].step_size) + " " + str(self.visible_tracks[i].current_step))
                                if self.visible_tracks[i].current_step > -1:
                                    self.set_loop(i)
    
                self.build_lcd()
        
            # Make all step lengths 1 step longer
            elif x == self.width - 1 and y == self.height - 4:
                if self.step == 1:
                    self.track_left()
                    
                else:
                    self.log("up")
                    for i in range(len(self.visible_tracks)):
                        if self.visible_tracks[i].cid > -1:
                            if self.visible_tracks[i].step_size < 9:
                                self.visible_tracks[i].step_size += 1
                        
                                self.log(str(i) + " " + str(self.visible_tracks[i].step_size) + " " + str(self.visible_tracks[i].current_step))
                                if self.visible_tracks[i].current_step > -1:
                                    self.set_loop(i)

                self.build_lcd()
        
            elif x == self.width - 1 and y == self.height - 5:            
                self.log("right")
                self.track_right()

            elif x == self.width - 1 and y == self.height - 6:
                self.log("left")
                self.track_left()
        
            elif self.step == 1:
                if y == self.height - 1:
                    # Stop/Start Clip
                    if self.visible_tracks[tr].cid > -1:
                        clip = self.song().visible_tracks[tr].clip_slots[self.visible_tracks[tr].cid].clip
                        if clip.is_playing == 1:
                            clip.stop()
                        else:
                            clip.fire()
                    
                else:
                    # Change step size
                    self.visible_tracks[tr].step_size = y
                    self.build_lcd()
                    
                    if self.visible_tracks[tr].cid > -1 and self.visible_tracks[tr].current_step > -1:
                        self.set_loop(tr)

            elif y == self.visible_tracks[tr].current_step:
                # Reset track
                self.do_reset(self.song().visible_tracks[tr].clip_slots[self.visible_tracks[tr].cid].clip, self.visible_tracks[tr].start, self.visible_tracks[tr].length)
                self.visible_tracks[tr].current_step = -1

            else: 
                #Change loop position
                self.visible_tracks[tr].current_step = y
                self.set_loop(tr);
                
                if self.visible_tracks[tr].looping == 0:
                    self.song().visible_tracks[tr].clip_slots[self.visible_tracks[tr].cid].fire()
            
        
    def do_bg(self):
        time = self.get_time()       
        now = int(time.beats) + (int(time.bars) * 4)
        
        if now != self._last:
            self._last = now
            
        # Reset any clips that have been stopped
        if len(self.reset) > 0:
            for clip in self.reset:
                self.log("reset: " + str(clip))
                self.do_reset(self.song().visible_tracks[clip[0]].clip_slots[clip[1]].clip, clip[2], clip[3])
                
            self.reset = []
            
    def do_receive_midi(self, midi_bytes):
        pass


    def set_loop(self, tr):
        track = self.visible_tracks[tr]
   
        clip = self.song().visible_tracks[tr].clip_slots[track.cid].clip
        size = track.length / self.height

        clip.loop_end   = track.start +(track.current_step * size) + (size / self.sindex[track.step_size])
        clip.loop_start = track.start + (track.current_step * size)
        clip.loop_end   = track.start +(track.current_step * size) + (size / self.sindex[track.step_size])
        
    def do_reset(self, clip, start, length):
        if clip != None:
            clip.loop_end   = start + length
            clip.loop_start = start
            clip.loop_end   = start + length
        
class Track:
    def __init__(self, cid=-1, stime=0, looping=0, start=0, length=0, name='', current_step=-1, step_size=2):
        self.cid = cid
        self.stime = stime
        self.looping = looping
        self.start = start
        self.length = length
        self.name = name
        self.current_step = current_step
        self.step_size = step_size
        
    def update(self, cid=-1, stime=0, looping=0, start=0, length=0, name='', current_step=-1, step_size=2):
        self.cid = cid
        self.stime = stime
        self.looping = looping
        self.start = start
        self.length = length
        self.name = name
        self.current_step = current_step
        self.step_size = step_size     
