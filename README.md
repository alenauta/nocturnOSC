# nocturnOSC
Ableton Live MIDI Remote scripts for interaction between Novation Nocturn and TouchOSC

This set of script is heavily based on LiveControl by ST8 <st8@q3f.org>
My contribution was to add the MIDI funcionality to control the underrated Novation Nocturn and fix some bugs.

# Instructions

<ul>
<li>Load the included Automap template (Inst-ch2.automap) in the inst section, channel 2 of Automap software. If you want to change the channel you'll have to change also the DEV_CH constant in the nocturnConst.py file (remember to start to count from 0, i.e. DEV_CH = 0 means MIDI channel 1)</li>
<li>Move the nocturnOSC folder into your MIDI Remote Script folder</li>
<li>Edit the nocturnOSC.conf file included in the same folder according to your network configuration</li>
<li>Change the network settings on TouchOSC app accordingly</li>
<li>In Ableton Live select nocturnOSC as control surface with Automap MIDI as Input and Output</li>
</ul>
