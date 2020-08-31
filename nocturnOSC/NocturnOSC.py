"""
# This set of script is heavily based on LiveControl by ST8 <st8@q3f.org>
# My contribution was to add the MIDI funcionality to control the underrated
# Novation Nocturn and fix some bugs.

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3.0 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

# alenauta 2020

"""

import Live
import RemixNet
import re
import os
import ConfigParser


class NocturnOSC:
    __module__ = __name__
    __doc__ = "NocturnOSC Ableton Live Control Interface"

    width = 8
    height = 6

    ipad = None

    receive_port = 9000
    send_port = 9001

    local_ip = '127.0.0.1'
    remote_ip = '127.0.0.1'

    locked = False

    name = "NocturnOSC"

    def __init__(self, c_instance):
        self.c_instance = c_instance

        self.LOGGING = 0

        self.load_settings()

        self.oscServer = RemixNet.OSCServer(
            self, self.remote_ip, self.send_port, self.local_ip, self.receive_port)
        self.oscServer.sendOSC('/connected', 1)
        self.oscServer.callbackManager.add(self.set_ipad, '/ipad')
        self.oscServer.callbackManager.add(self.set_debug, '/debug')

        for j in range(1, 9):
            self.oscServer.callbackManager.add(
                self.button_press, '/1/stop' + str(j))
            self.oscServer.callbackManager.add(
                self.button_press, '/1/trpush' + str(j))
            self.oscServer.callbackManager.add(
                self.button_press, '/3/rotary' + str(j))
            self.oscServer.callbackManager.add(
                self.button_press, '/2/fader' + str(j))
            self.oscServer.callbackManager.add(
                self.button_press, '/4/toggle' + str(j))
            self.oscServer.callbackManager.add(
                self.button_press, '/2/push' + str(j))
            self.oscServer.callbackManager.add(
                self.button_press, '/3/push' + str(j))
            self.oscServer.callbackManager.add(
                self.button_press, '/3/toggle' + str(j))

        self.oscServer.callbackManager.add(self.button_press, '/2/fader9')
        self.oscServer.callbackManager.add(self.button_press, '/1/stop9')

        self.oscServer.callbackManager.add(self.button_press, '/1/vscroll1')
        self.oscServer.callbackManager.add(self.button_press, '/1/hscroll1')

        self.oscServer.callbackManager.add(self.button_press, '/3/toggle0')
        self.oscServer.callbackManager.add(self.button_press, '/2/rotary1')
        self.oscServer.callbackManager.add(self.button_press, '/4/toggle0')
        self.oscServer.callbackManager.add(self.button_press, '/4/push1')
        self.oscServer.callbackManager.add(self.button_press, '/4/push2')

        for i in range(1, 10):
            self.oscServer.callbackManager.add(
                self.button_press, '/2/vol' + str(i))

        for i in range(1, 17):
            self.oscServer.callbackManager.add(
                self.button_press, '/4/multifader1/' + str(i))

        for i in range(1, 9):
            for j in range(1, 17):
                self.oscServer.callbackManager.add(
                    self.button_press, '/4/multitoggle1/' + str(i) + '/' + str(j))

        for i in range(7, 9):
            self.oscServer.callbackManager.add(
                self.button_press, '/' + str(i) + '/fader1')

            for j in range(1, 5):
                self.oscServer.callbackManager.add(
                    self.button_press, '/' + str(i) + '/rotary' + str(j))

        for i in range(1, 9):
            self.oscServer.callbackManager.add(self.page_change, '/' + str(i))

            for j in range(1, 9):
                self.oscServer.callbackManager.add(
                    self.button_press, '/' + str(i) + '/nav' + str(j))
                self.oscServer.callbackManager.add(
                    self.button_press, '/' + str(i) + '/2nav' + str(j))

        for i in range(9, 14):
            self.oscServer.callbackManager.add(
                self.button_press, '/4/2nav' + str(i))

        for i in range(9, 11):
            self.oscServer.callbackManager.add(
                self.button_press, '/2/2nav' + str(i))

        for i in range(1, 70):
            self.oscServer.callbackManager.add(
                self.button_press, '/1/push' + str(i))
            self.oscServer.callbackManager.add(
                self.button_press, '/6/toggle' + str(i))

        for i in range(1, 19):
            self.oscServer.callbackManager.add(
                self.button_press, '/4/push' + str(i))
            self.oscServer.callbackManager.add(
                self.button_press, '/5/push' + str(i))

        for i in range(1, 5):
            self.oscServer.callbackManager.add(
                self.button_press, '/5/xy' + str(i))

        for i in range(1, 6):
            self.oscServer.callbackManager.add(
                self.button_press, '/4/fader' + str(i))
        self.oscServer.callbackManager.add(self.button_press, '/4/push1')

        self.mode = 1
        self.prog = []

        self._menu = 0

        self.update_time = 0

        # Track / scene change callbacks
        if self.song().view.selected_scene_has_listener(self.scene_change) != 1:
            self.song().view.add_selected_scene_listener(self.scene_change)

        if self.song().view.selected_track_has_listener(self.track_change) != 1:
            self.song().view.add_selected_track_listener(self.track_change)

        # Visible tracks listener
        if self.song().visible_tracks_has_listener(self.refresh_state) != 1:
            self.song().add_visible_tracks_listener(self.refresh_state)

        # Load programs
        for prog in ['ClipLauncher', 'TrackControl', 'DeviceControl', 'Sequencer']:
            exec "import " + prog
            eval("self.prog.append(" + prog + "." +
                 prog + "(self, self.width, self.height))")

        self.lc = None

    def set_ipad(self, msg):
        self.log(str(msg))
        self.ipad = msg[2]

        if msg[2] == 1:
            self.width = 9
            self.height = 9
        else:
            self.width = 8
            self.height = 6

        for prog in self.prog:
            prog.set_wh(self.width, self.height)

        self.refresh_state()
        # if not self.conn:
        #    self.oscServer.sendOSC('/connected', 1)
        #    self.conn = 1

    def set_debug(self, msg):
        if msg[2] == 1:
            self.LOGGING = 1
            self.log('Logging Enabled')
        else:
            self.log('Logging Disabled')
            self.LOGGING = 0

    def load_settings(self):
        config = ConfigParser.ConfigParser()
        try:
            config.read(os.path.join(
                os.path.dirname(__file__), 'nocturnOSC.conf'))
        except:
            self.log('error reading conf file')
            pass

        try:
            self.LOGGING = int(config.get("NocturnOSC", "debug"))
        except:
            self.LOGGING = 0

        try:
            self.remote_ip = config.get("NocturnOSC", "remote")
        except:
            self.remote_ip = '127.0.0.1'

        try:
            self.local_ip = config.get("NocturnOSC", "local")
        except:
            self.local_ip = '127.0.0.1'

        try:
            self.send_port = int(config.get("NocturnOSC", "send"))
        except:
            self.send_port = 9001

        try:
            self.receive_port = int(config.get("NocturnOSC", "receive"))
        except:
            self.receive_port = 9000

        try:
            ipad = int(config.get("NocturnOSC", "ipad"))
        except:
            ipad = 0

        self.ipad = ipad

        if ipad == 1:
            self.height = 9
            self.width = 9

    def page_change(self, msg):
        self.mode = int(str(msg[0])[1:])
        self.log('page ' + str(self.mode))

        for prog in self.prog:
            if self.mode in prog.pageid:
                prog.page_selected()
                prog.update_selection()

    def button_press(self, msg):
        if msg[0].find('xy') > -1:
            m = re.match('/(\d+)/(\w+?)(\d+)', msg[0])

            for prog in self.prog:
                if int(m.group(1)) in prog.pageid:
                    prog.do_button_press(int(m.group(1)), m.group(
                        2), int(m.group(3)), 0, [msg[2], msg[3]])

        elif msg[0].find('multifader') > -1:
            m = re.match('/(\d+)/(\w+?)(\d+)/(\d+)', msg[0])
            #self.log("page: " + str(m.group(1)) + "type: " + m.group(2) + " id:" + str(m.group(3)) + " val:" + str(msg[2]) + "[" + str(m.group(4)) + ",0]")

            for prog in self.prog:
                if int(m.group(1)) in prog.pageid:
                    prog.do_button_press(int(m.group(1)), m.group(2), int(
                        m.group(3)), float(msg[2]), [int(m.group(4)), 0])

        elif msg[0].find('multitoggle') > -1:
            m = re.match('/(\d+)/(\w+?)(\d+)/(\d+)/(\d+)', msg[0])
            #self.log("page: " + str(m.group(1)) + "type: " + m.group(2) + " id:" + str(m.group(3)) + " val:" + str(msg[2]) + "[" + str(m.group(4)) + "," + str(m.group(5)) + "]")

            for prog in self.prog:
                if int(m.group(1)) in prog.pageid:
                    prog.do_button_press(int(m.group(1)), m.group(2), int(
                        m.group(3)), float(msg[2]), [int(m.group(5)), int(m.group(4))])
        else:
            m = re.match('/(\d+)/(\w+?)(\d+)', msg[0])
            #self.log("page: " + str(m.group(1)) + "type: " + m.group(2) + " id:" + str(m.group(3)) + " val:" + str(msg[2]))

            for prog in self.prog:
                if int(m.group(1)) in prog.pageid:
                    prog.do_button_press(int(m.group(1)), m.group(
                        2), int(m.group(3)), float(msg[2]))

