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

from Program import Program
from nocturnConst import *
import Live
import os
import pickle


class DeviceControl(Program):
    name = "Device Control"
    pageid = [3, 5, 7, 8]

    def __init__(self, parent, width, height):
        self.width = 8
        self.height = height

        self.parent = parent
        self.c_instance = parent.c_instance
        self.oscServer = parent.oscServer

        self.listen = {}
        self.dlisten = {}
        self.plisten = {}

        self.bank = 0

        self._num_banks = 0

        self.xy_pads = [{'tid': 0, 'did': 0, 'device': None, 'locked': False,
                         'x_off': 0, 'y_off': 0, 'params': {}} for i in range(4)]
        self.xy_sel = 0

        self.update = 0
        self.skip = 0

        # self.do_refresh_state()

    def set_wh(self, w, h):
        self.width = 8
        self.height = h

    def update_leds(self):
        msgs = []
        for i in range(4):
            msgs.append(['/5/lock' + str(i + 1),
                         int(self.xy_pads[i]['locked'])])

            if self.xy_sel == i:
                msgs.append(['/5/sel' + str(i + 1), 1])
            else:
                msgs.append(['/5/sel' + str(i + 1), 0])

        self.oscServer.sendBundle(msgs)

    def update_selection(self):
        self.log('UPDATE_SELECTION')
        # pass

    def rem_listeners(self):
        for pr in self.listen:
            if pr != None:
                ocb = self.listen[pr]
                if pr.value_has_listener(ocb) == 1:
                    pr.remove_value_listener(ocb)

        self.listen = {}

        for tr in self.dlisten:
            if tr != None:
                ocb = self.dlisten[tr]
                if tr.view.selected_device_has_listener(ocb) == 1:
                    tr.view.remove_selected_device_listener(ocb)

        self.dlisten = {}

        for de in self.plisten:
            if de != None:
                ocb = self.plisten[de]
                if de.parameters_has_listener(ocb) == 1:
                    de.remove_parameters_listener(ocb)

        self.plisten = {}

        if self.song().view.selected_track_has_listener(self.track_change) == 1:
            self.song().view.remove_selected_track_listener(self.track_change)

        self.log("*Removed Parameter Listeners*")

    def add_devpmlistener(self, device):
        def cb(): return self.devpm_change()

        if self.plisten.has_key(device) != 1:
            device.add_parameters_listener(cb)
            self.plisten[device] = cb

    def devpm_change(self):
        self.do_refresh_state()

    def add_paramlistener(self, param, tid, did, pid):
        def cb(): return self.param_changestate(param, tid, did, pid)

        if self.listen.has_key(param) != 1:
            param.add_value_listener(cb)
            self.listen[param] = cb

    def param_changestate(self, param, tid, did, pid):
        if pid == 0:
            if self.device[0] == tid and self.device[1] == did:
                self.log("toggle on off")
                self.oscServer.sendOSC('/3/toggle0', int(param.value))

        else:
            msgs = []

            tr = self.tuple_idx(self.tracks(), self.song().view.selected_track)
            dev = self.tuple_idx(self.song().view.selected_track.devices, self.song(
            ).view.selected_track.view.selected_device)

            if tr == tid and dev == did:
                if pid < 5:
                    if self.skip == 0:
                        for j in range(7, 9):
                            msgs.append(['/' + str(j) + '/rotary' + str(pid),
                                         (param.value - param.min) / (param.max - param.min)])
                    else:
                        if self.skip == 7:
                            msgs.append(
                                ['/8/rotary' + str(pid), (param.value - param.min) / (param.max - param.min)])
                        elif self.skip == 8:
                            msgs.append(
                                ['/7/rotary' + str(pid), (param.value - param.min) / (param.max - param.min)])

            id = pid - (self.bank * 8)
            msgs.append(
                ['/3/val' + str(id), self.to_ascii(unicode(param)).strip()])
            self.log('param ' + str(param))

            if self.skip == 0:
                if self.device[0] == tid and self.device[1] == did:
                    self.log('update now!')
                    if id > 0:
                        msgs.append(
                            ['/3/rotary' + str(id), (param.value - param.min) / (param.max - param.min)])
                        msgs.append(
                            ['/3/label' + str(id), str(self.trunc_string(param.name, 15)).strip()])

                for i in range(4):
                    d = self.xy_pads[i]
                    if tid == d['tid'] and did == d['did']:
                        x = self.xy(0, i)
                        y = self.xy(1, i)

                        if x == pid or y == pid:
                            self.update_xy(i)

            else:
                self.update = 3

            self.oscServer.sendBundle(msgs)

        self.log("Parameter: " + str(tid) + " " + str(did) + " " + str(pid) + " changed: " +
                 str(param.value) + " min:" + str(param.min) + " max:" + str(param.max))

    def add_devicelistener(self, track, tid):
        def cb(): return self.device_changestate(track, tid)

        if self.dlisten.has_key(track) != 1:
            track.view.add_selected_device_listener(cb)
            self.dlisten[track] = cb

    def device_changestate(self, track, tid):
        self.log('DEVICE_CHANGESTATE')
        self.cur_dev()

        if self.locked == False:
            did = self.tuple_idx(track.devices, track.view.selected_device)
            self.device = [tid, did]

            self.update_params()

            self.log("Selected Device Change: " + str(tid) + " " + str(did))

        for i in range(4):
            did = self.tuple_idx(track.devices, track.view.selected_device)

            if not self.xy_pads[i]['locked']:
                self.xy_pads[i]['tid'] = tid
                self.xy_pads[i]['did'] = did
                self.xy_pads[i]['device'] = track.view.selected_device

        self.update_labels()

    def track_change(self):
        self.log('TRACK_CHANGE')
        self.cur_dev()

        track = self.song().view.selected_track
        tid = self.track_idx(track)

        if self.locked == False:
            self.device[0] = tid
            self.device[1] = 0

            if len(track.devices) > 0:
                self.song().view.select_device(track.devices[0])

            self.update_params()

        self.refresh_devices()

        for i in range(4):
            if not self.xy_pads[i]['locked']:
                self.xy_pads[i]['tid'] = tid
                self.xy_pads[i]['did'] = 0

                if len(track.devices) > 0:
                    self.xy_pads[i]['device'] = track.devices[0]
                else:
                    self.xy_pads[i]['device'] = None

        self.update_labels()

    def refresh_devices(self):
        self.log('REFRESH DEVICES')
        msgs = []
        devs = self.tracks()[self.device[0]].devices
        for i in range(5):
            if i < len(devs):
                msgs.append(['/3/dlabel' + str(i + 1),
                             self.trunc_string(devs[i].name, 12).strip()])
            else:
                msgs.append(['/3/dlabel' + str(i + 1), ''])

        self.oscServer.sendBundle(msgs)

    def cur_dev(self):
        tr = self.song().view.selected_track
        dev = tr.view.selected_device

        if dev != None:
            msgs = []

            for j in range(7, 9):
                msgs.append(['/' + str(j) + '/dlabel',
                             self.trunc_string(dev.name, 20).strip()])

                for i in range(1, 5):
                    if i < len(dev.parameters):
                        msgs.append(['/' + str(j) + '/plabel' + str(i),
                                     self.trunc_string(dev.parameters[i].name, 10).strip()])
                        msgs.append(['/' + str(j) + '/rotary' + str(i), (dev.parameters[i].value -
                                                                         dev.parameters[i].min) / (dev.parameters[i].max - dev.parameters[i].min)])
                    else:
                        msgs.append(['/' + str(j) + '/plabel' + str(i), ''])
                        msgs.append(['/' + str(j) + '/rotary' + str(i), 0])

        else:
            msgs = []

            for j in range(7, 9):
                msgs.append(['/' + str(j) + '/dlabel', ''])

                for i in range(1, 5):
                    msgs.append(['/' + str(j) + '/plabel' + str(i), ''])
                    msgs.append(['/' + str(j) + '/rotary' + str(i), 0])

        self.oscServer.sendBundle(msgs)

    def update_params(self):
        self.log('UPDATE PARAMS')
        msgs = []

        if self.device[1] < len(self.tracks()[self.device[0]].devices):
            device = self.tracks()[self.device[0]].devices[self.device[1]]
            self.log('update params of device ' + self.to_ascii(device.name))

            msgs.append(['/3/label0', self.to_ascii(self.tracks()[self.device[0]].name) +
                         ": " + self.to_ascii(device.name) + " - Bank: " + str(self.bank + 1)])
            msgs.append(['/3/toggle0', device.parameters[0].value])

            for i in range(self.width):
                id = i + 1 + (self.bank * self.width)

                if id < len(device.parameters):
                    p = device.parameters[id]
                    msgs.append(['/3/label' + str(i + 1),
                                 str(self.trunc_string(p.name, 15)).strip()])
                    msgs.append(['/3/rotary' + str(i + 1),
                                 (p.value - p.min) / (p.max - p.min)])
                    msgs.append(['/3/val' + str(i + 1), str(p)])
                else:
                    msgs.append(['/3/label' + str(i + 1), " "])
                    msgs.append(['/3/rotary' + str(i + 1), 0])
                    msgs.append(['/3/val' + str(i + 1), " "])

        else:
            msgs.append(['/3/label0', self.to_ascii(self.tracks()
                                                    [self.device[0]].name) + ": No Device Selected"])
            msgs.append(['/3/toggle0', 0])

            for i in range(self.width):
                msgs.append(['/3/label' + str(i + 1), " "])
                msgs.append(['/3/rotary' + str(i + 1), 0])
                msgs.append(['/3/val' + str(i + 1), " "])

        self.parent.request_rebuild_midi_map()
        self.oscServer.sendBundle(msgs)
        self.update_labels()

    def do_button_press(self, page, type, id, val, xy=[]):
        if page == 3:
            if type == 'toggle':
                if id == 0:
                    self.log("button toggle")
                    self.tracks()[self.device[0]].devices[self.device[1]
                                                          ].parameters[0].value = val
                else:
                    if val == 1:
                        params = self.tracks()[
                            self.device[0]].devices[self.device[1]].parameters
                        pid = id + (self.bank * 8)

                        if id < len(params):
                            self.skip = 0
                            p = params[pid]

                            if p.value == p.max:
                                p.value = p.min
                            else:
                                p.value = p.max

            elif type == 'push':
                if val == 1:
                    if id == 1:
                        if self.locked:
                            self.locked = False
                            self.track_change()
                            self.oscServer.sendOSC('/3/lock', 'Lock')
                            self.parent.send_midi((NOTE_OFF_STATUS + 1, DEV_NAV_NO + 1, 0))

                        else:
                            self.locked = True
                            self.oscServer.sendOSC('/3/lock', 'Unlock')
                            self.parent.send_midi((NOTE_ON_STATUS + 1, DEV_NAV_NO + 1, 127))

                        self.log(str(self.locked))

                    else:
                        d = id - 2
                        tr = self.tracks()[self.device[0]]

                        self.log(str(d))
                        if d < len(tr.devices):
                            self.song().view.select_device(tr.devices[d])

            elif type == 'rotary':
                params = self.tracks()[self.device[0]
                                       ].devices[self.device[1]].parameters
                pid = id + (self.bank * 8)

                if id < len(params):
                    self.skip = 1
                    p = params[pid]

                    newval = (val * (p.max - p.min)) + p.min
                    p.value = newval

            elif type == '2nav':
                if val == 1:
                    tr = id + self.track - 1
                    if tr < len(self.song().visible_tracks):
                        self.song().view.selected_track = self.song(
                        ).visible_tracks[tr]

            elif type == 'nav':
                if val == 1:
                    # Track Right
                    if id == 2:
                        self.sel_track_right()

                    # Track Left
                    elif id == 1:
                        self.sel_track_left()

                    # Device Right
                    elif id == 4:
                        self.device_right()

                    # Device Left
                    elif id == 3:
                        self.device_left()

                    # Bank Up
                    elif id == 6:
                        self.bank = self.bank + 1
                        self.update_params()

                    # Bank Down
                    elif id == 5:
                        if self.bank > 0:
                            self.bank = self.bank - 1
                            self.update_params()

        elif page == 5:
            if type == 'push':
                self.log("HI: " + str(id))
                if val == 1:
                    if id < 6:
                        pid = id + (self.xy_pads[self.xy_sel]['x_off'] * 5)
                        self.xy(0, self.xy_sel, pid)
                        self.update_labels()

                    elif id < 11:
                        pid = id + (self.xy_pads[self.xy_sel]['y_off'] * 5) - 5
                        self.xy(1, self.xy_sel, pid)
                        self.update_labels()

                    elif id < 15:
                        self.xy_sel = id - 11
                        self.log(str(self.xy_sel))
                        self.update_leds()
                        self.update_labels()

                    else:
                        xy = id - 15
                        if self.xy_pads[xy]['locked']:
                            self.xy_pads[xy]['locked'] = False
                        else:
                            self.xy_pads[xy]['locked'] = True

                        self.update_leds()
                        self.log(str(self.xy_pads))

            elif type == '2nav':
                if val == 1:
                    if id == 2:
                        self.xy_pads[self.xy_sel]['x_off'] += 1

                    elif id == 1:
                        if self.xy_pads[self.xy_sel]['x_off'] > 0:
                            self.xy_pads[self.xy_sel]['x_off'] -= 1

                    elif id == 4:
                        self.xy_pads[self.xy_sel]['y_off'] += 1

                    elif id == 3:
                        if self.xy_pads[self.xy_sel]['y_off'] > 0:
                            self.xy_pads[self.xy_sel]['y_off'] -= 1

                    self.update_labels()

            elif type == 'nav':
                if val == 1:
                    if id == 1:
                        self.sel_track_left()
                    elif id == 2:
                        self.sel_track_right()
                    elif id == 3:
                        self.device_left()
                    elif id == 4:
                        self.device_right()
                    elif id == 5:
                        file = os.path.expanduser(
                            '~') + '/livecontrol_to_xy.pkl'
                        if os.path.exists(file) and os.path.isfile(file):
                            pkl = open(file, 'rb')
                            self.xy_pads = pickle.load(pkl)
                            pkl.close()

                            self.update = 6
                            self.update_labels()
                            self.oscServer.sendOSC(
                                '/5/title1', 'Config Loaded...')

                    elif id == 6:
                        file = os.path.expanduser(
                            '~') + '/livecontrol_to_xy.pkl'
                        pkl = open(file, 'wb')
                        pickle.dump(self.xy_pads, pkl)
                        pkl.close()

                        self.oscServer.sendOSC('/5/title1', 'Config Saved...')
                        self.update = 6

            elif type == 'xy':
                xyi = id - 1
                x = self.xy(0, xyi)
                y = self.xy(1, xyi)

                if x != None and y != None:
                    self.skip = 1
                    px = self.xy_pads[xyi]['device'].parameters[x]
                    py = self.xy_pads[xyi]['device'].parameters[y]

                    px.value = (xy[1] * (px.max - px.min)) + px.min
                    py.value = (xy[0] * (py.max - py.min)) + py.min

        elif page == 7 or page == 8:
            if type == 'rotary':
                tr = self.song().view.selected_track
                dev = tr.view.selected_device

                if dev != None:
                    self.skip = page
                    p = dev.parameters[id]
                    p.value = (val * (p.max - p.min)) + p.min

    def device_left(self):
        self.log('dev left')
        track = self.song().view.selected_track
        did = self.tuple_idx(track.devices, track.view.selected_device)

        if did > 0:
            self.song().view.select_device(track.devices[did - 1])

    def device_right(self):
        self.log('dev right')
        track = self.song().view.selected_track
        did = self.tuple_idx(track.devices, track.view.selected_device)

        if len(track.devices) > did + 1:
            self.song().view.select_device(track.devices[did + 1])

    def xy(self, xy, xyi, pid=None):
        if pid == None:
            if self.xy_pads[xyi]['params'].has_key(self.xy_pads[xyi]['tid']):
                if self.xy_pads[xyi]['params'][self.xy_pads[xyi]['tid']].has_key(self.xy_pads[xyi]['did']):
                    return self.xy_pads[xyi]['params'][self.xy_pads[xyi]['tid']][self.xy_pads[xyi]['did']][xy]

        else:
            if self.xy_pads[xyi]['device'] != None:
                p = self.xy_pads[xyi]['device'].parameters

                if pid < len(p):
                    arr = [1, 1]
                    arr[xy] = pid

                    if self.xy_pads[xyi]['params'].has_key(self.xy_pads[xyi]['tid']):
                        if self.xy_pads[xyi]['params'][self.xy_pads[xyi]['tid']].has_key(self.xy_pads[xyi]['did']):
                            self.xy_pads[xyi]['params'][self.xy_pads[xyi]
                                                        ['tid']][self.xy_pads[xyi]['did']][xy] = pid
                        else:
                            self.xy_pads[xyi]['params'][self.xy_pads[xyi]
                                                        ['tid']][self.xy_pads[xyi]['did']] = arr
                    else:
                        self.xy_pads[xyi]['params'][self.xy_pads[xyi]['tid']] = {
                            self.xy_pads[xyi]['did']: arr}

    def update_labels(self):
        msgs = []

        device = self.xy_pads[self.xy_sel]['device']
        if device != None:
            for i in range(5):
                x = i + (self.xy_pads[self.xy_sel]['x_off'] * 5) + 1
                y = i + (self.xy_pads[self.xy_sel]['y_off'] * 5) + 1

                if x < len(device.parameters):
                    msgs.append(
                        ['/5/label' + str(i + 1), self.trunc_string(device.parameters[x].name, 12).strip()])
                else:
                    msgs.append(['/5/label' + str(i + 1), " "])

                if y < len(device.parameters):
                    msgs.append(
                        ['/5/label' + str(i + 6), self.trunc_string(device.parameters[y].name, 12).strip()])
                else:
                    msgs.append(['/5/label' + str(i + 6), " "])
        else:
            for i in range(5):
                msgs.append(['/5/label' + str(i + 1), " "])
                msgs.append(['/5/label' + str(i + 6), " "])

        for i in range(4):
            device = self.xy_pads[i]['device']
            trname = self.tracks()[self.xy_pads[i]['tid']].name

            if device != None:
                msgs.append(
                    ['/5/title' + str(i + 1), self.to_ascii(trname) + ": " + self.to_ascii(device.name)])

                x = self.xy(0, i)
                y = self.xy(1, i)

                if x:
                    msgs.append(['/5/paramx' + str(i + 1),
                                 self.to_ascii(device.parameters[x].name)])
                    msgs.append(['/5/paramy' + str(i + 1),
                                 self.to_ascii(device.parameters[y].name)])

                else:
                    msgs.append(['/5/paramx' + str(i + 1), " "])
                    msgs.append(['/5/paramy' + str(i + 1), " "])

            else:
                msgs.append(['/5/paramx' + str(i + 1), " "])
                msgs.append(['/5/paramy' + str(i + 1), " "])

                msgs.append(['/5/title' + str(i + 1),
                             str(trname) + ": No Device Selected"])

            self.update_xy(i)

        self.oscServer.sendBundle(msgs)

    def update_xy(self, id):
        msgs = []
        x = self.xy(0, id)
        y = self.xy(1, id)

        if x != None and y != None:
            device = self.xy_pads[id]['device']

            xp = device.parameters[x]
            xval = (xp.value - xp.min) / (xp.max - xp.min)

            yp = device.parameters[y]
            yval = (yp.value - yp.min) / (yp.max - yp.min)

            self.oscServer.sendOSC('/5/xy' + str(id + 1), (yval, xval))

        else:
            self.oscServer.sendOSC('/5/xy' + str(id + 1), (0, 0))

    def do_refresh_state(self):
        self.log('DO_REFRESH_STATE')
        self.limits()
        self.rem_listeners()

        track = self.song().view.selected_track
        tid = self.track_idx(track)
        did = self.tuple_idx(track.devices, track.view.selected_device)

        self.device = [tid, did]

        if self.song().view.selected_track_has_listener(self.track_change) != 1:
            self.song().view.add_selected_track_listener(self.track_change)

        tracks = self.tracks()
        for i in range(len(tracks)):
            self.add_devicelistener(tracks[i], i)

            if len(tracks[i].devices) >= 1:
                for j in range(len(tracks[i].devices)):
                    self.add_devpmlistener(tracks[i].devices[j])

                    if len(tracks[i].devices[j].parameters) >= 1:
                        for k in range(len(tracks[i].devices[j].parameters)):
                            self.add_paramlistener(
                                tracks[i].devices[j].parameters[k], i, j, k)

        self.update_labels()
        self.update_leds()
        self.track_change()

    def receive_note(self, channel, note, velocity):
        self.log('channel ' + str(channel) + ' note ' +
                 str(note) + ' velocity ' + str(velocity))
        if (channel == DEV_CH) and (note == DEV_NAV_NO + 1) and (velocity == 127):
            if self.locked:
                self.locked = False
                self.oscServer.sendOSC('/3/lock', 'Lock')
                self.parent.send_midi((NOTE_OFF_STATUS + channel, DEV_NAV_NO + note, 0))
                self.track_change()
            else:
                self.locked = True
                self.oscServer.sendOSC('/3/lock', 'Unlock')
                self.parent.send_midi((NOTE_ON_STATUS + channel, DEV_NAV_NO + note, 127))
        elif (channel == DEV_CH) and (note == DEV_NAV_NO + 2) and (velocity == 127):
            self.sel_track_left()
        elif (channel == DEV_CH) and (note == DEV_NAV_NO + 3) and (velocity == 127):
            self.sel_track_right()
        elif (channel == DEV_CH) and (note == DEV_NAV_NO + 4) and (velocity == 127):
            self.device_left()
        elif (channel == DEV_CH) and (note == DEV_NAV_NO + 5) and (velocity == 127):
            self.device_right()
        elif (channel == DEV_CH) and (note == DEV_NAV_NO + 6) and (velocity == 127):
            if self.bank > 0:
                self.bank = self.bank - 1
                self.update_params()
        elif (channel == DEV_CH) and (note == DEV_NAV_NO + 7) and (velocity == 127):
            self.bank = self.bank + 1
            self.update_params()

        # TIENI SPENTI I PULSANTI NON MAPPATI
        # self.parent.send_midi(
        #     (NOTE_OFF_STATUS + channel, DEV_BASE_NO + note, 0))

    def receive_midi_cc(self, channel, cc_no, cc_value):
        self.log('channel ' + str(channel) + ' cc ' +
                 str(cc_no) + ' value ' + str(cc_value))

    def do_bg(self):
        if self.update > 0:
            self.update -= 1

        if self.update == 1:
            self.update_labels()
            self.skip = 0

    def do_update(self):
        pass

    def build_midi_map(self, script_handle, midi_map_handle):
        self.clear_nocturn()
        tr = self.song().view.selected_track
        dev = tr.view.selected_device
        if (dev):
            self.log("BUILD MIDI MAP for " + self.to_ascii(dev.name))
            self.map_note_parameter(            # mapping on-off button
                midi_map_handle, dev.parameters[0], DEV_NAV_NO, 0)
            Live.MidiMap.forward_midi_note(
                script_handle, midi_map_handle, DEV_CH, DEV_NAV_NO + 0)
            for index in range(NUM_STRIPS):
                if (index + self.bank * NUM_STRIPS + 1 < len(dev.parameters)):
                    parameter = 0
                    parameter = dev.parameters[index +
                                               self.bank * NUM_STRIPS + 1]
                    self.map_cc_parameter(midi_map_handle, parameter, index)
                    Live.MidiMap.forward_midi_cc(
                        script_handle, midi_map_handle, DEV_CH, DEV_BASE_CC + index)
                    self.log('parameter name: ' + str(parameter))
                    if str(parameter).lower().strip() == 'on':
                        self.map_note_parameter(
                            midi_map_handle, parameter, DEV_BASE_NO, index)
                        Live.MidiMap.forward_midi_note(
                            script_handle, midi_map_handle, DEV_CH, DEV_BASE_NO + index)   # button on
                        self.parent.send_midi(
                            (NOTE_ON_STATUS + DEV_CH, DEV_BASE_NO + index, 127))
                    elif str(parameter).lower().strip() == 'off':
                        self.map_note_parameter(
                            midi_map_handle, parameter, DEV_BASE_NO, index)
                        Live.MidiMap.forward_midi_note(
                            script_handle, midi_map_handle, DEV_CH, DEV_BASE_NO + index)   # button off
                        self.parent.send_midi(
                            (NOTE_OFF_STATUS + DEV_CH, DEV_BASE_NO + index, 0))
                    else:
                        Live.MidiMap.forward_midi_note(
                            script_handle, midi_map_handle, DEV_CH, DEV_BASE_NO + index)   # not a button
                        self.parent.send_midi(
                            (NOTE_OFF_STATUS + DEV_CH, DEV_BASE_NO + index, 0))
                else:
                    Live.MidiMap.forward_midi_cc(
                        script_handle, midi_map_handle, DEV_CH, DEV_BASE_CC + index)
        for index in range(1, NUM_STRIPS):         # NAV buttons
            Live.MidiMap.forward_midi_note(
                script_handle, midi_map_handle, DEV_CH, DEV_NAV_NO + index)
        for index in range(2, NUM_STRIPS):
            self.parent.send_midi(
                (NOTE_ON_STATUS + DEV_CH, DEV_NAV_NO + index, 127))

    def map_cc_parameter(self, midi_map_handle, parameter, index):
        map_mode = Live.MidiMap.MapMode.absolute
        cc_feedback_rule = Live.MidiMap.CCFeedbackRule()
        cc_feedback_rule.delay_in_ms = 0
        cc_feedback_rule.cc_value_map = tuple()
        cc_feedback_rule.channel = DEV_CH
        cc_feedback_rule.cc_no = DEV_BASE_CC + index
        Live.MidiMap.map_midi_cc_with_feedback_map(
            midi_map_handle,
            parameter,
            cc_feedback_rule.channel,
            cc_feedback_rule.cc_no,
            Live.MidiMap.MapMode.absolute,
            cc_feedback_rule,
            False)
        Live.MidiMap.send_feedback_for_parameter(midi_map_handle, parameter)

    def map_note_parameter(self, midi_map_handle, parameter, dev_base, index):
        note_feedback_rule = Live.MidiMap.NoteFeedbackRule()
        note_feedback_rule.delay_in_ms = 0
        note_feedback_rule.vel_map = tuple()
        note_feedback_rule.channel = DEV_CH
        note_feedback_rule.note_no = dev_base + index
        Live.MidiMap.map_midi_note_with_feedback_map(
            midi_map_handle,
            parameter,
            note_feedback_rule.channel,
            note_feedback_rule.note_no,
            note_feedback_rule)
        Live.MidiMap.send_feedback_for_parameter(midi_map_handle, parameter)

    def clear_nocturn(self):
        for index in range(NUM_STRIPS):
            self.parent.send_midi((CC_STATUS + DEV_CH, DEV_BASE_CC + index, 0))
            self.parent.send_midi(
                (NOTE_OFF_STATUS + DEV_CH, DEV_BASE_NO + index, 0))
            self.parent.send_midi(
                (NOTE_OFF_STATUS + DEV_CH, DEV_NAV_NO + index, 0))
