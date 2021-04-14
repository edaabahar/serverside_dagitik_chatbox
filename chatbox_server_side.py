import sys
import threading
import socket
import time
import queue
import pandas as pd

class readThread(threading.Thread):
	def __init__(self, tName, servSock, tQueue, fihrist1, fihrist2, logQueue, addr):
		threading.Thread.__init__(self)
		self.tName = tName
		self.servSock = servSock
		self.tQueue = tQueue

		self.fihristUser = fihrist1

		self.fihristRoom = fihrist2
		self.ad = ""
		self.control = False
		self.logQueue = logQueue
		self.addr = addr
		self.logQueue.put(f"New connection: {self.addr}")

	def run(self):
		print(self.tName, " read thread starting")
		self.logQueue.put(f"{self.tName} read thread starting")
		while True:
			try:
				data = self.servSock.recv(1024)
				self.incoming_parser(data.decode())
			except:
				print("readThread error")
				self.logQueue.put("readThread error")
				break
		print(self.tName, " read thread exiting")
		self.logQueue.put(f"{self.tName} read thread exiting")

	def incoming_parser(self, data):
		# hatali komut kontrolu icin
		komutlar = {"1":"NIC","2":"PIN","3":"GLS","4":"QUI", "5":"GNL","6":"PRV", "7":"OKP", "8":"OKG","9":"OKW","10":"TON","12":"NOP",
		"13":"CPW", "14":"OLS", "15":"OOD", "16":"KIC","17":"CLO","18":"BAN", "19":"MKA", "20":"GOD", "21":"OKB", "22":"OKA"}
		data = data.strip().split()

		if data[0] == "\x00":
			pass
		elif data[0] == "NIC" and self.control == False:
			if ":" not in data[1]:
				self.tQueue.put("Password is required. Please use NIC <username:pwd>")
			elif data[1] not in self.fihristUser.keys():
				# ilk defa kayıt yaparken NIC eda:123456
				user = data[1].split(":")[0]
				pin = data[1].split(":")[1]
				# digit kontrolu
				if pin.isdigit():
					self.fihristUser[user] = [queue.Queue(), pin, [], self.tName]
					self.control = True
					self.ad = user
					self.tQueue.put(f"WEL {user}")
					# herkese WRN gitmeli
					for a in self.fihristUser.values():
						if a[3] == self.tName:
							continue
						a[0].put(f"WRN {user} logged in.")
					self.logQueue.put(f"WRN {user} logged in")
				else:
					self.tQueue.put("REJ")
			elif data[1] in self.fihristUser.keys():
				user = data[1].split(":")[0]
				pin = data[1].split(":")[1]
				# giris yaparken pin kontrolu
				if pin == str(self.fihristUser[user][1]):
					self.fihristUser[user][0] = queue.Queue()
					self.ad = user
					self.tQueue.put(f"WEL {user}")
					self.control = True
				else:
					self.tQueue.put("REJ Wrong Password!")
		elif data[0] == "NIC" and self.control == True:
			self.tQueue.put("You are already logged in.")
		elif data[0] == "CPW" and self.control == True:
			user = data[1].split(":")[0]
			pin = data[1].split(":")[1]
			# sifre degistirme
			if pin.isdigit():
				self.fihristUser[user][1] = pin
				self.tQueue.put("OKC")
				self.logQueue.put(f"CPW {self.ad} has changed his/her password")
			else:
				self.tQueue.put("REC")
		elif data[0] == "CPW" and self.control == False:
			self.tQueue.put("LRR")
		elif data[0] == "QUI":
			# odadan cikis
			if len(data) > 1:
				if data[1] in self.fihristRoom.keys():
					if data[1] in self.fihristUser[self.ad][2]:
						self.tQueue.put(f"BYE {data[1]}:{self.ad}")
						# bulundugu odalardan oda ismini silme
						self.fihristUser[self.ad][2].remove(data[1])
						# odadan kullaniciyi silme
						if self.ad in self.fihristRoom[data[1]][0]:
							self.fihristRoom[data[1]][0].remove(self.ad)
						elif self.ad in self.fihristRoom[data[1]][1]:
							self.fihristRoom[data[1]][1].remove(self.ad)
						# odada kimse kalmadiysa odayi kapat
						if len(self.fihristRoom[data[1]][0]) == 0 and len(self.fihristRoom[data[1]][1]) == 0:
							self.fihristRoom.remove(data[1])
							self.logQueue.put(f"The room {data[1]} is closed")

						# odada admin kalmadiysa uyelerden birini admin yap
						elif len(self.fihristRoom[data[1]][0]) == 0 and len(self.fihristRoom[data[1]][1]) != 0:
							tempUser = self.fihristRoom[data[1]][1][0]
							self.fihristRoom[data[1]][1].remove(tempUser)
							self.fihristRoom[data[1]][0].append(tempUser)
							self.fihristUser[tempUser][0].put(f"WMA You are now admin of {data[1]}")
							self.logQueue.put(f"{tempUser} is now admin of {data[1]}")

						# herkese WRN gitmeli
						# adminler
						for a in self.fihristRoom[data[1]][0]:
							self.fihristUser[a][0].put(f"WRN {self.ad} left the {data[1]}")
						# members
						for a in self.fihristRoom[data[1]][1]:
							if a == self.ad:
								continue
							self.fihristUser[a][0].put(f"WRN {self.ad} left the {data[1]}")
						self.logQueue.put(f"{self.ad} left the room {data[1]}")

			else:			

				self.fihristUser[self.ad][0] = None
				self.tQueue.put(f"BYE {self.ad}")
		elif data[0] == "PIN":
			self.tQueue.put("PON")
		elif data[0] == "PRV" and self.control == True:
			#self.tQueue.put("OKP")
			t = data[1].split(":",1)[0] #eda
			if t in self.fihristUser.keys():
				mesaj = self.ad + ":"
				mesaj += data[1].split(":")[1]
				mesaj += " "
				mesaj += " ".join(data[2:])
				self.fihristUser[t][0].put(mesaj)
				self.tQueue.put("OKP")
				self.logQueue.put(f"PRV {mesaj}")
			else:
				# yoksa kisi NOP hatasi ver
				name = data[1].split(":")[0]
				self.tQueue.put(f"NOP: <{name}>")
		elif data[0] == "PRV" and self.control == False:
			self.tQueue.put("LRR")
		elif data[0] == "OOD" and self.control == True:
			if data[1] not in self.fihristRoom.keys():
				# yeni oda acarken acani admin olarak atama
				self.fihristRoom[data[1]] = [[self.ad], [], []]
				self.fihristUser[self.ad][2].append(data[1])
				self.tQueue.put("OKO")
				self.logQueue.put(f"{data[1]} is created by {self.ad}")
			else:
				self.tQueue.put("NOO room is already exist, choose another name or log in with GOD <room>")
		elif data[0] =="GLS" and self.control == True:
			if data[1] in self.fihristRoom.keys() and len(self.fihristRoom[data[1]][0]) == 0 and len(self.fihristRoom[data[1]][1]) == 0:
				self.tQueue.put("LST")
				self.tQueue.put("The Room is empty...")
			# oyle bir oda varsa ve kullanici o odadaysa listele
			elif data[1] in self.fihristRoom.keys() and data[1] in self.fihristUser[self.ad][2]:
				users = ""
				for u in self.fihristRoom[data[1]][0]:
					users += u
					users += ":"
					users += "admin"
					users += ";"
				for u in self.fihristRoom[data[1]][1]:
					users += u
					users += ":"
					users += "member"
					users += ";"
				users = users[:-1]
				self.tQueue.put("LST")
				self.tQueue.put(users)
			else:
				self.tQueue.put("NST")
		elif data[0] == "GNL" and self.control == True:
			# oda ismi varsa
			if data[1].split(":")[0] in self.fihristRoom.keys():
				# kullanici o odadaysa
				if data[1].split(":")[0] in self.fihristUser[self.ad][2]:
					mesaj = "GNL "
					mesaj += data[1].split(":")[0]
					mesaj += ";"
					mesaj += self.ad
					mesaj += ":"
					mesaj += data[1].split(":")[1]
					mesaj += " "
					mesaj += " ".join(data[2:])

					# herkesin kuyruguna mesaji koyma
					oda = data[1].split(":")[0]
					# adminler
					for a in self.fihristRoom[oda][0]:
						if a == self.ad:
							continue
						self.fihristUser[a][0].put(mesaj)
					# memebers
					for a in self.fihristRoom[oda][1]:
						if a == self.ad:
							continue
						self.fihristUser[a][0].put(mesaj)
					self.tQueue.put("OKG")
					self.logQueue.put(f"{mesaj}")
			else:
				self.tQueue.put("NKG")
		elif data[0] == "OLS" and self.control == True:
			# tum odalar
			if len(data) < 2:
				rooms = ""
				for r in self.fihristRoom.keys():
					rooms += r
					rooms += ":"
				rooms = rooms[:-1]
				self.tQueue.put("LSO")
				self.tQueue.put(rooms)
			elif data[1] == self.ad:
				# icinde bulunulan odalar
				rooms = ""
				for r in self.fihristUser[self.ad][2]:
					rooms += r
					rooms += ":"
				rooms = rooms[:-1]
				self.tQueue.put("LSO")
				self.tQueue.put(rooms)
		elif data[0] == "KIC" and self.control == True:
			oda = data[1].split(":")[0]
			user = data[1].split(":")[1]
			# atan kisi admin mi ve atilan kisi admin degilse ve atilan kisi odada varsa ve oda varsa
			if self.ad in self.fihristRoom[oda][0] and user not in self.fihristRoom[oda][0] and user in self.fihristRoom[oda][1] and oda in self.fihristRoom.keys():
				self.tQueue.put("OKK")
				self.fihristRoom[oda][1].remove(user)
				self.fihristUser[user][2].remove(oda)
				self.fihristUser[user][0].put(f"WRK You are kicked from {oda}")
				self.logQueue.put(f"WRK {user} is kicked from {oda} by {user}")
			else:
				self.tQueue.put("NKC")
		elif data[0] == "CLO" and self.control == True:
			# boyle bir oda var mi ve silen kisi admin mi
			if data[1] in self.fihristRoom.keys() and self.ad in self.fihristRoom[data[1]][0]:
				
				self.tQueue.put("OKL")
				
				# adminler
				for a in self.fihristRoom[data[1]][0]:
					if a == self.ad:
						continue
					self.fihristUser[a][0].put(f"WOK {self.ad} closed {data[1]}")
				# members
				for a in self.fihristRoom[data[1]][1]:
					self.fihristUser[a][0].put(f"WRN {self.ad} closed {data[1]}")
				self.fihristRoom.pop(data[1])
				self.logQueue.put(f"WRN {data[1]} is closed by {self.ad}")
			else:
				self.tQueue.put("NKL")
		elif data[0] == "BAN" and self.control == True:
			oda = data[1].split(":")[0]
			user = data[1].split(":")[1]
			# boyle bir oda var mi ve banlayan admin mi ve banlanan admin mi
			if oda in self.fihristRoom.keys() and self.ad in self.fihristRoom[oda][0] and user in self.fihristRoom[oda][1]:
				
				self.tQueue.put("OKB")
				# kullaniciyi members listten silme
				self.fihristRoom[oda][1].remove(user)
				self.fihristUser[user][2].remove(oda)
				self.fihristRoom[oda][2].append(user)
				self.fihristUser[user][0].put(f"WBN You are banned from {oda}")
				self.logQueue.put(f"WBN {user} banned from {oda} by {self.ad}")
			else:
				self.tQueue.put("NBB")
		elif data[0] == "MKA" and self.control == True:
			oda = data[1].split(":")[0]
			user = data[1].split(":")[1]
			# oda var mi
			if oda in self.fihristRoom.keys():
				# kisi admin mi
				if self.ad in self.fihristRoom[oda][0]:
					# kisi member mi 
					if user in self.fihristRoom[oda][1]:
						self.fihristRoom[oda][1].remove(user)
						self.fihristRoom[oda][0].append(user)
						self.tQueue.put("OKM")
						self.fihristUser[user][0].put(f"WMA You are now admin of {oda}")
						self.logQueue.put(f"WMA {self.ad} maked admin {user} of the room {oda}")
			else:
				self.tQueue.put("NOM")
		elif data[0] == "GOD" and self.control == True:
			# oda var mi ve kullanici banli degilse ve kullanici zaten odada degilse
			if data[1] in self.fihristRoom.keys() and self.ad not in self.fihristRoom[data[1]][2] and data[1] not in self.fihristUser[self.ad][2]:
				
				self.fihristRoom[data[1]][1].append(self.ad)
				self.fihristUser[self.ad][2].append(data[1])
				self.tQueue.put("OKD")
				# herkese WRN gitmeli
				# adminler
				for a in self.fihristRoom[data[1]][0]:
					self.fihristUser[a][0].put(f"WRN {self.ad} logged in to {data[1]}")
				# memebers
				for a in self.fihristRoom[data[1]][1]:
					if a == self.ad:
						continue
					self.fihristUser[a][0].put(f"WRN {self.ad} logged in to {data[1]}")
				self.logQueue.put(f"WRN {self.ad} logged in to {data[1]}")

			else:
				self.tQueue.put("NOD")
		elif len(data) > 0 and data[1] not in komutlar.values() and self.control == False:
			self.tQueue.put("LRR")
			self.logQueue.put("LRR Login Error")
		elif data[0] not in komutlar.values():
			self.tQueue.put("ERR")
			self.logQueue.put(f"{self.ad}'s command {data[0]} not recognized.")



