import socket
import hashlib, hmac
import threading
import time

class UpdateClient(object):
  def __init__(self, host, port):
    self.host = host
    self.port = port
    self.secretkey = bytes("MySecret")
    self.id_num = bytes([123])
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

  def doUpdates(self):
    try:
      while True:
        my_ip = bytes(map(int, socket.gethostbyname(socket.getfqdn()).split(".")))
        msg = self.id_num + my_ip
        signature = hmac.new(self.secretkey, msg, digestmod=hashlib.sha256).digest()
        self.sock.sendto(msg+signature, (self.host, self.port))

        time.sleep(30)
    except:
      print("Exitting.")

if __name__ == "__main__":
  uc = UpdateClient("azzy.org", 44445)
  uc.doUpdates()