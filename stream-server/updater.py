import socket
import hashlib, hmac
import threading
import time
import subprocess

class UpdateClient(object):
  def __init__(self, host, port):
    self.host = host
    self.port = port
    self.secretkey = bytes(b"MySecret")
    self.id_num = bytes([123])
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

  def doUpdates(self):
    try:
      while True:
        my_ip = bytes(map(int, self.get_ip().split(".")))
        msg = self.id_num + my_ip
        signature = hmac.new(self.secretkey, msg, digestmod=hashlib.sha256).digest()
        self.sock.sendto(msg+signature, (self.host, self.port))
        print("Sent my IP and signature")

        time.sleep(30)
    except:
      print("Exitting.")

  # From https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
  def get_ip(self):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

class ListenServer(object):
  def __init__(self, host, port):
    self.host = host
    self.port = port
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.sock.bind((self.host, self.port))

  def listen(self):
    # Start the UDP server to listen for updates from streaming servers
    try:
      while True:
        data, addr = str(self.sock.recvfrom(64))
        print(data)

        if len(data.split()) > 1:
          self.sock.sendto(b"OK", addr)
          subprocess.Popen(['C:\\Users\\Husky\\Desktop\\cs293b-3\\gaminganywhere-0.8.0\\bin\\ga-server-event-driven', 'C:\\Users\\Husky\\Desktop\\cs293b-3\\gaminganywhere-0.8.0\\bin\\config\\server.stardew.conf'])
        else:
          print("Wow bad")
        
    except Exception as e:
      print(str(e))
      self.sock.close()

    except Exception as e:
      self.sock.close()
      print("Exception: " + str(e))


if __name__ == "__main__":
  in_use = False

  uc = UpdateClient("azzy.org", 44445)
  ls = ListenServer("", 55555)

  updateThread = threading.Thread(target = uc.doUpdates)
  updateThread.daemon = True
  updateThread.start()

  listenThread = threading.Thread(target = ls.listen)
  listenThread.daemon = True
  listenThread.start()

  while True:
    pass