import socket
import hashlib, hmac
import threading
import time

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
        my_ip = bytes(map(int, socket.gethostbyname(socket.getfqdn()).split(".")))
        msg = self.id_num + my_ip
        signature = hmac.new(self.secretkey, msg, digestmod=hashlib.sha256).digest()
        self.sock.sendto(msg+signature, (self.host, self.port))
        print("Sent my IP and signature")

        time.sleep(30)
    except:
      print("Exitting.")

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
        data, addr = self.sock.recvfrom(64)

        if len(data.split()) > 1 and data.split()[1] == "OK?":
          self.sock.sendto("OK", addr)
    except:
      self.sock.close()


if __name__ == "__main__":
  in_use = False

  uc = UpdateClient("azzy.org", 44445)
  ls = ListenServer("", 55555)

  updateThread = threading.Thread(target = uc.doUpdates)
  updateThread.daemon = True
  updateThread.start()

  listenThread = threading.Thread(target = ls.listen())
  listenThread.daemon = True
  listenThread.start()