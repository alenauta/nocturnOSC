import sys
import time
import OSC

try:
    import socket
except:
    print "No Sockets"
    
class Logger:
    def __init__(self):
        self.socket = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
        sys.stderr = self
                

    def log(self,msg):
        self.send(msg)
        
    def send(self,msg):
        omsg = OSC.OSCMessage()
        omsg.setAddress('/log')
        omsg.append(msg)
            
        self.socket.sendto( omsg.getBinary(), ('127.0.0.1', 4444))
            
    def close(self):
        omsg = OSC.OSCMessage()
        omsg.setAddress('/log')
        omsg.append("Closing..")
            
        self.socket.sendto( omsg.getBinary(), ('127.0.0.1', 4444))
            
    def write(self, msg):
        self.send("STDERR: " + msg)
