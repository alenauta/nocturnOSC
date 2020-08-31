from math import sqrt

class Program:

    tr     = 0
    sc     = 0
    
    sel_tr = 0
    sel_sc = 0   

    locked = False
    device = [0,0]

# #####################################################################
# # Class Methods

    def set_wh(self, w, h):
        self.width = w
        self.height = h

    def do_button_press(self, type, id, val):
        pass
        
    def do_refresh_state(self):
        pass
        
    def do_bg(self):
        pass
        
    def destroy(self):
        pass
        
    def lock(self, state):
        self.locked = state
        self.log('lock: ' + str(state))
        
    def sel_track_change(self):
        pass
        
    def sel_scene_change(self):
        pass
    
    def sel_device_change(self, tid, did):
        if not self.locked:
            self.device = [tid, did]
        
    def rem_listeners(self):
        pass
    
# #####################################################################
# # Selected Area

    def do_scene_change(self, new):
        if self.sc != new:
            if self.parent.lc != None:
                for prog in self.parent.lc.prog:
                    prog.do_scene_change(new)  
        
            for prog in self.parent.prog:
                prog.sc = new
                prog.limits(2)
                prog.scene_changed()
            
            self.update_selection()
            
            if self.skip == 0:
                self.oscServer.sendOSC('/1/vscroll1', float(new)/float(len(self.song().scenes) - self.sheight + 1))
            
    def do_track_change(self, new):
        if self.tr != new:
            if self.parent.lc != None:
                for prog in self.parent.lc.prog:
                    prog.do_track_change(new)  
        
            for prog in self.parent.prog:
                prog.tr = new
                prog.limits(1)
                prog.track_changed()
            
            self.update_selection()
            
            if self.skip == 0:
                self.oscServer.sendOSC('/1/hscroll1', float(new)/float(len(self.song().visible_tracks) - self.twidth + 1))
            
    def track_changed(self):
        pass
        
    def scene_changed(self):
        pass
            
    def update_selection(self):
        self.log(self.name + ": tr"+ str(self.track) + " sc" + str(self.scene) + " wi" + str(self.twidth) + " he" + str(self.sheight))
        self.c_instance.set_session_highlight(self.track,self.scene,self.twidth,self.sheight,0)
        
    def log(self, msg):
        self.parent.log(self.name + ": " + msg)    
            
    def song(self):
        return self.parent.c_instance.song()

    def limits(self, type = 3):
        if type == 1 or type == 3:
            tracks = len(self.c_instance.song().visible_tracks)
            self.twidth = tracks < self.width  and tracks or self.width - 1

            if self.tr < tracks:
                if tracks < self.width:
                    self.track = 0
                else:
                    if self.tr + self.twidth < tracks:
                        self.track = self.tr
                    else:
                        self.track = tracks - self.twidth
            else:
                self.track = max(0, tracks - self.twidth)

            self.tr = self.track
            self.log("Limits Tracks: " + str(tracks) + "tr init " + str(self.tr) + " track offset: " + str(self.track) + " track width: " + str(self.twidth));
        
        if type == 2 or type == 3:
            scenes = len(self.c_instance.song().visible_tracks[0].clip_slots)
            self.sheight = scenes < self.height - 2 and scenes or self.height - 2
                        
            if self.sc < scenes:
                if scenes < self.height - 2:
                    self.scene = 0
                else:
                    if self.sc + self.sheight < scenes:
                        self.scene = self.sc
                    else:
                        self.scene = scenes - self.sheight
            else:
                self.scene = max(0, scenes - self.sheight)
            
            self.sc = self.scene
            self.log("Limits Scenes: " + str(scenes) + "sc init " + str(self.sc) + " scene offset: " + str(self.scene) + " scene width: " + str(self.sheight))     

            
# #####################################################################
# # Helpers       

    def is_current(self):
        return self.parent.mode in self.pageid

    def has_size(self):
        return self.parent.ipad is not None

    def to_color(self, rgb, inv = 0):
        b = rgb & 255
        g = (rgb >> 8) & 255
        r = (rgb >> 16) & 255

        if inv:
            r = 255 - r
            g = 255 - g
            b = 255 - b

        palette = { #'gray':     [100,100,100],
                    'red':      [255,0,0],
                    'orange':   [255,127,0],
                    'yellow':   [200,200,0],
                    'green':    [0,255,0],
                    'blue':     [0,0,255],
                    'purple':   [127,0,255],
                    }
        
        col = None
        min = 1000
        
        for (name, rgb) in palette.items():
            dist = sqrt(pow(r - rgb[0], 2) + pow(g - rgb[1], 2) + pow(b - rgb[2], 2))
        
            if dist < min:
                min = dist
                col = name
        
        return col
     
    def register_inputs(self):
        if hasattr(self, 'controls'):
            for control in self.controls:
                self.parent.oscServer.callbackManager.add(self.parent.button_press, control)

    def to_ascii(self, text):
        return "".join([ (ord(c) > 127 and '' or str(c) ) for c in text ])

    def rlookup(self, d, v):
        for k in d:
            if d[k] == v:
                return k 
        
    def tuple_idx(self, tuple, obj):
        for i in xrange(0,len(tuple)):
            if (tuple[i] == obj):
                return i
                
    def getslots(self):
        tracks = self.song().visible_tracks

        clipSlots = []
        for track in tracks:
            clipSlots.append(track.clip_slots)
        return clipSlots 

    def trunc_string(self, display_string, length):
        display_string = self.to_ascii(display_string)

        if self.parent.ipad == 1:
            length += 5
    
        if (not display_string):
            return (' ' * length)
        if ((len(display_string.strip()) > length) and (display_string.endswith('dB') and (display_string.find('.') != -1))):
            display_string = display_string[:-2]
        if (len(display_string) > length):
            for um in [' ',
             'i',
             'o',
             'u',
             'e',
             'a']:
                while ((len(display_string) > length) and (display_string.rfind(um, 1) != -1)):
                    um_pos = display_string.rfind(um, 1)
                    display_string = (display_string[:um_pos] + display_string[(um_pos + 1):])

        else:
            display_string = display_string.ljust(length)

        return display_string[0:length] 

        
# #####################################################################
# # Track IDs

    def tracks(self):
        tracks = tuple(self.song().visible_tracks) + tuple(self.song().return_tracks) + (self.song().master_track,)
        #tracks.append(self.song().master_track)
        
        return tracks
        
    def track_idx(self, track):
        return self.tuple_idx(self.tracks(), track)
        
    def sel_track_right(self, size = 1):
        tid = self.track_idx(self.song().view.selected_track)
        self.log('tr right')
        if len(self.tracks()) > tid + size:
            self.song().view.selected_track = self.tracks()[tid + size]
        else:
            self.song().view.selected_track = self.tracks()[-1]
    
    def sel_track_left(self, size = 1):
        tid = self.track_idx(self.song().view.selected_track)
        self.log('tr left')
        if tid - size > 0:
            self.song().view.selected_track = self.tracks()[tid - size]
        else:
            self.song().view.selected_track = self.tracks()[0]
            
    def track_right(self):
        size = self.shift == 1 and 1 or (self.width - 1)
            
        if len(self.tracks()) > self.tr + size:
            self.do_track_change(self.tr + size)
        else:
            self.do_track_change(len(self.tracks()) - 1)
    
    def track_left(self):
        size = self.shift == 1 and 1 or (self.width - 1)
                
        if self.tr - size > 0:
            self.do_track_change(self.tr - size)
        else:
            self.do_track_change(0)
            
    def page_selected(self):
        pass