class writeThread(threading.Thread):
	def __init__(self, tName, servSock, tQueue, fihristUser, logQueue):
		threading.Thread.__init__(self)
		self.tName = tName
		self.servSock = servSock
		self.tQueue = tQueue
		self.fihristUser = fihristUser
		self.logQueue = logQueue

	def run(self):
		print(self.tName, " write thread starting")
		self.logQueue.put(f"{self.tName} write thread starting")
		#self.servSock.send(" ".encode())
		while True:
			try:
				time.sleep(1)
				if not self.tQueue.empty():
					data = self.tQueue.get()
				#print("sunucu:" ,data)
					self.servSock.send(data.encode())
				time.sleep(0.1)
				for a in self.fihristUser.values():
					if self.tName == a[3]:
						if not a[0].empty():
							self.servSock.send(a[0].get().encode())
			except:
				print("writeThread error")
				self.logQueue.put("writeThread error")
				break
		print(self.tName, " write thread exiting")
		self.logQueue.put(f"{self.tName} write thread exiting")

class logThread(threading.Thread):
	def __init__(self, logQueue, file):
		threading.Thread.__init__(self)
		self.logQueue = logQueue
		self.file = file

	def run(self):
		# dosyayi ac datayi al icine yaz
		f = open(self.file, "w")
		while True:
			data = self.logQueue.get()

			f.write(f"{time.ctime()} ;; {data}\r")
			f.flush()

def main():
	if not len(sys.argv) == 3:
		print("Insufficient parameters")
		return

	global fihrist1, fihrist2
	fihrist1 = dict()
	fihrist2 = dict()

	s = socket.socket()
	host = sys.argv[1]
	port = int(sys.argv[2])

	s.bind((host,port))
	s.listen(5)

	counter = 0

	logQueue = queue.Queue()
	lThread = logThread(logQueue, "log.txt")
	lThread.start()
	while True:
		servSock, addr = s.accept() # bekleme
		print(addr)
		tQueue = queue.Queue()
		rThread = readThread(counter, servSock, tQueue, fihrist1, fihrist2, logQueue, addr)
		rThread.start()
		wThread = writeThread(counter, servSock, tQueue, fihrist1, logQueue)
		wThread.start()
		counter += 1
	s.close()
'''
	# fihrist bilgilerini dosyaya yazma
	f1 = open("fihristUser.txt", "w")
	for item in fihristUser.items():
		f1.write(item)
	f2 = open("fihristRoom.txt", "w")
	for item in fihristRoom.items():
		f2.write(item)
'''
if __name__ == '__main__':
	main()
