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
import re

class ClipLauncher(Program):
    name = "Clip Launcher"
    pageid = [1]

    def __init__(self, parent, width, height):
        self.width = width
        self.height = height
        
        self.parent = parent
        self.c_instance = parent.c_instance
        self.oscServer = parent.oscServer

        self.tclisten = {}
        self.clisten  = {}
        self.slisten  = {}
        self.sglisten = {}
        self.splisten = {}
        self.sblisten = {}
        
        self._last = ''
        self._lt = 0

        self.pos_cache = [0 for i in range(self.width)]
        
        self.shift = 0
        self.view = 0
        self.ms = 0
        self.v = 0
        self.skip = 0
        
        self.do_refresh_state()

    def set_wh(self, w, h):
        self.width = w
        self.height = h
        
        self.pos_cache = [0 for i in range(self.width)]

    def default_labels(self):
        msgs = []
        msgs.append(['/1/2nlabel5', "Device"])
        msgs.append(['/1/2nlabel6', str(int(self.song().tempo))])
        
        msgs = self.ms_labels(msgs)    
                            
        self.oscServer.sendBundle(msgs)
        
    def shifted_labels(self):
        msgs = []
        msgs.append(['/1/2nlabel5', "Temp-"])
        msgs.append(['/1/2nlabel6', "Temp+"])
        
        msgs = self.ms_labels(msgs)
        
        self.oscServer.sendBundle(msgs)
        
    def ms_labels(self, msgs):
        if self.has_size():
            for x in range(self.width-1):
                if x < self.twidth:
                    tr = x + self.track
                        
                    if self.ms == 1:    
                        if self.song().visible_tracks[tr].mute:
                            msgs.append(['/1/slabel' + str(x + 1), 'Unmt'])
                        else:
                            msgs.append(['/1/slabel' + str(x + 1), 'Mute'])
                                            
                    else:
                        msgs.append(['/1/slabel' + str(x + 1), 'Stop'])

                    msgs.append(['/1/stop' + str(x + 1) + '/visible', 1])
                    msgs.append(['/1/stop' + str(x + 1) + '/color', 'blue'])
                    msgs.append(['/1/slabel' + str(x + 1) + '/color', 'blue'])
                    msgs.append(['/1/vol' + str(x + 1) + '/visible', 1])
                    msgs.append(['/1/fader' + str(x + 1) + '/visible', 1])
                    msgs.append(['/1/trpush' + str(x + 1) + '/visible', 1])
                    msgs.append(['/1/trlabel' + str(x + 1) + '/visible', 1])                    
                else:
                    msgs.append(['/1/slabel' + str(x + 1), ' '])
                    msgs.append(['/1/stop' + str(x + 1) + '/visible', 0])
                    msgs.append(['/1/vol' + str(x + 1) + '/visible', 0])
                    msgs.append(['/1/fader' + str(x + 1) + '/visible', 0])
                    msgs.append(['/1/trpush' + str(x + 1) + '/visible', 0])
                    msgs.append(['/1/trlabel' + str(x + 1) + '/visible', 0])                    
                            
        return msgs
        
    def track_changed(self):
        self.update_matrix()
        
    def scene_changed(self):
        self.update_matrix()
        
    #def page_selected(self):
    #    self.update_matrix()
        
    def rem_listeners(self):
        self.log("** Remove Listeners **")
    
        for slot in self.slisten:
            if slot != None:
                if slot.has_clip_has_listener(self.slisten[slot]) == 1:
                    slot.remove_has_clip_listener(self.slisten[slot])
    
        self.slisten = {}

        for slot in self.sglisten:
            if slot != None:
                if slot.controls_other_clips_has_listener(self.sglisten[slot]) == 1:
                    slot.remove_controls_other_clips_listener(self.sglisten[slot])

        self.sglisten = {}

        for slot in self.splisten:
            if slot != None:
                if slot.playing_status_has_listener(self.splisten[slot]) == 1:
                    slot.remove_playing_status_listener(self.splisten[slot])

        self.splisten = {}
        
        for slot in self.sblisten:
            if slot != None:
                if slot.has_stop_button_has_listener(self.sblisten[slot]):
                    slot.remove_has_stop_button_listener(self.sblisten[slot])
        
        self.sblisten = {}
        
        for clip in self.clisten:
            if clip != None:
                if clip.playing_status_has_listener(self.clisten[clip]) == 1:
                    clip.remove_playing_status_listener(self.clisten[clip])
                    
                if clip.name_has_listener(self.update_matrix) == 1:
                    clip.remove_name_listener(self.update_matrix)

                if clip.color_has_listener(self.update_matrix) == 1:
                    clip.remove_color_listener(self.update_matrix)
                                    
        self.clisten = {}
        
    def add_listeners(self):
        self.rem_listeners()
    
        tracks = self.getslots()
        for track in range(len(tracks)):
            for clip in range(len(tracks[track])):
                c = tracks[track][clip]
                if c.has_clip:
                    self.add_cliplistener(c.clip, track, clip)
                else:
                    self.add_slotlistener(c, track, clip)
        
    def add_cliplistener(self, clip, tid, cid):
        cb = lambda :self.clip_changestate(clip, tid, cid)
        
        if self.clisten.has_key(clip) != 1:
            clip.add_playing_status_listener(cb)
            clip.add_name_listener(self.update_matrix)
            clip.add_color_listener(self.update_matrix)
            self.clisten[clip] = cb
        
    def add_slotlistener(self, slot, tid, cid):
        cb = lambda :self.slot_changestate(slot, tid, cid)
        
        if self.slisten.has_key(slot) != 1:
            slot.add_has_clip_listener(cb)
            self.slisten[slot] = cb

        cb = lambda :self.slot_groupstate(slot, tid, cid)
        if self.sglisten.has_key(slot) != 1:
            slot.add_controls_other_clips_listener(cb)
            self.sglisten[slot] = cb

        cb = lambda :self.slot_playstate(slot, tid, cid)
        if self.splisten.has_key(slot) != 1:
            slot.add_playing_status_listener(cb)
            self.splisten[slot] = cb
            
        if not self.song().visible_tracks[tid].is_foldable:
            cb = lambda :self.slot_stopbutton(slot, tid, cid)
            if self.sblisten.has_key(slot) != 1:
                slot.add_has_stop_button_listener(cb)
                self.sblisten[slot] = cb
        
    def slot_stopbutton(self, slot, tid, cid):
        x = tid - self.track
        y = cid - self.scene          

        if x > -1 and x < self.twidth and y > -1 and y < self.sheight:
            if slot.has_stop_button:
                msgs = []
                msgs.append(['/1/push' + str((y * (self.width -1)) + x + 1) + '/visible', 1])
                msgs.append(['/1/push' + str((y * (self.width -1)) + x + 1) + '/color', 'grey'])
                msgs.append(['/1/label' + str((y * (self.width -1)) + x + 1) + '/color', 'gray'])
                self.oscServer.sendBundle(msgs)
                
            else:
                self.oscServer.sendOSC('/1/push' + str((y * (self.width -1)) + x + 1) + '/visible', 0)
        
    def slot_groupstate(self, slot, tid, cid):
        x = tid - self.track
        y = cid - self.scene

        self.log('ping new group: ' + str(tid) + ' ' +str(cid))

        if slot.controls_other_clips:
            if x > -1 and x < self.twidth and y > -1 and y < self.sheight:
                msgs = []
                msgs.append(['/1/label' + str((y * (self.width -1)) + x + 1), '-->'])
                msgs.append(['/1/label' + str((y * (self.width -1)) + x + 1) + '/color', 'gray'])
                self.oscServer.sendBundle(msgs)
        else:
            if x > -1 and x < self.twidth and y > -1 and y < self.sheight:
                self.oscServer.sendOSC('/1/label' + str((y * (self.width -1)) + x + 1), ' ')            
        
    def slot_changestate(self, slot, tid, cid):
        x = tid - self.track
        y = cid - self.scene
    
        # Added new clip
        if slot.has_clip:                            
            self.add_cliplistener(slot.clip, tid, cid)
            
            name = self.trunc_string(slot.clip.name, 8).strip()
            
            if x > -1 and x < self.twidth and y > -1 and y < self.sheight:
                id = str((y * (self.width -1)) + x + 1)
                
                msgs = []
                
                msgs.append(['/1/push' + str(id) + '/visible', 1])  
                msgs.append(['/1/label' + str(id), name])
                msgs.append(['/1/push' + str(id) + '/color', self.to_color(slot.clip.color)])  
                msgs.append(['/1/label' + str(id) + '/color', self.to_color(slot.clip.color)]) 
                
                self.oscServer.sendBundle(msgs)
                
                #self.oscServer.sendOSC('/1/label' + str((y * (self.width -1)) + x + 1), name)
        else:
            if x > -1 and x < self.twidth and y > -1 and y < self.sheight:
                self.oscServer.sendOSC('/1/label' + str((y * (self.width -1)) + x + 1), " ")
                #self.oscServer.sendOSC('/1/push' + str((y * (self.width -1)) + x + 1) + '/visible', 0)
                self.oscServer.sendOSC('/1/push' + str((y * (self.width -1)) + x + 1) + '/color', 'gray')

            if self.clisten.has_key(slot.clip) == 1:
                slot.clip.remove_playing_status_listener(self.clisten[slot.clip])
                
                if slot.clip.name_has_listener(self.update_matrix):
                    slot.clip.remove_name_listener(self.update_matrix)
                    
                if clip.color_has_listener(self.update_matrix):
                    clip.remove_color_listener(self.update_matrix)  
            
    def slot_playstate(self, slot, tid, cid):
        x = tid - self.track
        y = cid - self.scene
        
        self.log('tid:' + str(tid))
        
        if tid > -1 and tid < self.twidth:
            if self.ms == 0:
                name = 'Stop'
            else:
                if self.song().visible_tracks[tid].mute:
                    name = 'Unmt'
                else:
                    name = 'Mute'
                    
            self.oscServer.sendOSC('/1/slabel' + str(x+1), name)
            self.oscServer.sendOSC('/1/stop' + str(x+1) + '/color', 'blue')  
            self.oscServer.sendOSC('/1/fader' + str(x+1), 0)
            
            if not slot.is_playing:
                if x > -1 and x < self.twidth and y > -1 and y < self.sheight:
                    #self.oscServer.sendOSC('/1/label' + str((y * (self.width -1)) + x + 1), 'group')
                    self.oscServer.sendOSC('/1/push' + str((y * (self.width -1)) + x + 1) + '/color', 'gray')

    def clip_changestate(self, clip, x, y):
        self.log("Listener: x: " + str(x) + " y: " + str(y));
        
        tid = x - self.track
        self.log('tid:' + str(tid))
        if tid > -1 and tid < self.twidth:
            if self.ms == 0:
                name = 'Stop'
            else:
                if self.song().visible_tracks[tid].mute:
                    name = 'Unmt'
                else:
                    name = 'Mute'
                
            msgs = []
                            
            msgs.append(['/1/slabel' + str(tid+1), name])
            msgs.append(['/1/stop' + str(tid+1) + '/color', 'blue']) 
            msgs.append(['/1/fader' + str(tid+1), 0])
            
            if not clip.is_playing:
                sid = y - self.scene
            
                if sid > -1 and sid < self.sheight:
                    name = self.trunc_string(clip.name, 8).strip()
                    if not name:
                        name = 'clip'
                        
                    id = str((sid * (self.width -1)) + tid + 1)
                
                
                    #msgs.append(['/1/label' + str(id), name])
                    #self.oscServer.sendOSC('/1/push' + str((sid * (self.width -1)) + tid + 1) + '/color', 'red')  
                    
                    msgs.append(['/1/push' + str(id) + '/color', self.to_color(clip.color)])  
                    msgs.append(['/1/label' + str(id) + '/color', self.to_color(clip.color)])   
        
            self.oscServer.sendBundle(msgs)
        
    def do_refresh_state(self):
        self.limits()

        tracks = self.getslots()
        for track in range(len(tracks)):
            
            for clip in range(len(tracks[track])):            
                c = tracks[track][clip]
        
        self.update_matrix()
        self.add_listeners()
        self.default_labels()
        
    def do_bg(self):
        pass
        
    def do_update(self):
        song = self.song()
        t = song.get_current_beats_song_time()
        beats = t.beats
        sub = t.sub_division
        
        if self.skip == 1:
            self.skip = 0
        
        tracks = self.song().visible_tracks
        msgs = []
        for x in range(self.width-1):
            xs = x + self.track
            
            if x < self.twidth:
                tr = tracks[xs]
                
                if tr.playing_slot_index > -1:
                    if self.ms == 0:
                        name = 'Stop'
                    else:
                        if self.song().visible_tracks[xs].mute:
                            name = 'Unmt'
                        else:
                            name = 'Mute'
                
                    if beats % 2 == 0:
                        msgs.append(['/1/stop' + str(x + 1) + '/color', 'green'])
                        #msgs.append(['/1/slabel' + str(x + 1), '<' + name + '>'])
                    elif beats % 2 == 1:
                        msgs.append(['/1/stop' + str(x + 1) + '/color', 'blue'])
                        #msgs.append(['/1/slabel' + str(x + 1), name])
                                            
                    if tr.clip_slots[tr.playing_slot_index].has_clip:
                        slot = tr.clip_slots[tr.playing_slot_index]
                        if not slot.controls_other_clips:
                            clip = slot.clip
                            pos = round((clip.playing_position - clip.loop_start) / (clip.loop_end - clip.loop_start), 2)
                        else:
                            pos = 0
                    else:
                        pos = 0
                else:
                    pos = 0
                    
                if pos != self.pos_cache[x]:
                    self.pos_cache[x] = pos
                    msgs.append(['/1/fader' + str(x+1), pos])
                
                for y in range(self.height - 2):
                    ys = y + self.scene
                    id = (y * (self.width - 1)) + x + 1
                
                    if y < self.sheight:
                        slot = tracks[xs].clip_slots[ys]
                        
                        if slot.controls_other_clips:
                            if slot.is_playing:
                                if beats % 2 == 0:
                                    msgs.append(['/1/push' + str(id) + '/color', 'green'])
                                    
                                elif beats % 2 == 1:
                                    msgs.append(['/1/push' + str(id) + '/color', 'gray'])

                            if slot.is_triggered:
                                if sub % 3 == 1:
                                    msgs.append(['/1/push' + str(id) + '/color', 'green'])
                                    
                                elif sub % 3 == 0:
                                    msgs.append(['/1/push' + str(id) + '/color', 'gray'])
                        
                        elif slot.has_clip:
                            if slot.clip.is_triggered or slot.clip.is_playing:
                                name = self.trunc_string(slot.clip.name, 5).strip()
                            else:
                                name = self.trunc_string(slot.clip.name, 8).strip()
                            
                            if not name:
                                name = 'clip'
                        
                            if song.is_playing:
                                if slot.clip.is_triggered:
                                    if sub % 3 == 1:
                                        #msgs.append(['/1/label' + str(id), '<' + name + '>'])
                                        msgs.append(['/1/push' + str(id) + '/color', self.to_color(slot.clip.color)])
                                        
                                    elif sub % 3 == 0:
                                        #msgs.append(['/1/label' + str(id), name])
                                        msgs.append(['/1/push' + str(id) + '/color', 'gray'])
                                        
                                if slot.clip.is_playing:
                                    if beats % 2 == 0:
                                        msgs.append(['/1/push' + str(id) + '/color', self.to_color(slot.clip.color)])
                                        #msgs.append(['/1/label' + str(id), '<' + name + '>'])

                                    elif beats % 2 == 1:
                                        msgs.append(['/1/push' + str(id) + '/color', 'gray'])
                                        #msgs.append(['/1/label' + str(id), name])

        #time = str(t.bars) + '.' + str(t.beats) # + '.' + str(t.sub_division)
        smpt = self.song().get_current_smpte_song_time(0)
        time = (smpt.hours > 0 and ((smpt.hours < 10 and '0'+ str(smpt.hours) or str(smpt.hours)) + ':') or '') + (smpt.minutes < 10 and '0'+ str(smpt.minutes) or str(smpt.minutes)) + ':' + (smpt.seconds < 10 and '0'+ str(smpt.seconds) or str(smpt.seconds))
        
        if time != self._last:
            msgs.append(['/1/2nlabel7', time])
            self._last = time
            
        if self.shift == 0:
            tempo = int(self.song().tempo)
            if self._lt != tempo:
                msgs.append(['/1/2nlabel6', str(tempo)])
                self._lt = tempo
            
        if len(msgs) > 0:
            self.oscServer.sendBundle(msgs)
                                                  
    def update_matrix(self, labels = 0):
        if self.has_size():
            tracks = self.song().visible_tracks
            msgs = []
            for x in range(self.width - 1):
                xs = x + self.track
                
                #msgs = []
                
                if labels == 1:
                    if self.ms == 0:
                        name = 'Stop'
                    else:
                        if self.song().visible_tracks[xs].mute:
                            name = 'Unmt'
                        else:
                            name = 'Mute'
                
                    msgs.append(['/1/slabel' + str(x+1), name])
                
                for y in range(self.height - 2):
                    ys = y + self.scene
                    id = (y * (self.width - 1)) + x + 1
                
                    if x == 0:
                        if y < self.sheight:
                            msgs.append(['/1/nlabel' + str(y+1), self.trunc_string(self.song().scenes[ys].name, 6).strip()])
                            
                        else:
                            msgs.append(['/1/nlabel' + str(y+1), " "])
                
                    if (x < self.twidth):
                        if (y < self.sheight):
                            slot = tracks[xs].clip_slots[ys]
                            #self.log(str(xs) + " " + str(ys) + " " + str(slot) + " " + str(id))
                            
                            if tracks[xs].is_foldable:
                                if slot.controls_other_clips:
                                    msgs.append(['/1/label' + str(id), '-->'])
                                else:
                                    msgs.append(['/1/label' + str(id), ' '])
                                    
                                msgs.append(['/1/push' + str(id) + '/visible', 1]) 
                                msgs.append(['/1/push' + str(id) + '/color', 'gray']) 
                                msgs.append(['/1/label' + str(id) + '/color', 'gray']) 
                                                     
                            else:
                                if slot.has_stop_button:
                                    if slot.has_clip:
                                        name = self.trunc_string(slot.clip.name, 8).strip()
                                        
                                        msgs.append(['/1/push' + str(id) + '/visible', 1]) 
                                        msgs.append(['/1/label' + str(id), name])
                                        msgs.append(['/1/push' + str(id) + '/color', self.to_color(slot.clip.color)])  
                                        msgs.append(['/1/label' + str(id) + '/color', self.to_color(slot.clip.color)])                              
                                        
                                    else:
                                        msgs.append(['/1/label' + str(id), " "])
                                        msgs.append(['/1/push' + str(id) + '/visible', 1])                            
                                        msgs.append(['/1/push' + str(id) + '/color', 'gray']) 
                                        
                                else:
                                    msgs.append(['/1/label' + str(id), " "])
                                    msgs.append(['/1/push' + str(id) + '/visible', 0])
                                    
                        else:
                            msgs.append(['/1/label' + str(id), " "])
                            msgs.append(['/1/push' + str(id) + '/visible', 0])                            
                    else:
                        msgs.append(['/1/label' + str(id), " "])
                        msgs.append(['/1/push' + str(id) + '/visible', 0])                            


            self.oscServer.sendBundle(msgs)
                    
    def do_button_press(self, page, type, id, val, xy = []):   
        if type == 'nav':        
            if val == 1:
                # Fire scene
                sid = id - 1 + self.scene
                if sid < len(self.song().scenes):
                    self.song().scenes[sid].fire()
                    
        elif type == 'trpush':
            if val == 1:
                tid = self.track + id - 1
                trk = self.song().visible_tracks[tid]
                
                if trk.is_foldable:
                    trk.fold_state = (not trk.fold_state)
                
                else:
                    if trk.playing_slot_index > -1:
                        self.song().view.selected_track = trk
                        self.song().view.selected_scene = self.song().scenes[trk.playing_slot_index]
                        self.do_scene_change(trk.playing_slot_index)

                
        elif type == 'stop':
            if val == 1:
                # Stop all
                if (id == self.width):
                    self.song().stop_all_clips()
                
                # Stop track
                else:            
                    x = id - 1 + self.track
                    
                    if self.ms == 0:
                        self.song().visible_tracks[x].stop_all_clips()
                        #if self.trid.has_key(x):
                        #    self.song().visible_tracks[x].clip_slots[self.trid[x]].clip.stop()

                    else:
                        track = self.song().visible_tracks[x]
                        
                        if track.mute:
                            track.mute = 0
                            name = 'Mute'
                        else:
                            track.mute = 1
                            name = 'Unmt'
  
                        self.oscServer.sendOSC('/1/slabel'+str(id), name)
  
            
        elif type == '2nav':        
            # Shift
            if id == 8:
                self.shift = val
                self.ms = val
                
                if val == 1:
                    self.shifted_labels()
                    
                else:
                    self.default_labels()  
                        
            elif val == 1:          
                if id == 7:
                    if self.song().is_playing:
                        self.song().stop_playing()
                    else:
                        self.song().start_playing()
                        
                # Tap Tempo
                elif id == 6:
                    if self.shift == 1:
                        self.song().tempo = self.song().tempo + 1
                    else:
                        self.song().tap_tempo()
                        
                    self.oscServer.sendOSC('/1/2nlabel' + str(id), str(int(self.song().tempo)))
                    
                elif id == 5:
                    if self.shift == 1:
                        self.song().tempo = self.song().tempo - 1
                        self.oscServer.sendOSC('/1/2nlabel' + str(id+1), str(int(self.song().tempo)))
                    else:
                        if self.view == 1:
                            Live.Application.get_application().view.show_view("Detail/Clip")
                            self.oscServer.sendOSC('/1/2nlabel' + str(id), "Clip")
                            self.view = 0
                            
                        else:
                            Live.Application.get_application().view.show_view("Detail/DeviceChain")
                            self.oscServer.sendOSC('/1/2nlabel' + str(id), "Device")
                            self.view = 1

                elif id == 4:
                    self.track_right()
                    #self.update_matrix(1)
        
                elif id == 3:
                    self.track_left()
                    #self.update_matrix(1)
                    
                elif id == 2:
                    size = self.shift == 1 and 1 or (self.height - 2)
                    sid = self.sc
                    
                    if len(self.song().scenes) > sid + size:
                        self.do_scene_change(sid + size)
                        #self.update_matrix()
                        
                elif id == 1:
                    size = self.shift == 1 and 1 or (self.height - 2)
                    sid = self.sc
                    
                    if sid - size + 1 > 0:
                        step = sid - size
                    else:
                        step = 0
                    
                    self.do_scene_change(step)
                    #self.update_matrix()

        
        elif type == 'vscroll':
            self.skip = 1
            step = int(val * (len(self.song().scenes) - self.sheight + 1))
            
            self.do_scene_change(step)
            #self.update_matrix()
        
        elif type == 'hscroll':
            self.skip = 1
            step = int(val * (len(self.song().visible_tracks) - self.twidth + 1))
            
            self.do_track_change(step)
            #self.update_matrix()
        
        elif type == 'push':
            if val == 1:
        
                x = ((id-1) % (self.width-1)) + self.track
                y = int((id-1) / (self.width-1)) + self.scene           
            
                self.log(str(id) + " " + str(x) + " " + str(y))
            
                # View Track / Clip
                if self.shift == 1:
                    track = self.song().visible_tracks[x]
                
                    self.song().view.selected_track = track
                    self.song().view.selected_scene = self.song().scenes[y]
                    self.song().view.detail_clip = track.clip_slots[y].clip
                    Live.Application.get_application().view.show_view("Detail/Clip")
                
                # Launch Clips
                else:
                    if self.song().visible_tracks[x].clip_slots[y].has_clip:
                        self.song().visible_tracks[x].clip_slots[y].clip.fire()
                    else:
                        self.song().visible_tracks[x].clip_slots[y].fire()
                        
                    self.song().view.selected_track = self.song().visible_tracks[x]
                    self.song().view.selected_scene = self.song().scenes[y]

            elif val == 0:
                x = ((id-1) % (self.width-1)) + self.track
                y = int((id-1) / (self.width-1)) + self.scene 
                
                if self.shift == 0:
                    if self.song().visible_tracks[x].clip_slots[y].has_clip:
                        self.song().visible_tracks[x].clip_slots[y].clip.set_fire_button_state(0)
                    else:
                        self.song().visible_tracks[x].clip_slots[y].set_fire_button_state(0) 
                        
                    self.log('stopped clip')