import platform
import getpass
import time
import os
import signal
from subprocess import Popen
import math
# matar socket fuser -k -n tcp 37
# matar proceso pkill omxplayer
# o killall omxplayer

VIDEO_FILE="video.mov"
im_raspi = False
paused = False


if platform.system() == "Linux":
	import dbus
	#	si estoy en las raspi hago todo lo que tenga que ver com omx
	im_raspi = True
	OMXPLAYER = 'omxplayer'
	OMXPLAYER_DBUS_ADDR='/tmp/omxplayerdbus.%s' % getpass.getuser()

class OMXController():

	im_ready = False

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
			        #self.dbusIfaceKey.Pause()
			        self.im_ready = True
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
			#self.rewind()

		else:
			print "* OMX: READY, ESPERANDO PLAY *"
	def rewind(self):
		print "* RECIBO REWIND *"
		if im_raspi:
			self.seek(0)
			time.sleep(.4)
			self.pause()
	def play(self):
		print "* RECIBO PLAY *"
		if im_raspi:
			self.dbusIfaceKey.Action(dbus.Int32("16"))
	def seek(self,seconds):
		if im_raspi:
			self.dbusIfaceKey.SetPosition(dbus.ObjectPath('/not/used'), Int64(seconds*1000*1000))
	def pause(self):
		print "* RECIBO PAUSE *"
		if im_raspi:
			self.dbusIfaceKey.Pause()
			#self.dbusIfaceKey.Action(dbus.Int32("16"))
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
