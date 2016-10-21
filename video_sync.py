#!/usr/bin/env python2.7
import thread
import threading
import time
import sys,platform
import socket
import atexit

from socket import error as socket_error
from subprocess import Popen
from omx_controller import OMXController

# constantes
MODE_INIT = -1
MASTER_MODE_WAITING_CLIENTS = 0
SLAVE_SAY_HELLO = 1
MODE_READY = 3
VIDEO_FILE_NAME = 'video.mp4'
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

class VideoSync():
	def __init__(self):
		# cierro los puertos antes
		"""if platform.system() == "Linux":
			cmd = "fuser -k -n udp 12000 && fuser -k -n udp 13000"
			Popen([cmd], shell=True)"""

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
			self.udp_port = MASTER_INPUT_PORT
		else:
			#slave
			self.master_ip = str(sys.argv[2])	
			self.udp_port = SLAVE_INPUT_PORT

		self.sock = self.init_socket()
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
		if self.master:
			self.mode = MASTER_MODE_WAITING_CLIENTS
			self.as_master()
		else:
			self.mode = SLAVE_SAY_HELLO
			self.as_slave()

	def as_slave(self):
		print "* RUTINA DE CONEXION *"
		while True:
			try:
				#recibo data
				data,addr = self.sock.recvfrom(1024)
				if data == "welcome":
					self.mode = MODE_READY
					self.omx_controller.ready()
					print "* ESTOY LISTO *"
			except socket_error as serr:
				#no hay data
				pass
			if self.mode == SLAVE_SAY_HELLO:
				self.sock.sendto("hello", (self.master_ip, MASTER_INPUT_PORT))
				time.sleep(MSG_HELLO_TIMER)
			if self.mode == MODE_READY:
				if data == "play":
					data = ""
					self.omx_controller.play()
				elif data == "rewind":
					data = ""
					self.omx_controller.rewind()


	def as_master(self):
		while True:
			if(self.mode == MODE_READY):
				try:
					key_input=raw_input('key input :')
					if key_input == 'p':
						self.send_play()
					elif key_input == 'r':
						self.send_rewind()
				except ValueError:
					pass
			if self.mode == MASTER_MODE_WAITING_CLIENTS:
				try:
					data, addr = self.sock.recvfrom(1024)
					client_list.append(addr)
					if(data == "hello"):
						self.sock.sendto("welcome", (str(addr[0]), int(addr[1])))
						self.connected_clients += 1
						if self.connected_clients == self.total_clients:
							self.mode = MODE_READY
							print "* TODOS LOS CUADROS LISTOS *"	
				except socket_error as serr:
					#no hay data
					pass
	def send_play(self):	
		print " * ENVIO PLAY *"
		self.sock.sendto("play", ("255.255.255.255", SLAVE_INPUT_PORT))
		"""for client in client_list:
			print(client)
			self.sock.sendto("play", (str(client[0]), int(client[1])))"""
	def send_rewind(self):
		print " * ENVIO REWIND *"
		self.sock.sendto("rewind", ("255.255.255.255", SLAVE_INPUT_PORT))
	def exit(self):
		self.sock.close()
		self.omx_controller.kill()
	#	conexion	#
	def init_socket(self):
		sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM,0)
		if self.master:
			sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		sock.bind(('0.0.0.0',self.udp_port))
		sock.setblocking(0)
		return sock


def exit_handler():
	video_sync.exit()

atexit.register(exit_handler)

if __name__=='__main__':
	video_sync = VideoSync()
	video_sync.run()