# #####################################################################
# # Track / Scene Listeners

    def scene_change(self):
        id = self.tuple_idx(self.song().scenes,
                            self.song().view.selected_scene)
        self.sel_sc = id

        for prog in self.prog:
            prog.sel_scene_change()

    def track_change(self):
        id = self.tuple_idx(self.song().visible_tracks,
                            self.song().view.selected_track)

        if id != None:
            self.sel_tr = id
            for prog in self.prog:
                prog.sel_track_change()

# #####################################################################
# # Built In Ableton Methods
    def disconnect(self):
        self.prog[2].clear_nocturn()
        self.oscServer.sendOSC('/connected', 0)
        self.oscServer.shutdown()

        self.song().view.remove_selected_scene_listener(self.scene_change)
        self.song().view.remove_selected_track_listener(self.track_change)
        self.song().remove_visible_tracks_listener(self.refresh_state)

        for prog in self.prog:
            prog.rem_listeners()
            prog.destroy()

    def connect_script_instances(self, instanciated_scripts):
        try:
            import NocturnOSC_Monome.NocturnOSC
        except:
            pass

        for script in instanciated_scripts:
            self.log(str(script))
            try:
                if isinstance(script, NocturnOSC_Monome.NocturnOSC):
                    self.lc = script
            except:
                pass

    def is_extension(self):
        return False

    def request_rebuild_midi_map(self):
        self.c_instance.request_rebuild_midi_map()

    def build_midi_map(self, midi_map_handle):
        script_handle = self.c_instance.handle()
        self.prog[2].build_midi_map(script_handle, midi_map_handle)
        # for i in range(len(self.prog)):
        #     self.prog[i].do_refresh_state()

    def send_midi(self, midi_bytes):
        self.c_instance.send_midi(midi_bytes)

    def receive_midi(self, midi_bytes):
        # note on  note off
        if (((midi_bytes[0] & 240) == 144) or ((midi_bytes[0] & 240) == 128)):
            channel = (midi_bytes[0] & 15)
            note = midi_bytes[1]
            velocity = midi_bytes[2]
            # for c in self._components:
            # c.receive_note(channel, note, velocity)
            self.prog[2].receive_note(channel, note, velocity)
        elif ((midi_bytes[0] & 240) == 176):                        # CC
            channel = (midi_bytes[0] & 15)
            cc_no = midi_bytes[1]
            cc_value = midi_bytes[2]
            # for c in self._components:
            # c.receive_midi_cc(channel, cc_no, cc_value)
            self.prog[2].receive_midi_cc(channel, cc_no, cc_value)

    def can_lock_to_devices(self):
        return True

    def lock_to_device(self, device):
        for i in range(len(self.prog)):
            self.prog[i].lock(True)

    def unlock_from_device(self, device):
        for i in range(len(self.prog)):
            self.prog[i].lock(False)

    def set_appointed_device(self, device):
        track = self.song().view.selected_track

        tid = self.track_idx(track)
        did = self.tuple_idx(track.devices, device)

        if did != None and tid != None:
            self.log("appointed" + str(tid) + " " + str(did))

            for prog in self.prog:
                prog.sel_device_change(tid, did)

    def suggest_input_port(self):
        return 'Automap MIDI'

    def suggest_output_port(self):
        return 'Automap MIDI'

    def suggest_map_mode(self, cc_no, channel):
        return Live.MidiMap.MapMode.absolute

    def __handle_display_switch_ids(self, switch_id, value):
        pass

# #####################################################################
# Ableton Methods

    def refresh_state(self):
        if self.ipad != None:
            for i in range(len(self.prog)):
                self.prog[i].do_refresh_state()

            self.cur_sel()
            # self.oscServer.sendOSC('/1', 1)

    def update_display(self):
        if self.ipad != None:
            for prog in self.prog:
                if self.mode in prog.pageid:
                    prog.do_update()

            for i in range(len(self.prog)):
                self.prog[i].do_bg()

        if self.oscServer:
            try:
                self.oscServer.processIncomingUDP()
            except:
                pass

# #####################################################################
# Useful Methods
    def cur_sel(self):
        for prog in self.prog:
            if self.mode in prog.pageid:
                prog.update_selection()

    def log(self, msg):
        if self.LOGGING == 1:
            self.c_instance.log_message(msg)

    def song(self):
        return self.c_instance.song()

    def tuple_idx(self, tuple, obj):
        for i in xrange(0, len(tuple)):
            if (tuple[i] == obj):
                return i

    def tracks(self):
        tracks = tuple(self.song().visible_tracks) + \
            tuple(self.song().return_tracks) + (self.song().master_track,)
        return tracks

    def track_idx(self, track):
        return self.tuple_idx(self.tracks(), track)
