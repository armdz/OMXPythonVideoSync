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
import errno
import math
import time
from threading import Thread
from socket import error as socket_error
from subprocess import Popen
from omx_controller import OMXController

# constantes
MODE_INIT = -1
MASTER_MODE_WAITING_CLIENTS = 0
SLAVE_SAY_HELLO = 1
MODE_READY = 3
SLAVE_INPUT_PORT = 12000
MASTER_INPUT_PORT = 13000
MSG_HELLO_TIMER = 2	#cada cuando mando el mensaje

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

class VideoSync():
	def __init__(self):
		self.master = False
		arg_len = len(sys.argv)
		if arg_len < 3:
			print "* Como ejecutar el script ?"
			print "* Para SLAVE los argumentos: ",sys.argv[0],"master NUMERO_CLIENTES_A_ESPERAR"
			print "* Para SLAVE los argumentos: ",sys.argv[0],"slave IP_MASTER"
			exit()
		if  str(sys.argv[1]) == "master":
			self.master = True
			self.total_clients = int(sys.argv[2])
			self.tcp_port = MASTER_INPUT_PORT
			self.client_list = []
			self.ip_list = []
			self.sock = self.init_socket()
		else:
			#slave
			self.master_ip = str(sys.argv[2])	
			self.tcp_port = MASTER_INPUT_PORT
			self.im_connected = False
		self.playing = False
		self.rewinded = False
		self.ping_tick = time.clock()
		self.connected_clients = 0

	def run(self):
		print 	"**************************************"
		print	"VideoSync * PLAN *"
		if self.master:
			print	"Esperando a",total_clients, "cliente/s"
		else:
			print	"Slave"
		print 	"**************************************"
		self.omx_controller = OMXController()
		self.omx_controller.ready()
		if self.master:
			self.mode = MASTER_MODE_WAITING_CLIENTS
			self.as_master()
		else:
			self.mode = SLAVE_SAY_HELLO
			self.as_slave()

	def as_slave(self):
		print "* RUTINA DE CONEXION *"
		while True:
			if self.im_connected:
				try:
					data,addr = self.sock.recvfrom(1024)
					if not data:
						pass
					else:
						if data == "play":
							self.omx_controller.play()
						elif data == "pause":
							self.omx_controller.pause()
						elif data == "rewind":
							self.omx_controller.rewind()
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
					time.sleep(5)
					self.omx_controller.rewind()
					self.rewinded = True
				else:
					self.sock = self.init_socket()


			

	def add_input(self,input_queue):
		while True:
			input_queue.put(sys.stdin.read(1))
			pass

	def as_master(self):
		self.shared_q = Queue.Queue()
		input_thread = threading.Thread(target=self.add_input, args=(self.shared_q,))
		input_thread.daemon = True
		input_thread.start()
		last_update = time.time()
		while True:
			try:
				client, address = self.sock.accept()

				if address[0] in self.ip_list:
					ip_index = self.ip_list.index(address[0])
					self.ip_list.remove(address[0])
					del self.client_list[ip_index]
				self.client_list.append(client)
				self.ip_list.append(address[0])
				print "* Nueva conexion",address,len(self.client_list),"*"
			except:
				pass
			if not self.shared_q.empty():
				input_char = self.shared_q.get()
				if input_char == 's':
					self.send("play")
				elif input_char == 'p':
					self.send("pause")
				elif input_char == 'r':
					self.send("rewind")


	def send_play(self):	
		if not self.playing:
			print " * ENVIO PLAY *"
			self.playing = True
			self.send("play")
		#self.omx_controller.play()	
	def send_pause(self):	
		if self.playing:
			print " * ENVIO PAUSE *"
			self.playing = False
			self.send("pause")
		#self.omx_controller.play()	
	def send_rewind(self):
		print " * ENVIO REWIND *"
		self.send("rewind")
		self.playing = False
		#	duplicar acciones para master
		#self.omx_controller.rewind()
	def exit(self):
		self.sock.close()
		self.omx_controller.kill()
		pass
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
			print self.tcp_port
			sock.setblocking(0)
			sock.bind(('0.0.0.0',self.tcp_port))
			sock.listen(10)
		else:
			try:
				sock.connect((self.master_ip,self.tcp_port))
				sock.setblocking(0)
				self.im_connected = True
				time.sleep(3)
				#self.omx_controller.rewind()
				print "* CONECTADO AL MASTER *"
				
			except socket.error,v:
				self.im_connected = False
				time.sleep(1)
		return sock

def exit_handler():
	pass
	video_sync.exit()

atexit.register(exit_handler)

if __name__=='__main__':
	video_sync = VideoSync()
	video_sync.run()