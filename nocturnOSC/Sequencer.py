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
from math import log
import Live
import time

class Sequencer(Program):
    name = "Step Sequencer"
    pageid = [4]
    
    def __init__(self, parent, width, height):
        self.width = 16
        self.height = 7
        
        self.parent = parent
        self.c_instance = parent.c_instance
        self.oscServer = parent.oscServer
        
        if self.parent.ipad:
            self.height = 8
        
        self.quan = 0.25
        self.len = 1
        self.bank = 0
        self.vel = 100.0
        self.offset = 60
        self.fold = 0

        self.scales = { 'Maj': [0,2,4,5,7,9,11,12], 
                        'Nat Min': [0,2,3,5,7,8,10,12],
                        'Harm Min': [0,2,3,5,7,8,11,12],
                        'Pent': [0,2,4,7,9,11,13,15],
                        'Chromatic': [] }
                       
        self.scale = sorted(self.scales.keys())[0]
        self.root = 0

        self.menu = 0
        self.update = 0
        
        self.sel_scene = 0
        self.sel_track = 0
        self.sel_clip  = None
        self.sel_slot  = None
        self.note_cache = {}
        self.real_notes = []
        self.last_note = 60
        self.mutes = [False for i in range(127)]
        
        self.follow = 1
        self.skip = 0
        self.ms = 0
        
        self.last = 0
        self.ltime = ""
        
        self.oscServer.sendOSC('/4/fader4', 1-((log(self.quan,2) + 4.0) / 8.0))
        #self.do_refresh_state()
        
    def set_wh(self, w, h):
        self.width = 16
        self.height = 7

        if self.parent.ipad:
            self.height = 8
        
    def sel_track_change(self):
        if self.follow:
            tr = self.song().view.selected_track
            
            self.log('tr change'+ str(tr))
            
            self.sel_track = self.track_idx(tr)
            self.clip_change()
        
    def sel_scene_change(self):
        if self.follow:
            sc = self.song().view.selected_scene
            
            self.log('sc change'+ str(sc))
                    
            self.sel_scene = self.tuple_idx(self.song().scenes, sc)
            self.clip_change()
        
    def first_midi(self):
        tracks = self.song().visible_tracks

        # First track is a midi track
        if tracks[self.sel_track].has_midi_input:
            self.clip_change()
            return

        # Find next midi track
        for i in range(len(tracks)):
            if tracks[i].has_midi_input:
                self.sel_track = i
                self.clip_change()
                return
    
    def destroy(self):
        if self.sel_clip != None:
            if self.sel_clip.notes_has_listener(self.note_change) == 1:
                self.sel_clip.remove_notes_listener(self.note_change)
        
    def clip_change(self):
        if len(self.song().visible_tracks) > self.sel_track:
            cl = self.song().visible_tracks[self.sel_track].clip_slots[self.sel_scene].clip
    
            if self.sel_slot:
                self.sel_slot.remove_has_clip_listener(self.clip_change)
                self.sel_slot = None
    
            if cl != None and cl.is_midi_clip == 1 and cl != self.sel_clip:
                if self.sel_clip != None:
                    if self.sel_clip.notes_has_listener(self.note_change) == 1:
                        self.sel_clip.remove_notes_listener(self.note_change)
            
                self.sel_clip = cl
                self.update_notes()
                
                if not self.sel_clip.notes_has_listener(self.note_change):
                    self.sel_clip.add_notes_listener(self.note_change)
            
                self.log("clip: " + str(self.sel_clip) + " t:" + str(self.sel_track) + " :" + str(self.sel_scene))
            
            else:
                self.note_cache = {}
                self.sel_clip = None
                
                tr = self.song().tracks[self.sel_track]
                if tr.has_midi_input:
                    slot = tr.clip_slots[self.sel_scene]
                    slot.add_has_clip_listener(self.clip_change)
                    
                    self.sel_slot = slot
            
            if self.is_current():
                self.page_selected()
            
            
    def page_selected(self):
        self.update_matrix()
        self.update_vel_matrix()
        self.get_title()
        self.get_note_line()
        self.update_selection()
        self.get_timeline()

    def update_notes(self):
        if self.sel_clip != None:
            self.sel_clip.select_all_notes()
            all_notes = list(self.sel_clip.get_selected_notes())
            self.sel_clip.deselect_all_notes()
                    
            diff = [i for i in all_notes+self.real_notes if i not in all_notes or i not in self.real_notes]
            
            if len(diff) > 0 and len(self.note_cache) > 0:
                self.last_note = diff[-1][0]
                self.get_note_line()
                    
            notes = {}
            for note in all_notes:
                if notes.has_key(note[1]):
                    notes[note[1]].append([note[0],note[3],note[2],note[4]])
                else:
                    notes[note[1]] = [[note[0],note[3],note[2],note[4]]]
            
            self.note_cache = notes
            self.real_notes = all_notes
            
            self.log("ALL: " + str(all_notes))
        
    def update_vel_matrix(self):
        self.log('update vels')
        
        msgs = []
        for i in range(16):
            pos = self.pos(i)
            
            found = 0
            if self.note_cache.has_key(pos):
                for nt in self.note_cache[pos]:
                    if nt[0] == self.last_note:
                        msgs.append(['/4/multifader1/' + str(i+1), nt[1]/127.0])
                        found = 1 
        
            if found == 0:
                msgs.append(['/4/multifader1/' + str(i+1), 0])
          
        self.oscServer.sendBundle(msgs)

    def update_matrix(self):
        for k in range(2):
            msgs = []
            for j in range(k*8,(k*8)+8):
                for i in range(0,8):
                    msgs.append(['/4/multitoggle1/' + str(i+1) + '/' + str(j+1), 0])

            self.oscServer.sendBundle(msgs)
        
        self.log('updating matrix')
        
        msgs = []
        notes = self.note_keys()
        for i in range(16):
            pos = self.pos(i)
            
            for j in range(self.height):
                if j < len(notes):
                    if self.note_cache.has_key(pos):
                        for nt in self.note_cache[pos]:
                            if nt[0] == notes[j]:
                                msgs.append(['/4/multitoggle1/' + str(j+1) + '/' + str(i+1), 1])
               
        self.log(str(msgs))
        self.oscServer.sendBundle(msgs)
                            
    def do_refresh_state(self):
        self.first_midi()
        
        msgs = []
        for i in range(16):
            msgs.append(['/4/led' + str(i+1), 0])

        msgs.append(['/4/toggle0', self.follow])
        msgs.append(['/4/2nlabel1', self.scale])
        msgs.append(['/4/mute', self.ms == 0 and 'Mute' or 'Solo'])
        
        self.oscServer.sendBundle(msgs)
    
        self.get_timeline()
        self.get_note_line()
        
    def do_update(self):
        if self.sel_clip != None:
            msgs = []
            cp = self.sel_clip.playing_position
            if self.sel_clip.is_playing:
                for i in range(16):
                    pos = self.pos(i)

                    if cp > pos and cp < pos + self.quan:
                        if pos != self.last:
                            msgs.append(['/4/led' + str(i+1), 1])
                            self.last = pos
                    else:
                        msgs.append(['/4/led' + str(i+1), 0])
                     
                self.oscServer.sendBundle(msgs)
    
    def do_bg(self):
        if self.update > 0:
            self.update -= 1

        if self.update == 1:
            self.log("triggered")
            self.update_notes()
            self.update_matrix()
            self.update_vel_matrix()

    def default_labels(self):
        self.oscServer.sendOSC('/4/nlabel5', 'Zoom-')
        self.oscServer.sendOSC('/4/nlabel6', 'Zoom+')

    def menu2_labels(self):
        self.oscServer.sendOSC('/4/nlabel5', (self.fold == 1 and 'Unfold' or 'Fold'))
        
        if self.sel_clip != None:
            if self.sel_clip.is_playing:
                self.oscServer.sendOSC('/4/nlabel6', 'Stop')
            else:
                self.oscServer.sendOSC('/4/nlabel6', 'Start')
        else:
            self.oscServer.sendOSC('/4/nlabel6', 'Start')

    def _fold(self):
        if self.fold == 1:
            self.fold = 0
            self.update_matrix()
            self.get_note_line()
            self.oscServer.sendOSC('/4/nlabel5', 'Fold')
            self.oscServer.sendOSC('/4/fold', 'Fold') 
        else:
            self.fold = 1  
            self.update_matrix()
            self.get_note_line()
            self.oscServer.sendOSC('/4/nlabel5', 'Unfold')
            self.oscServer.sendOSC('/4/fold', 'Unfold')
                    
        self.offset = 60

    def do_button_press(self, page, type, id, val, xy = []):
        self.log(str(type))
        if type == 'multifader':
            if self.sel_clip == None:
                self.oscServer.sendOSC('/4/multifader1/' + str(xy[0]), 0) 
                return
            
            self.skip = 1            
            pos = self.pos(xy[0]-1)
            found = 0
            for nt in self.real_notes:
                if nt[0] == self.last_note and nt[1] == pos:
                    found = 1
                    
            if found == 0:
                self.oscServer.sendOSC('/4/multifader1/' + str(xy[0]), 0) 
                return
        
            self.update_vel(self.last_note, pos, val*127.0)       
        
        elif type == 'fader':
            if id == 1:
                val = int((val - 0.5) * 10)
                self.log(str(val))
                self.len = pow(2,val)
                
                self.get_title()
            
            # note up/down
            elif id == 2:
                new = (self.scale == 'Chromatic' and max(0,int(val * 127) - 4) or (int(int(val * 127) / 12)* 12))
                
                if new != self.offset:
                    self.offset = new
                
                    self.get_note_line()
                    self.update_matrix()
                    self.update_vel_matrix()
            
            # left / right
            elif id == 3:
                new = round(((self.sel_clip.length/(self.quan * self.width)) - 1) * val, 4)
                new = new - (new % 0.0625)
            
                if new != self.bank:
                    self.bank = new
                    
                    self.get_timeline()
                    self.update_matrix()
                    self.update_vel_matrix() 
            
            # zoom up/down
            elif id == 4:
            
                new = pow(2, int((1-val) * 8) - 4)
                
                if new != self.quan:
                    self.quan = new
                    
                    self.get_timeline()
                    self.get_title()
                    self.update_matrix()
                    self.update_vel_matrix()
            
        
        elif type == 'push':
            if id == 1:
                if val == 1:
                    if self.ms == 1:
                        self.ms = 0
                    else:
                        self.ms = 1
                        
                self.oscServer.sendOSC('/4/mute', self.ms == 0 and 'Mute' or 'Solo')
                
            elif id == 2:
                if val == 1:
                    self._fold()
        
        elif type == 'toggle':
            if id == 0:
                self.follow = val
                self.log('follow: ' + str(val))
                
            else:        
                self.skip = 1
                if self.fold == 1:
                    folded_notes = self.note_keys()
                    id = id + self.offset - 60 - 1
                    if len(folded_notes) > id:
                        note = folded_notes[id]
                    else:
                        note = -1
                else:
                    note = self.get_note(id - 1)
            
                if note > -1:
                    self.mute(note, bool(val))
                
        elif type == '2nav':
            if val == 1:
                if not self.fold:
                    if id == 1:
                        scales = sorted(self.scales.keys())
                        
                        self.log(str(scales))
                        cs = scales.index(self.scale)
                    
                        if cs < len(scales) - 1:
                            self.scale = scales[cs+1]
                        else:
                            self.scale = scales[0]
                            
                        self.oscServer.sendOSC('/4/2nlabel1', self.scale)
                        self.offset = 60
            
                    else:
                        self.root = id - 2
                    
                    self.get_note_line()
                    self.update_matrix()
        
        elif type == 'nav':
            if id == 7:
                if val == 1:
                    self.menu = 1
                    self.menu2_labels()
                else:
                    self.menu = 0
                    self.default_labels()
                
            if val == 1:
                if self.menu == 0:
                    # Quantiation Up
                    if id == 6:
                        if self.quan > 0.0625:
                            self.quan /= 2
                            self.log(str(self.quan))
                    
                            self.get_timeline()
                            self.get_title()
                            self.update_matrix()
                            self.update_vel_matrix()
                            
                            self.oscServer.sendOSC('/4/fader4', 1-((log(self.quan,2) + 4.0) / 8.0))
                    
                    # Quantisation Down
                    if id == 5:
                        if self.quan < 8:
                            self.quan *= 2
                            self.log(str(self.bank))
                                
                            if self.sel_clip != None:
                                if self.sel_clip.length <= (self.quan*self.bank*self.width):
                                    self.bank = int(self.sel_clip.length/(self.quan * self.width) - 1)
                                    
                            self.get_timeline()
                            self.get_title()
                            self.update_matrix()
                            self.update_vel_matrix()                            
                            
                            self.oscServer.sendOSC('/4/fader4', 1-((log(self.quan,2) + 4.0) / 8.0))
                                                        
                    # Note Offset Up
                    if id == 3:
                        if self.offset < 127 - self.height:
                            self.offset += (self.scale == 'Chromatic' and self.height or 12)
                            
                            self.get_note_line()
                            self.update_matrix()
                            self.update_vel_matrix()

                            self.oscServer.sendOSC('/4/fader2', (self.offset+1)/127.0)
                        
                    # Note Offset Down
                    if id == 4:
                        num = self.scale == 'Chromatic' and self.height or 12
                    
                        if self.offset > num:
                            self.offset -= num
                            self.get_note_line()
                            
                            self.update_matrix()
                            self.update_vel_matrix()                            
                            
                            self.oscServer.sendOSC('/4/fader2', (self.offset+1)/127.0)
                        
                    # Bank Up
                    if id == 2:
                        if self.sel_clip != None:
                            if self.bank < self.sel_clip.length/(self.quan * self.width) - 1:
                                self.bank = int(self.bank) + 1
                                
                                self.get_timeline()
                                self.update_matrix()
                                self.update_vel_matrix()
                                                                                                                   
                                self.oscServer.sendOSC('/4/fader3', self.bank/((self.sel_clip.length/(self.quan * self.width)) - 1))
                                
                    # Bank Down
                    if id == 1:
                        if self.bank > 0:
                            self.bank = int(self.bank) - 1
                            
                            self.get_timeline()
                            self.update_matrix()
                            self.update_vel_matrix()
                            
                            self.oscServer.sendOSC('/4/fader3', self.bank/((self.sel_clip.length/(self.quan * self.width)) - 1))                    
                            
                        self.log(str(self.bank))
                        
                elif self.menu == 1:
                    # Track Right
                    if id == 2:
                        tracks = self.song().visible_tracks
                        if self.sel_track < len(tracks):
                            for i in range(self.sel_track+1,len(tracks)):
                                if self.check_track(tracks[i],i):
                                    return
                    
                    # Track Left
                    if id == 1:
                        tracks = self.song().visible_tracks
                        if self.sel_track > 0:
                            for i in range(self.sel_track-1,-1,-1):
                                if self.check_track(tracks[i],i):
                                    return
                                                                            
                    # Scene Up
                    if id == 4:
                        if self.sel_scene < len(self.song().scenes):
                            self.sel_scene += 1
                            self.update_selection()
                            self.clip_change()
                            
                    # Scene Down
                    if id == 3:
                        if self.sel_scene > 0:
                            self.sel_scene -= 1
                            self.update_selection()
                            self.clip_change()
                            
                    # Fold Notes
                    if id == 5:
                        self._fold()
        
                    # Start/Stop Clips
                    if id == 6:
                        if self.sel_clip != None:
                            if self.sel_clip.is_playing == 1:
                                self.sel_clip.stop()
                                self.oscServer.sendOSC('/4/nlabel5', 'Start')
                            else:
                                self.sel_clip.fire()
                                self.oscServer.sendOSC('/4/nlabel5', 'Stop')
                                                    
        if type == 'multitoggle':
            x = xy[0] - 1
            y = xy[1] - 1
            self.skip = 1
            
            if self.sel_clip == None:
                self.oscServer.sendOSC('/4/multitoggle1/' + str(xy[1]) + '/' + str(xy[0]), 0)
                return

            pos = self.pos(x)
            
            self.log(str(pos))
            
            if self.fold == 1:
                folded_notes = self.note_keys()
                id = y + self.offset - 60
                self.log(str(id) + " " + str(folded_notes))
                if len(folded_notes) > id:
                    note = folded_notes[id]
                else:
                    note = -1
                    self.log('bad note')
                    self.oscServer.sendOSC('/4/multitoggle1/' + str(xy[1]) + '/' + str(xy[0]), 0)
            else:
                note = self.get_note(y)
        
            if note > -1:
                if self.note_cache.has_key(pos):
                    found = 0
                    for nt in self.note_cache[pos]:
                        if nt[0] == note:
                            found = 1
                
                    if found == 0:
                        self.add_note(pos,note)
                    else:
                        self.rem_note(pos,note)
                    
                else:
                    self.add_note(pos,note)
                    
                self.update_vel_matrix()
                    
            self.get_note_line()
            
        self.log(str(xy))

    def check_track(self, track, id):
        if track.has_midi_input:
            self.sel_track = id
            self.update_selection()
            self.clip_change()
            return 1

        else:
            return 0
              
    def pos(self, pos):
        return (self.bank * self.width * self.quan) + (pos * self.quan)
            
    def add_note(self, pos, note):
        notes = list(self.real_notes)
        notes.append([note, pos, self.quan * self.len, self.vel, False])

        self.sel_clip.deselect_all_notes()
        self.sel_clip.replace_selected_notes(tuple(notes))
                
        self.last_note = note
        self.update_notes()

    def rem_note(self, pos, note):
        new_notes = []
        
        for nt in self.real_notes:
            if nt[0] == note and nt[1] == pos:
                pass
            else:
                new_notes.append(nt)
                
        self.sel_clip.select_all_notes()
        self.sel_clip.replace_selected_notes(tuple(new_notes))
        self.sel_clip.deselect_all_notes()
        
        self.last_note = note
        self.update_notes()
    
    def update_vel(self, note, pos, vel):
        note_out = []
        for nt in self.real_notes:
            if nt[0] == note and nt[1] == pos:
                note_out.append([nt[0], nt[1], nt[2], vel, nt[4]])
            else:
                note_out.append(nt)

        if self.note_cache.has_key(pos):
            for j in range(len(self.note_cache[pos])):
                if self.note_cache[pos][j][0] == note:
                    self.note_cache[pos][j][1] = vel

        self.real_notes = note_out
        self.sel_clip.select_all_notes()
        self.sel_clip.replace_selected_notes(tuple(note_out))
        self.sel_clip.deselect_all_notes()
   
        
    def mute(self, note, mute):
        self.log('muting notes' + str(note) + " " + str(mute))
        note_out = []
        for nt in self.real_notes:
            if self.ms == 0:
                if nt[0] == note:
                    note_out.append([nt[0], nt[1], nt[2], nt[3], mute])
                    self.mutes[note] = mute
                else:
                    note_out.append(nt)
            else:
                if nt[0] != note:
                    note_out.append([nt[0], nt[1], nt[2], nt[3], mute])
                    self.mutes[note] = mute
                else:
                    note_out.append(nt)
                self.get_note_line()

        self.real_notes = note_out
        self.sel_clip.select_all_notes()
        self.sel_clip.replace_selected_notes(tuple(note_out))
        self.sel_clip.deselect_all_notes()

    def note_keys(self):
        if self.fold == 1:    
            list = {}
            for note in self.real_notes:
                list[note[0]] = 1

            return sorted(list.keys())
        
        else:
            list =  []
            
            for i in range(self.height):
                list.append(self.get_note(i))
                
            return list
        
    def note_change(self):
        self.log("notes changed")
        
        if self.skip == 0:
            self.update = 10
        else:
            self.skip = 0
            
    def get_timeline(self):
        msgs = []
        for i in range(8):
            if self.sel_clip != None:
                if self.pos(i*2) < self.sel_clip.length:
                    name = self.beat_time(self.pos(i*2))
                    if name != self.ltime:
                        msgs.append(['/4/time' + str(i+1),  name.ljust(10)])
                        self.ltime = name
                    else:
                        msgs.append(['/4/time' + str(i+1),  " ".ljust(20)])
                else:
                    msgs.append(['/4/time' + str(i+1),  " ".ljust(20)])
            else:
                msgs.append(['/4/time' + str(i+1),  " ".ljust(20)])
                
        self.oscServer.sendBundle(msgs)
    
    def get_title(self):
        if self.sel_clip != None:
            clip = self.to_ascii(self.sel_clip.name)
            
            if not clip.strip():
                clip = 'MIDI Clip'
            
        tracks = self.song().visible_tracks
        if self.sel_track < len(tracks):
            track = self.to_ascii(tracks[self.sel_track].name)

        quan = self.quan > 4 and str(int(self.quan/4)) or ("1/" + str(int(4/self.quan)))

        clen = self.quan * self.len            
        clen = clen > 4 and str(int(clen/4)) or ("1/" + str(int(4/clen)))
        
        if self.sel_clip == None:
            self.oscServer.sendOSC('/4/title', 'Please select a midi clip')
        else:
            self.oscServer.sendOSC('/4/title', track + ': ' + clip + ' | Step Size: ' + quan)
    
        self.oscServer.sendOSC('/4/quant', clen) 

    
    def get_note_line(self):
        self.log('note line')
        if self.fold == 1:
            folded_notes = self.note_keys()
    
        msgs = []
        for i in range(self.height+1):
            if i == 0:
                msgs.append(['/4/label' + str(i+1),  self.to_note(self.last_note)])
            else:
                if self.fold == 1:
                    self.log(str(folded_notes))
                
                    id = i - 1
                    if id < len(folded_notes):
                        msgs.append(['/4/label' + str(i+1),  self.to_note(folded_notes[id])])
                        msgs.append(['/4/toggle' + str(i),  int(self.mutes[folded_notes[id]])])
                    else:
                        msgs.append(['/4/label' + str(i+1), " "])
                        msgs.append(['/4/toggle' + str(i), 0])
                else:
                    print str(i+1)
                    msgs.append(['/4/label' + str(i+1),  self.to_note(self.get_note(i-1))])
                    msgs.append(['/4/toggle' + str(i),  int(self.mutes[self.get_note(i-1)])])
                    
                    
        self.oscServer.sendBundle(msgs)
    
    def to_note(self, note):
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        return notes[int(note % 12)] + str(int(note / 12) - 2)
    
    def get_note(self, id):
        if self.scale == 'Chromatic':
            return self.offset + id + self.root
        
        else:    
            nid = (id % self.height)
            oid = int(id / self.height)
        
            return self.offset + self.root + self.scales[self.scale][nid] + (12 * oid)
    
    def beat_time(self, time):
        beats = int(time % 4)
        bars  = int(time/4)
        qb    = int(time * 4 % 4)

        return str(bars+1) + (self.quan < 2 and ("." + str(beats+1)) or "") + (self.quan < 0.5 and ("." + str(qb+1)) or "")

    def update_selection(self):
        if self.parent.mode in self.pageid:
            self.c_instance.set_session_highlight(self.sel_track,self.sel_scene,1,1,0)
        