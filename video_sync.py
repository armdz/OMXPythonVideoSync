#!/usr/bin/env python2.7
#http://pythonhackers.com/p/popcornmix/omxplayer
import thread
import threading
import time
import sys,platform
import socket
import atexit
import Queue
import sys
import os
import errno
import math
import time
from threading import Thread
from socket import error as socket_error
from subprocess import Popen
from omx_controller import OMXController

if platform.system() == "Linux":
	import RPi.GPIO as GPIO


# constantes
MODE_INIT = -1
MASTER_MODE_WAITING_CLIENTS = 0
SLAVE_SAY_HELLO = 1
MODE_READY = 3
SLAVE_INPUT_PORT = 12000
MASTER_INPUT_PORT = 13000
MSG_HELLO_TIMER = 2	#cada cuando mando el mensaje
DELAY_INIT_TO_RW = 2
# botones
BUTTON_SHUTDOWN = 12
BUTTON_PLAY_PAUSE = 16
BUTTON_REWIND = 18
ARRAY_BUTTON_SHUTDOWN = 0
ARRAY_BUTTON_PLAY = 1
ARRAY_BUTTON_REWIND = 2
SENSOR_ID = 11
val_rew = False
val_shutdown = False
val_play_pause = False
gpio_buttons = []
gpio_buttons_val = []

im_raspi = False
master = False
udp_port = 0
mode = MODE_INIT
total_clients = 1
connected_clients = 0
master_ip = ""
client_list = []
ip_list = []
im_connected = False
rewinded = False
shared_q = Queue.Queue()
playing = False
paused_by_button = False
video_file_path = ""
master_ready_to_operate = False
#
shut_down_timer = False
shut_down_tick = 0

