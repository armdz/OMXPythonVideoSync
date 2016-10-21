import platform
import getpass
import time
import os
import signal
from subprocess import Popen

# matar socket fuser -k -n tcp 37
# matar proceso pkill omxplayer
# o killall omxplayer

VIDEO_FILE="video.mp4"
im_raspi = False
paused = False

if platform.system() == "Linux":
	import dbus
	#	si estoy en las raspi hago todo lo que tenga que ver com omx
	im_raspi = True
	OMXPLAYER = 'omxplayer'
	OMXPLAYER_DBUS_ADDR='/tmp/omxplayerdbus.%s' % getpass.getuser()

class OMXController():

	def __init__(self):
		if im_raspi:
			print "* OMX INITED *"	
		else:
			print "* OMX: NO ESTOY CORRIENDO EN RASPI , SOLO TIRO PRINT :O *"
	def ready(self):
		if im_raspi:
			cmd = "omxplayer --no-osd %s" %(VIDEO_FILE)
			Popen([cmd], shell=True)
			done,retry=0,0
			while done==0:
			    try:
			    	self.bus = dbus.bus.BusConnection(open(OMXPLAYER_DBUS_ADDR).readlines()[0].rstrip())
			        object = self.bus.get_object('org.mpris.MediaPlayer2.omxplayer','/org/mpris/MediaPlayer2', introspect=False)
			        self.dbusIfaceProp = dbus.Interface(object,'org.freedesktop.DBus.Properties')
			        self.dbusIfaceKey = dbus.Interface(object,'org.mpris.MediaPlayer2.Player')
			        print "* OMX CACHEADO *"
			        done=1
			    except:
			    	print "ERROR"
			        retry+=1
			        time.sleep(1)
			        if retry >= 50:
			            print "* ERRROR CACHEANDO OMX *"
			            raise SystemExit
			#incio el video en 0 y con pausa y espero play
			self.rewind()
		else:
			print "* OMX: READY, ESPERANDO PLAY *"
	def rewind(self):
		self.seek(0)
		time.sleep(.5)
		self.pause()
	def play(self):
		print "* RECIBO PLAY *"
		self.dbusIfaceKey.Action(dbus.Int32("16"))
	def seek(self,seconds):
		self.dbusIfaceKey.SetPosition(dbus.ObjectPath('/not/used'), long(seconds*1000000))
	def pause(self):
		self.dbusIfaceKey.Action(dbus.Int32("16"))
	def kill(self):
		if im_raspi:
			try:
				os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
			except:
				pass
			try:
				self.process.wait()
			except:
				pass
		else:
			print "* CHAU * "
