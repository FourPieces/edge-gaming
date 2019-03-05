import socket
import hashlib, hmac
import threading
import time
import subprocess
import re
import os, signal
import sys

# RW Lock from https://www.oreilly.com/library/view/python-cookbook/0596001673/ch06s04.html
# Modified to fit the playing boolean structure
class PlayLock(object):
  def __init__(self):
    self._read_ready = threading.Condition(threading.Lock())
    self._readers = 0
    self._playing = False

  def set_playing(self, playing = False):
    self._acquire_write()
    self._playing = playing
    self._release_write()

  def get_playing(self):
    res = False
    self._acquire_read()
    res = self._playing
    self._release_read()
    return res

  def _acquire_read(self):
    """ Acquire a read lock. Blocks only if a thread has
    acquired the write lock. """
    self._read_ready.acquire(  )
    try:
      self._readers += 1
    finally:
      self._read_ready.release(  )

  def _release_read(self):
    """ Release a read lock. """
    self._read_ready.acquire(  )
    try:
      self._readers -= 1
      if not self._readers:
        self._read_ready.notifyAll(  )
    finally:
      self._read_ready.release(  )

  def _acquire_write(self):
    """ Acquire a write lock. Blocks until there are no
    acquired read or write locks. """
    self._read_ready.acquire(  )
    while self._readers > 0:
      self._read_ready.wait(  )

  def _release_write(self):
    """ Release a write lock. """
    self._read_ready.release(  )

class UpdateClient(object):
  def __init__(self, host, port, play_lock):
    self.host = host
    self.port = port
    self.secretkey = bytes(b"MySecret")
    self.id_num = bytes([123])
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.play_lock = play_lock

  def doUpdates(self):
    try:
      while True:
        my_ip = bytes(map(int, self.get_ip().split(".")))

        if self.play_lock.get_playing():
          avail = bytes([0])
        else:
          avail = bytes([1])

        msg = self.id_num + my_ip + avail
        signature = hmac.new(self.secretkey, msg, digestmod=hashlib.sha256).digest()

        self.sock.sendto(msg+signature, (self.host, self.port))
        print("Sent my IP and signature")
        print(str(len(msg+signature)))

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
  def __init__(self, host, port, play_lock):
    self.host = host
    self.port = port
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.sock.bind((self.host, self.port))
    self.play_lock = play_lock

    self.game_pid = -1

  def listen(self):
    # Start the UDP server to listen for updates from streaming servers
    try:
      while True:
        data, addr = self.sock.recvfrom(16)

        if data == bytes(b"STREAMOK?"):
          if not self.play_lock.get_playing():
            self.sock.sendto(b"OK", addr)
          else:
            self.sock.sendto(b"NO", addr)
        elif data == bytes(b"STREAMREQ"):
          if not self.play_lock.get_playing():
            curr_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
            game = subprocess.Popen([curr_dir + '/gaminganywhere-0.8.0/bin/ga-server-event-driven',
                                    curr_dir + '/gaminganywhere-0.8.0/bin/config/server.stardew.conf'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            game.wait()
            _, err = game.communicate()
            ferr = re.findall(r"pid=(\d{4,5})", str(err))
            if len(ferr) > 0:
              self.game_pid = int(ferr[0])
              print("Game PID: " + ferr[0])
              self.play_lock.set_playing(True)
              time.sleep(10)
              self.sock.sendto(b"OK", addr)
            else:
              print(str(err))
              self.sock.sendto(b"NO", addr)
          else:
            self.sock.sendto(b"NO", addr)
        elif data == bytes(b"STREAMEND"):
          if self.play_lock.get_playing() and self.game_pid > 1024:
            print("Killing the game.")
            self.play_lock.set_playing(False)
            try:
              os.kill(self.game_pid, signal.SIGTERM)
            except:
              pass
            self.game_pid = -1
        else:
          print("Wow bad")
        
    except Exception as e:
      print(str(e))
      self.sock.close()


if __name__ == "__main__":
  play_lock = PlayLock()

  uc = UpdateClient("azzy.org", 44445, play_lock)
  ls = ListenServer("", 55555, play_lock)

  updateThread = threading.Thread(target = uc.doUpdates)
  updateThread.daemon = True
  updateThread.start()

  listenThread = threading.Thread(target = ls.listen)
  listenThread.daemon = True
  listenThread.start()

  while True:
    pass