class VideoSync():
	def __init__(self):
		self.master = False
		self.video_file_path = ""
		arg_len = len(sys.argv)
		if arg_len < 3:
			print "* Como ejecutar el script ?"
			print "* Para SLAVE los argumentos: ",sys.argv[0],"master NUMERO_CLIENTES_A_ESPERAR"
			print "* Para SLAVE los argumentos: ",sys.argv[0],"slave IP_MASTER"
			exit()
		if  str(sys.argv[1]) == "master":
			self.master = True
			self.connected_clients = 0
			self.total_clients = int(sys.argv[2])
			self.tcp_port = MASTER_INPUT_PORT
			self.client_list = []
			self.ip_list = []
			self.sock = self.init_socket()
			self.master_ready_to_operate = False
		else:
			#slave
			self.master_ip = str(sys.argv[2])	
			self.tcp_port = MASTER_INPUT_PORT
			self.im_connected = False


		self.video_file_path = os.path.abspath(sys.argv[0]).replace("video_sync.py",str(sys.argv[3]))

		self.paused_by_button = False
		self.playing = False
		self.rewinded = False
		self.ping_tick = time.clock()
		self.connected_clients = 0

		self.shut_down_timer = False
		self.shut_down_tick = 0

	def run(self):
		print 	"**************************************"
		print	"VideoSync * PLAN *"
		if self.master:
			print	"Esperando a",total_clients, "cliente/s"
		else:
			print	"Slave"
		print 	"**************************************"
		self.omx_controller = OMXController()
		
		if self.master:
			time.sleep(DELAY_INIT_TO_RW)
			#self.omx_controller.rewind()
			self.mode = MASTER_MODE_WAITING_CLIENTS
			self.as_master()
		else:
			self.omx_controller.ready(self.video_file_path)
			self.mode = SLAVE_SAY_HELLO
			self.as_slave()

	def as_slave(self):
		print "* RUTINA DE CONEXION *"
		while True:
			if self.im_connected:
				if self.rewinded:
					try:
						data,addr = self.sock.recvfrom(1024)
						if not data:
							pass
						else:
							print "RECIBO DATA",data
							if data == "play":
								self.omx_controller.play()
							elif data == "pause":
								self.omx_controller.pause()
							elif data == "rewind":
								self.omx_controller.rewind()
							elif data == "shutdown":
								os.system("sudo shutdown -h now")
					except socket.error, e:
						pass
					time_dif = math.floor(math.fabs(self.ping_tick-time.clock()))
					if(time_dif > 5):
						self.ping_tick = time.clock()
						try:
							self.sock.send("estoy")
						except:
							print "* INTENTO AUTOCONECTAR *"
							self.sock.close()
							self.im_connected = False
			elif self.omx_controller.im_ready:
				if not self.rewinded:
					time.sleep(DELAY_INIT_TO_RW)
					self.omx_controller.rewind()
					self.rewinded = True
				else:
					self.sock = self.init_socket()

	def add_input(self,input_queue):
		while True:
			input_queue.put(sys.stdin.read(1))
			pass

	def as_master(self):
		self.im_raspi = False
		if platform.system() == "Linux":
			self.im_raspi = True
			GPIO.setwarnings(False)
			GPIO.setmode(GPIO.BOARD)
			GPIO.setup(BUTTON_SHUTDOWN, GPIO.IN, pull_up_down = GPIO.PUD_UP)
			GPIO.setup(BUTTON_PLAY_PAUSE, GPIO.IN, pull_up_down = GPIO.PUD_UP) 
			GPIO.setup(BUTTON_REWIND, GPIO.IN, pull_up_down = GPIO.PUD_UP) 
			GPIO.setup(SENSOR_ID, GPIO.IN)

		self.gpio_buttons = []
		self.gpio_buttons_val = []
		#	este orden es fundamental
		self.gpio_buttons.append(BUTTON_SHUTDOWN)
		self.gpio_buttons.append(BUTTON_PLAY_PAUSE)
		self.gpio_buttons.append(BUTTON_REWIND)
		for b in self.gpio_buttons:
			self.gpio_buttons_val.append(1)

		self.val_rew = False
		self.val_shutdown = False
		self.val_play_pause = False

		self.master_ready_to_operate = True
		time.sleep(2)
		self.omx_controller.ready(self.video_file_path)
		self.omx_controller.pause()

		#BORRRAR ESTO



		#self.shared_q = Queue.Queue()
		#input_thread = threading.Thread(target=self.add_input, args=(self.shared_q,))
		#input_thread.daemon = True
		#input_thread.start()
		last_update = time.time()
		while True:
			#botones
			if self.im_raspi and self.master_ready_to_operate:



				#print self.omx_controller.get_dif()
				if self.omx_controller.get_dif() <= 0.5:
					self.send_rewind()
				button_pressed = -1
				for i,val in enumerate(self.gpio_buttons):
					if button_pressed == -1:
						button_val = GPIO.input(val)
						if i == ARRAY_BUTTON_SHUTDOWN:
							if button_val == 0:
								button_pressed = i
								self.gpio_buttons_val[i] = button_val
						else:
							if button_val != self.gpio_buttons_val[i]:
								if button_val == 0:
									button_pressed = i
								self.gpio_buttons_val[i] = button_val
				if button_pressed != -1:
					if button_pressed == ARRAY_BUTTON_SHUTDOWN:
						#shut
						if not self.shut_down_timer:
							self.shut_down_timer = True
							self.shut_down_tick = time.clock()
						else:
							time_dif = math.fabs(self.shut_down_tick-time.clock())
							#print math.fabs(self.shut_down_tick-time.clock())
							if(time_dif > .04):
								print "TIEMPO SHUTDOWN"
								self.send_shutdown()

					elif button_pressed == ARRAY_BUTTON_PLAY:
						#play

						if GPIO.input(BUTTON_REWIND) == 0:
							print "* EXIIIT *"
							exit()
						else:
							if self.playing:
								print "* PAUSA *"
								self.paused_by_button = True
								self.send_pause()
							else:
								print "* PLAY *"
								self.paused_by_button = False
								self.send_play()
					elif button_pressed == ARRAY_BUTTON_REWIND:
						if GPIO.input(BUTTON_PLAY_PAUSE) == 0:
							print "* EXIIIT *"
							exit()
						else:
							print "* REWIND *"
							self.send_rewind()

				else:
					self.shut_down_timer = False

				sensor_val = GPIO.input(SENSOR_ID)
				if sensor_val == 1:
					if not self.playing:
						if not self.paused_by_button:
							print "* SENSOR PLAY *"
							self.send_play()


			try:
				client, address = self.sock.accept()

				if address[0] in self.ip_list:
					ip_index = self.ip_list.index(address[0])
					self.ip_list.remove(address[0])
					self.connected_clients-=1
					del self.client_list[ip_index]
				self.client_list.append(client)
				print "* Nueva conexion",address,len(self.client_list),"*"
				self.ip_list.append(address[0])
				self.connected_clients+=1
				if self.connected_clients >= self.total_clients:
					print "* CLIENTES CONECTADOS LISTO PARA OPERAR *"
					self.master_ready_to_operate = True
					time.sleep(2)
					self.omx_controller.ready(self.video_file_path)
					self.omx_controller.pause()
					#time.sleep(2)
					#self.omx_controller.rewind()
					#self.send_rewind()
					# ACA INICIO EL OMX EN EL MASTER
				
			except:
				pass
			"""if not self.shared_q.empty():
				input_char = self.shared_q.get()
				if input_char == 's':
					self.send_play()
				elif input_char == 'p':
					self.send_pause()
				elif input_char == 'r':
					self.send_rewind()"""

	def send_play(self):	
		if not self.playing:
			print " * ENVIO PLAY *"
			self.playing = True
			self.send("play")
			self.omx_controller.play()	
	def send_pause(self):	
		if self.playing:
			print " * ENVIO PAUSE *"
			self.playing = False
			self.send("pause")
			self.omx_controller.pause()	
	def force_rewind(self):
		pass
	def send_rewind(self):
		print " * ENVIO REWIND *"
		if self.playing:
			self.send("rewind")
			self.omx_controller.rewind()	
			self.playing = False
		else:
			print "mando play"
			self.playing = True
			self.send("play")
			self.omx_controller.play()	
			print "espero"
			time.sleep(1)
			print "mando rewind"
			self.send_rewind()
	def send_shutdown(self):
		self.send("shutdown")
		time.sleep(5)
		os.system("sudo shutdown -h now")
		#	duplicar acciones para master
		#self.omx_controller.rewind()
	def exit(self):
		self.omx_controller.kill()
		self.sock.close()
		os.system("fuser -k -n tcp 13000")
		sys.exit(0)
	#	conexion	#
	def send(self,msg):
		for client in self.client_list:
			try:
				sent = client.send(msg)
			except:
				print "error en cliente"
				break

	def init_socket(self):
		sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		#sock.setblocking(0)
		if self.master:
			sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		
		if self.master:
			sock.setblocking(0)
			sock.bind(('0.0.0.0',self.tcp_port))
			sock.listen(10)
		else:
			try:
				sock.connect((self.master_ip,self.tcp_port))
				sock.setblocking(0)
				self.im_connected = True
				
				#self.omx_controller.rewind()
				print "* CONECTADO AL MASTER *"
				
			except socket.error,v:
				self.im_connected = False
				time.sleep(1)
		return sock

def exit_handler():
	video_sync.exit()

atexit.register(exit_handler)

if __name__=='__main__':
	video_sync = VideoSync()
	video_sync.run()