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
import os

class TrackControl(Program):
    name = "Track Control"
    pageid = [2,6,7,8]
    
    def __init__(self, parent, width, height):
        self.width = width
        self.height = height    
    
        self.parent = parent
        self.c_instance = parent.c_instance
        self.oscServer = parent.oscServer
        
        self.listen = {}
        
        self.shift = 0
        self.mode = 0
        self.send = 0
        
        self.update = 0
        self.skip = 0
        
        self.mlcache = [-1 for i in range(self.width)] 
        self.mrcache = [-1 for i in range(self.width)] 
        self.ccache  = [-1 for i in range(self.width)]
        self.quant   = None

        #self.do_refresh_state()

    def set_wh(self, w, h):
        self.width = w
        self.height = h
        
        self.mlcache = [-1 for i in range(self.width)] 
        self.mrcache = [-1 for i in range(self.width)] 
        self.ccache  = [-1 for i in range(self.width)]        

    def cue_change(self):
        if not self.skip:
            self.oscServer.sendOSC('/2/rotary1', float(self.song().master_track.mixer_device.cue_volume.value))

    def sel_track_change(self):
        self.log('tr change')
        self.mode_led(self.mode)

    def mode_led(self, id):
        msgs = []
    
        for i in range(3):
            if i == id:
                msgs.append(['/2/led'+str(i+1), 1])
            else:
                msgs.append(['/2/led'+str(i+1), 0])
        
        if self.mode == 2:
            if self.send < len(self.song().return_tracks):
                msgs.append(['/2/label'+str(self.width), self.trunc_string(self.song().return_tracks[self.send].name, 6)])
            else:
                msgs.append(['/2/label'+str(self.width), ''])
                
        else:
            msgs.append(['/2/label'+str(self.width), 'Master'])
        
        for j in range(7,9):
            if self.send < len(self.song().return_tracks):
                msgs.append(['/'+str(j)+'/send', self.trunc_string(self.song().return_tracks[self.send].name, 6)])

                tid = self.tuple_idx(self.song().visible_tracks, self.song().view.selected_track)
                if tid != None:
                    msgs.append(['/'+str(j)+'/fader1', self.song().view.selected_track.mixer_device.sends[self.send].value])
            else:
                msgs.append(['/'+str(j)+'/send', ''])
                msgs.append(['/'+str(j)+'/fader1', 0])
                        
        self.oscServer.sendBundle(msgs)
        
    def default_labels(self):
        msgs = []
        msgs.append(['/2/2nlabel1', 'Stop'])
        msgs.append(['/2/2nlabel2', 'Start'])
        msgs.append(['/2/2nlabel3', 'Record'])
        msgs.append(['/2/2nlabel4', 'Ovr ' + (self.song().overdub and 'Off' or 'On')])
        msgs.append(['/2/2nlabel5', 'Met ' + (self.song().metronome and 'Off' or 'On')])
        msgs.append(['/2/nlabel6', 'LQ-'])
        msgs.append(['/2/nlabel7', 'LQ+'])
        
        self.oscServer.sendBundle(msgs)

    def select_labels(self):
        msgs = []
        
        rets = self.song().return_tracks
        for i in range(5):
            if i < len(rets):
                msgs.append(['/2/2nlabel'+str(i+1), self.trunc_string(rets[i].name, 7)])
            else:
                msgs.append(['/2/2nlabel'+str(i+1), " "])
        
        msgs.append(['/2/nlabel6', 'RQ-'])
        msgs.append(['/2/nlabel7', 'RQ+'])
        
        self.oscServer.sendBundle(msgs)
        
    def rem_listeners(self):
        for tr in self.listen:
            if tr != None:
                ocb = self.listen[tr]
                if hasattr(tr, 'solo'):
                    if tr.solo_has_listener(ocb) == 1:
                        tr.remove_solo_listener(ocb)
                
                if hasattr(tr, 'mute'):
                    if tr.mute_has_listener(ocb) == 1:
                        tr.remove_mute_listener(ocb)
                    
                if (tr.can_be_armed == 1) and (tr.arm_has_listener(ocb) == 1):
                    tr.remove_arm_listener(ocb)

                if tr.mixer_device.volume.value_has_listener(ocb) == 1:
                    tr.mixer_device.volume.remove_value_listener(ocb)
                    
                if tr.mixer_device.panning.value_has_listener(ocb) == 1:
                    tr.mixer_device.panning.remove_value_listener(ocb)
                
                if tr.can_be_armed == 1 and tr.current_monitoring_state_has_listener(ocb) == 1:
                    tr.remove_current_monitoring_state_listener(ocb)
                    
                for i in range(len(tr.mixer_device.sends)):
                    if tr.mixer_device.sends[i].value_has_listener(ocb) == 1:
                        tr.mixer_device.sends[i].remove_value_listener(ocb)
                        
                if tr.name_has_listener(self.update_mixer):
                    tr.remove_name_listener(self.update_mixer)
                    
                #if tr.color_has_listener(self.update_mixer):
                #    tr.remove_color_listener(self.update_mixer)
                        
                self.log("Removed Mixer Listener: " + self.to_ascii(tr.name) + " cb: " + str(ocb))   
                
        self.listen = {}
        
        cue = self.song().master_track.mixer_device.cue_volume
        if cue.value_has_listener(self.cue_change):
            cue.remove_value_listener(self.cue_change)
        
    def add_listeners(self):       
        self.rem_listeners()
    
        tracks = self.tracks()
        for i in range(len(tracks)):
            self.add_mixerlistener(i, tracks[i])

        cue = self.song().master_track.mixer_device.cue_volume
        if not cue.value_has_listener(self.cue_change):
            cue.add_value_listener(self.cue_change)

    def add_mixerlistener(self, tid, track):
        cb = lambda :self.mixer_changestate(tid, track)

        if self.listen.has_key(track) != 1:
            if hasattr(track, 'solo'):
                track.add_solo_listener(cb)
                track.add_mute_listener(cb)

            if track.can_be_armed == 1:
                track.add_arm_listener(cb)
                track.add_current_monitoring_state_listener(cb)
            
            track.mixer_device.volume.add_value_listener(cb)
            track.mixer_device.panning.add_value_listener(cb)
            
            for i in range(len(track.mixer_device.sends)):
                track.mixer_device.sends[i].add_value_listener(cb)
            
            self.log("Added Mixer Listener: " + str(tid) + " track: " + self.to_ascii(track.name))
                
            track.add_name_listener(self.update_mixer)
            #track.add_color_listener(self.update_mixer)
            
            self.listen[track] = cb
            
    def mixer_changestate(self, tid, track):
        msgs = []
        
        if self.skip == 5:
            #if self.parent.ipad:
            if not hasattr(track, 'solo'):
                msgs.append(['/1/vol' + str(self.width), self.song().master_track.mixer_device.volume.value])
            else:
                id = tid - self.track + 1
                msgs.append(['/1/vol' + str(id), track.mixer_device.volume.value])
    
        if self.skip == 0 or self.skip == 4:
            self.do_update_tr(tid, track)

            tr = self.song().view.selected_track
            if tr == track:
                if self.send < len(self.song().return_tracks):
                    for j in range(7,9):
                        msgs.append(['/'+str(j)+'/fader1', track.mixer_device.sends[self.send].value])
            
        else:
            self.update = 4
    
        if len(msgs) > 0:
            self.oscServer.sendBundle(msgs)
    
    def do_update_tr(self, tid, track):
        sl = len(track.mixer_device.sends)
        msgs = []
        
        if not hasattr(track, 'solo'):
            if self.mode == 0:
                msgs.append(['/2/fader'+str(self.width), track.mixer_device.volume.value])
                
            elif self.mode == 1:
                msgs.append(['/2/fader'+str(self.width), (track.mixer_device.panning.value+1)/2])
                
            #if self.parent.ipad:
            msgs.append(['/2/vol' + str(self.width), track.mixer_device.volume.value])
        
        if tid < self.twidth + self.track:
            id = tid - self.track + 1

            if not self.skip == 4:
                msgs.append(['/2/vol' + str(id), track.mixer_device.volume.value])

            if self.mode == 0:
                msgs.append(['/2/fader' + str(id), track.mixer_device.volume.value])
                
            elif self.mode == 1:
                msgs.append(['/2/fader' + str(id), (track.mixer_device.panning.value+1)/2])
                
            elif self.mode == 2:
                if self.send < len(self.song().return_tracks):
                    msgs.append(['/2/fader' + str(id), track.mixer_device.sends[self.send].value])
                
            self.update_track(tid, id-1)

        else:
            if self.mode == 2:
                if self.send < len(self.song().return_tracks):
                    if tid == self.send + len(self.song().visible_tracks):
                        msgs.append(['/2/fader'+str(self.width), self.song().return_tracks[self.send].mixer_device.volume.value])

        self.oscServer.sendBundle(msgs)
        
    def do_refresh_state(self):
        self.limits()
        self.add_listeners()
        
        if len(self.song().return_tracks) > 0:
            self.oscServer.sendOSC('/2/nlabel3', self.trunc_string(self.song().return_tracks[self.send].name, 6))
            
        self.cue_change()
        self.mode_led(0)
        
        self.update_mixer()
        self.update_tracks()
        
    def update_mixer(self):
        msgs = []
    
        for i in range(self.width): 
            if i == self.width - 1:
                if self.parent.ipad and not self.skip == 4:
                    msgs.append(['/1/vol' + str(i+1), self.song().master_track.mixer_device.volume.value])
            
                if self.mode == 0:
                    msgs.append(['/2/fader' + str(i+1), self.song().master_track.mixer_device.volume.value])
                    
                elif self.mode == 1:
                    msgs.append(['/2/fader' + str(i+1), (self.song().master_track.mixer_device.panning.value+1)/2])
                    
                elif self.mode == 2:
                    if self.send < len(track.mixer_device.sends):
                        msgs.append(['/2/fader' + str(i+1), self.song().return_tracks[self.send].mixer_device.volume.value])
        
            elif i < self.twidth:
                tr = i + self.track                
                track = self.song().visible_tracks[tr]

                if not track.has_midi_output:
                    msgs.append(['/2/fader' + str(i+1) + '/color', 'red'])
                    msgs.append(['/2/fader' + str(i+1) + 'l/color', 'green'])
                    msgs.append(['/2/fader' + str(i+1) + 'r/color', 'green'])
                else:
                    msgs.append(['/2/fader' + str(i+1) + '/color', 'gray'])
                    msgs.append(['/2/fader' + str(i+1) + 'l/color', 'gray'])
                    msgs.append(['/2/fader' + str(i+1) + 'r/color', 'gray'])
                
                msgs.append(['/2/fader' + str(i+1) + '/visible', 1])
                msgs.append(['/2/fader' + str(i+1) + 'l/visible', 1])
                msgs.append(['/2/fader' + str(i+1) + 'r/visible', 1])

                msgs.append(['/2/toggle' + str(i+((self.width-1)*4)+1) + '/visible', 1])
                msgs.append(['/2/toggle' + str(i+((self.width-1)*5)+1) + '/visible', 1])
                
                if track.can_be_armed:
                    msgs.append(['/2/toggle' + str(i+((self.width-1)*6)+1) + '/visible', 1])
                else:
                    msgs.append(['/2/toggle' + str(i+((self.width-1)*6)+1) + '/visible', 0])


                msgs.append(['/2/push' + str(i+1) + '/visible', 1])

                msgs.append(['/2/label' + str(i+1), self.trunc_string(track.name, 6).strip()])
                msgs.append(['/6/label' + str(i+1), self.trunc_string(track.name, 6).strip()])
                msgs.append(['/3/2nlabel' + str(i+1), self.trunc_string(track.name, 6).strip()])
                msgs.append(['/1/trlabel' + str(i+1), self.trunc_string(track.name, 6).strip()])

                #col = self.to_color(track.color)
                
                #msgs.append(['/1/trlabel' + str(i+1) + '/color', col])
                #msgs.append(['/1/fader' + str(i+1) + '/color', col])
                #msgs.append(['/1/vol' + str(i+1) + '/color', col])
                
                if self.parent.ipad and not self.skip == 4:
                    msgs.append(['/1/vol' + str(i+1), track.mixer_device.volume.value])
                
                if self.mode == 0:
                    msgs.append(['/2/fader' + str(i+1), track.mixer_device.volume.value])
                    
                elif self.mode == 1:
                    msgs.append(['/2/fader' + str(i+1), (track.mixer_device.panning.value+1)/2])
                    
                elif self.mode == 2:
                    if len(track.mixer_device.sends) > self.send:
                        msgs.append(['/2/fader' + str(i+1), track.mixer_device.sends[self.send].value])
                    else:
                        msgs.append(['/2/fader' + str(i+1), 0])
                        
            else:
                if self.parent.ipad and not self.skip == 4:
                    msgs.append(['/1/vol' + str(i+1), 0])

                msgs.append(['/2/fader' + str(i+1), 0])

                msgs.append(['/2/fader' + str(i+1) + '/visible', 0])
                msgs.append(['/2/fader' + str(i+1) + 'l/visible', 0])
                msgs.append(['/2/fader' + str(i+1) + 'r/visible', 0])
                msgs.append(['/2/toggle' + str(i+((self.width-1)*4)+1) + '/visible', 0])
                msgs.append(['/2/toggle' + str(i+((self.width-1)*5)+1) + '/visible', 0])
                msgs.append(['/2/toggle' + str(i+((self.width-1)*6)+1) + '/visible', 0])
                msgs.append(['/2/push' + str(i+1) + '/visible', 0])
                
                msgs.append(['/6/label' + str(i+1), " "])
                msgs.append(['/1/trlabel' + str(i+1), " "])
                msgs.append(['/3/2nlabel' + str(i+1), " "])
                msgs.append(['/2/label' + str(i+1), " "])
        
        if self.send < len(track.mixer_device.sends):
            msgs.append(['/2/nlabel3', self.trunc_string(self.song().return_tracks[self.send].name, 6).strip()])
        else:
            msgs.append(['/2/nlabel3', ''])
        
        self.oscServer.sendBundle(msgs)
        self.update_tracks()

    def update_tracks(self):
        for i in range(self.width-1): 
            if i < self.twidth:
                tr = i + self.track 
                self.update_track(tr, i)
                
            else:
                for j in range(7):
                    self.oscServer.sendOSC('/6/toggle' + str((j*(self.width-1))+i+1), 0)
                    
                self.oscServer.sendOSC('/6/label' + str(i+1), " ")
        
    def track_changed(self):
        self.update_tracks()
        self.update_mixer()
        
    def update_track(self, tr, i):
        track = self.song().visible_tracks[tr]
        msgs = []
           
        msgs.append(['/6/toggle' + str(i+1), round(track.mixer_device.volume.value,2) == 0.85 and 1 or 0])
        msgs.append(['/6/toggle' + str(i+self.width), track.mixer_device.panning.value == 0 and 1 or 0])
        
        send = 0
        for j in range(len(track.mixer_device.sends)):
            if track.mixer_device.sends[j].value > 0:
                send += 1
                
        msgs.append(['/6/toggle' + str(i+((self.width-1)*2)+1), send == 0 and 1 or 0])
        msgs.append(['/6/toggle' + str(i+((self.width-1)*4)+1), track.mute == 0 and 1 or 0])
        msgs.append(['/6/toggle' + str(i+((self.width-1)*5)+1), track.solo == 1 and 1 or 0])
        
        if track.can_be_armed:
            msgs.append(['/6/toggle' + str(i+((self.width-1)*3)+1), track.current_monitoring_state])
            msgs.append(['/6/toggle' + str(i+((self.width-1)*6)+1), track.arm == 1 and 1 or 0])
        
        self.oscServer.sendBundle(msgs)
                
    def do_button_press(self, page, type, id, val, xy = []):
        self.log(str(page)+ str(type) + str(id))
        if page == 6:
            if type == 'nav':
                if val == 1:
                    if id == 1:
                        self.track_left()
                    
                    elif id == 2:
                        self.track_right()
        
            elif type == 'toggle':
                self.skip = 4
            
                type = int((id-1) / (self.width - 1))
                tr   = (id-1) % (self.width - 1) + self.track
                track = self.song().visible_tracks[tr]
            
                if val == 1:
                    if type == 0:
                        track.mixer_device.volume.value = 0.85
                    
                    elif type == 1:
                        track.mixer_device.panning.value = 0
                    
                    elif type == 2:
                        for i in range(len(track.mixer_device.sends)):
                            track.mixer_device.sends[i].value = 0
                            
                    elif type == 3:
                        if track.current_monitoring_state == 0:
                            track.current_monitoring_state = 1
                        else:
                            track.current_monitoring_state = 0
                            
                if type == 4:
                    self.log(str(val) + " " + str(track.mute))
                    if val == 1:
                        track.mute = 0
                    else:
                        track.mute = 1
                    
                elif type == 5:
                    track.solo = int(val)
                    
                elif type == 6:
                    if track.can_be_armed:
                        track.arm = int(val)
                        

        elif page == 2:            
            if type == 'nav':
                if val == 1:
                    if id < 4:
                        self.mode = id - 1
                        self.mode_led(self.mode)
                        self.update_mixer()
                        
                    elif id == 4:
                        self.track_left()
                    
                    elif id == 5:
                        self.track_right()
                        
                    elif id == 6:
                        if self.shift == 1:
                            self.song().midi_recording_quantization = self.song().midi_recording_quantization + 1
                        else:
                            self.song().clip_trigger_quantization = self.song().clip_trigger_quantization + 1
    
                    elif id == 7:
                        if self.shift == 1:
                            self.song().midi_recording_quantization = self.song().midi_recording_quantization - 1
                        else:
                            self.song().clip_trigger_quantization = self.song().clip_trigger_quantization - 1
        
            elif type == 'vol':
                self.skip = 4
                
                if id == self.width:
                    self.song().master_track.mixer_device.volume.value = val
                else:
                    tr = id + self.track - 1
                    self.song().visible_tracks[tr].mixer_device.volume.value = val
    
        
            elif type == 'push':
                tr   = (id-1) + self.track
                track = self.song().visible_tracks[tr]
            
                if val == 1:
                    if self.mode == 0:
                        track.mixer_device.volume.value = 0.85
                    
                    elif self.mode == 1:
                        track.mixer_device.panning.value = 0
                    
                    elif self.mode == 2:
                        for i in range(len(track.mixer_device.sends)):
                            track.mixer_device.sends[i].value = 0
        
            elif type == 'rotary':
                if id == 1:
                    self.skip = 1
                    self.song().master_track.mixer_device.cue_volume.value = val
        
            elif type == '2nav':
                if id == 8:
                    self.shift = val
                    
                    if self.shift == 1:
                        self.select_labels()
                    else:
                        self.default_labels()
                    
                if val == 1:
                    if id < 6:
                        if self.shift == 1:
                            self.send = id - 1
                            
                            self.mode = 2
                            self.mode_led(self.mode)
                            
                            self.update_mixer()
                        
                        else:
                            if id == 1:
                                self.song().stop_playing()
                            elif id == 2:
                                self.song().start_playing()
                            
                            elif id == 3:
                                if self.song().record_mode == 1:
                                    self.song().record_mode = 0
                                else:
                                    self.song().record_mode = 1
                            
                            elif id == 4:
                                if self.song().overdub == 1:
                                    self.song().overdub = 0
                                else:
                                    self.song().overdub = 1
                                    
                                self.oscServer.sendOSC('/2/2nlabel4', "Ovr " + (self.song().overdub and 'On' or 'Off'))                                    
                            
                            elif id == 5:
                                if self.song().metronome == 1:
                                    self.song().metronome = 0
                                else:
                                    self.song().metronome = 1
                                    
                                self.oscServer.sendOSC('/2/2nlabel5', "Met " + (self.song().metronome and 'On' or 'Off'))
                    if id == 6:
                        if self.send > 0:
                            self.send -= 1
                            self.mode_led(self.mode)
                            self.update_mixer()
                            
                    elif id == 7:
                        if self.send < len(self.song().visible_tracks[0].mixer_device.sends) - 1:
                            self.send += 1
                            self.mode_led(self.mode)
                            self.update_mixer()
        
            if type == 'fader':
                self.update = 4
                self.skip = 1
            
                if id == self.width:
                    if self.mode == 0:
                        self.skip = 5
                        self.song().master_track.mixer_device.volume.value = val

                    elif self.mode == 1:
                        self.song().master_track.mixer_device.panning.value = (val*2) - 1
                        
                    elif self.mode == 2:
                        if self.send < len(self.song().return_tracks):
                            self.song().return_tracks[self.send].mixer_device.volume.value = val
                else:
                    tr = id + self.track - 1
                    
                    if self.mode == 0:
                        self.skip = 5
                        self.song().visible_tracks[tr].mixer_device.volume.value = val

                    elif self.mode == 1:
                        self.song().visible_tracks[tr].mixer_device.panning.value = (val*2) - 1
                        
                    elif self.mode == 2:
                        if len(self.tracks()[tr].mixer_device.sends) > 0:
                            self.song().visible_tracks[tr].mixer_device.sends[self.send].value = val
                 
        elif page == 7 or page == 8:
            if type == 'fader':
                self.skip = 1

                if id == 1:
                    tid = self.tuple_idx(self.song().visible_tracks, self.song().view.selected_track)
                    if tid != None:
                        self.log(str('hi'))
                        self.song().view.selected_track.mixer_device.sends[self.send].value = val
                
            if type == 'nav':
                if val == 1:
                    if id == 3:
                        tr = self.song().view.selected_track
                        dev = tr.view.selected_device
                        did = self.tuple_idx(tr.devices, dev)
                        
                        if did > 0:
                            self.song().view.select_device(tr.devices[did-1])
                    
                    elif id == 4:
                        tr = self.song().view.selected_track
                        dev = tr.view.selected_device
                        did = self.tuple_idx(tr.devices, dev)
                        
                        if did < len(tr.devices) - 1:
                            self.song().view.select_device(tr.devices[did+1])
                                            
                    elif id == 5:
                        if self.send > 0:
                            self.send -= 1
                            self.mode_led(self.mode)
                            self.update_mixer()
                    
                    elif id == 6:
                        if self.send < len(self.song().visible_tracks[0].mixer_device.sends) - 1:
                            self.send += 1
                            self.mode_led(self.mode)
                            self.update_mixer()                    
                    
            if type == '2nav':
                self.log('undo/redo')
                if val == 1:
                    if id == 1:
                        #if self.song().can_undo():
                        self.song().undo()
                            
                    elif id == 2:
                        #if self.song().can_redo():
                        self.song().redo()
                 
    def do_bg(self):
        if self.update > 0:
            self.update -= 1
            
        if self.update == 1:
            self.skip = 0
        
    def do_update(self):
        if self.update < 3:
            if self.parent.mode == 2:
                tracks = self.tracks()
            
                for i in range(self.width):
                    if i == self.width - 1:
                        if self.mode == 2:
                            if self.send < len(self.song().return_tracks):
                                vall = (pow(10, self.song().return_tracks[self.send].output_meter_left)-1)/10.0
                                valr = (pow(10, self.song().return_tracks[self.send].output_meter_right)-1)/10.0                                
                            else:
                                vall = 0
                                valr = 0
                            
                        else:
                            vall = (pow(10, self.song().master_track.output_meter_left)-1)/10.0
                            valr = (pow(10, self.song().master_track.output_meter_right)-1)/10.0
                    
                    elif i < self.twidth:
                        tr = i + self.track
                        track = tracks[tr]
                            
                        if track.has_audio_output:
                            vall = (pow(10, track.output_meter_left)-1)/10.0
                            valr = (pow(10, track.output_meter_right)-1)/10.0
                        else:
                            vall = 0
                            valr = 0
                            
                    else:
                        vall = 0
                        valr = 0

                    vall = round(vall, 2)
                    valr = round(valr, 2)
                        
                    msgs = []
                    
                    clip = 0
                    if vall > 0.848 or valr > 0.848:
                        clip = 1
                    
                    if vall != self.mlcache[i]:
                        msgs.append(['/2/fader' + str(i+1) + 'l', vall])
                        self.mlcache[i] = vall
                        
                    if valr != self.mrcache[i]:
                        msgs.append(['/2/fader' + str(i+1) + 'r', valr])
                        self.mrcache[i] = valr
                            
                    if clip != self.ccache[i]:
                        msgs.append(['/2/clip'+str(i+1), clip])
                        self.ccache[i] = clip

                    rec_quants = {  'rec_q_eight': '1/8',
                                    'rec_q_eight_eight_triplet': '1/8T',
                                    'rec_q_eight_triplet': '1/8+T',
                                    'rec_q_no_q': 'None',
                                    'rec_q_quarter': '1/4',
                                    'rec_q_sixtenth': '1/16',
                                    'rec_q_sixtenth_sixtenth_triplet': '1/16+T',
                                    'rec_q_sixtenth_triplet': '1/16T' }
                    
                    quants = {  'q_2_bars': '2 bars',
                                'q_4_bars': '4 bars',
                                'q_8_bars': '8 bars',
                                'q_bar': '1 bar',
                                'q_eight': '1/8',
                                'q_eight_triplet': '1/8T',
                                'q_half': '1/2',
                                'q_half_triplet': '1/2T',
                                'q_no_q': 'None',
                                'q_quarter': '1/4',
                                'q_quarter_triplet': '1/4T',
                                'q_sixtenth': '1/16',
                                'q_sixtenth_triplet': '1/16T',
                                'q_thirtytwoth': '1/32' }

                    quant = self.shift and rec_quants[self.song().midi_recording_quantization.name] or quants[self.song().clip_trigger_quantization.name]
                    if quant != self.quant:
                        msgs.append(['/2/quant', quant])
                        self.quant = quant

                    self.oscServer.sendBundle(msgs)
                    