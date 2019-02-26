from dbinterface import DatabaseInterface
import custom_config
import iplocate
import socket, ssl
import hashlib, hmac
import threading
import math
import random
import string
import os, pwd, grp
import sys
import time

# From https://stackoverflow.com/questions/2699907/dropping-root-permissions-in-python
# Need to start server as root for cert/privkey access, but don't want to stay root
def drop_privileges(uid_name='nobody', gid_name='nogroup'):
  if os.getuid() != 0:
    # We're not root so, like, whatever dude
      return

  # Get the uid/gid from the name
  running_uid = pwd.getpwnam(uid_name).pw_uid
  running_gid = grp.getgrnam(gid_name).gr_gid

  # Remove group privileges
  os.setgroups([])

  # Try setting the new uid/gid
  os.setgid(running_gid)
  os.setuid(running_uid)

  # Ensure a very conservative umask
  os.umask(0o77)

class AbstractServer(object):
  def __init__(self, host, port, mydb, socket_type = socket.SOCK_STREAM):
    self.host = host
    self.port = port
    self.db_conn = mydb

    self.sock = socket.socket(socket.AF_INET, socket_type)
    self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.sock.bind((self.host, self.port))

  # Abstract method
  def listen(self):
    pass

class UpdateServer(AbstractServer):
  def __init__(self, host, port, mydb):
    super(UpdateServer, self).__init__(host, port, mydb, socket_type=socket.SOCK_DGRAM)

  def listen(self):
    # Start the UDP server to listen for updates from streaming servers
    udpthread = threading.Thread(target = self.updateHosts)
    udpthread.daemon = True
    udpthread.start()

  # UDP Socket thread listening for updates from streaming servers
  def updateHosts(self):
    try:
      while True:
        data, _ = self.sock.recvfrom(64)
        data_bytes = bytearray(data.rstrip())

        # 1 byte ID, 4 bytes IP, 32 bytes HMAC
        if len(data_bytes) != 37:
          print("Bad update received.")
          continue
        
        idstr = str(int(data_bytes[0]))
        ipstr = ".".join(str(int(x)) for x in data_bytes[1:5])
        print("Received " + idstr + " and " + ipstr)

        valid = self.validateHMAC(data_bytes)

        if not valid:
          print("Bad MAC received for update.")
          continue

        num_updated = self.db_conn.update("UPDATE edgeservers SET ipaddr = %s WHERE userid = %s", (ipstr, idstr))

        if num_updated > 1:
          raise Exception("Updated more than 1 entry.")
        elif num_updated == 0:
          print("No updates.")
          
      
    except Exception as e:
      print("Some issue: " + str(e))
      print("Closing update socket.")
      self.sock.close()

  def validateHMAC(self, data_bytes):
    msg = data_bytes[:5]
    mac = data_bytes[5:]

    return hmac.compare_digest(hmac.new(custom_config.Config.hmacsecret(), msg, digestmod=hashlib.sha256).digest(), mac)
    
class CoordServer(AbstractServer):
  def __init__(self, host, port, mydb):
    super(CoordServer, self).__init__(host, port, mydb)

    self.context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    self.context.load_cert_chain(certfile=custom_config.Config.certinfo()['cert'], keyfile=custom_config.Config.certinfo()['key'])
    self.context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
    self.context.set_ciphers("EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EHD")

  def listen(self):
    # The main thread will listen for client connections
    self.sock.listen(5)
    
    try:
      while True:
        client, addr = self.sock.accept()
        client.settimeout(60)
        conn = self.context.wrap_socket(client, server_side=True)
        threading.Thread(target = self.displayMenu, args = (conn, addr)).start()
    except KeyboardInterrupt:
      print("[!] Keyboard Interrupted!")
      self.sock.close()

  # Handles the initial connect from a client
  # Display a menu that the client can use to navigate
  def displayMenu(self, conn, address):
    result = False			
    while not result:
      try:
        conn.send("1. Login\n2. Register\nSelect an option: ")
        selection = int(conn.recv(10).rstrip())
      
        if selection == 1:
          result = self.processLogin(conn,address)	
        elif selection == 2:
          result = self.processRegistration(conn, address)

        if not result:
          conn.send("Process failed, please try again.\n")
        else:
          closest_list = self.findClosestServers(address[0])
          closest = self.findClosestAvailable(address[0], closest_list)
          if closest is not None:
            conn.send("Success. The closest server ready to play is: " + closest + "\n")
          else:
            conn.send("All edge servers are currently busy.")

      except ValueError:
        conn.send("Process failed, please try again.\n")

      except Exception as e:
        print("Exception: " + str(e))
        print("Closing client connection.")
        conn.close()
        return
      
    conn.shutdown(1)
    conn.close()

  # Once we have a list of servers, ping them all in order
  # until one is found that's ready to accept a gaming connection
  def findClosestAvailable(self, client_ip, closest_list):
    edgechecksock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
      edgechecksock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      edgechecksock.bind((self.host, 55555))
      edgechecksock.settimeout(5)

      for closest in closest_list:
        edgechecksock.sendto(b"STREAMREQ", (closest[0], 55555))
        response, _ = edgechecksock.recvfrom(16)
        
        if str(response) == "OK":
          return closest[0]

    except Exception as e:
      print("Something went wrong: " + str(e))
      edgechecksock.close()

    return None

  # Obtain a list of servers that have been updated semi-recently
  # Sorted by distance away from the client
  def findClosestServers(self, client_host):
    data = self.db_conn.query_all("SELECT ipaddr FROM edgeservers", None)

    (clilat, clilon) = iplocate.get_location_latlon(client_host)
    res = []

    for addr in data:
      (servlat, servlon) = iplocate.get_location_latlon(addr[0])
      curr_dist = math.sqrt((servlat - clilat)**2 + (servlon - clilon)**2)
      res.append((addr[0], curr_dist))

      time.sleep(0.5)

    # Sort by distance in ascending order
    res.sort(key = lambda tup: tup[1])
    return res

  # Register a new client with username/password
  def processRegistration(self, conn, address):
    try:
      conn.send("Create a username: ")
      client_user = conn.recv(32).rstrip()
      data = self.db_conn.query_all("SELECT * FROM users WHERE username = %s", (client_user,))

      if len(data) > 0:
        conn.send("Username already exists.\n")
        return False

      conn.send("Choose a password: ")
      client_pass = conn.recv(128).rstrip()

      # Generate a random 10 character salt
      client_salt = "".join(random.SystemRandom().choice(string.printable) for _ in range(10))
      client_pass = hashlib.sha256(client_pass + client_salt).hexdigest().upper()

      self.db_conn.update("INSERT INTO users VALUES (%s, %s, %s, %s)", (client_user, client_pass, client_salt, "100"))
      
      conn.send("Registered successfully. Please reconnect to login.\n")
      return True

    except Exception as e:
      print("ERROR: " + str(e))
      return False

  def processLogin(self, conn, address):
    try:
      conn.send("Enter username: ")
      client_user = conn.recv(32).rstrip()
    
      conn.send("Enter password: ")
      client_pass = conn.recv(128).rstrip()
  
      data = self.db_conn.query_one("SELECT passwordsalt FROM users WHERE username = %s", (client_user,))

      if data is None:
        conn.send("Username or password is incorrect.\n")
        return False	

      client_pass += data[0]
      client_pass = hashlib.sha256(client_pass).hexdigest().upper()
    
      data = self.db_conn.query_one("SELECT hours FROM users WHERE username = %s AND passwordhash = %s", (client_user, client_pass))
      
      if data is None:
        conn.send("Username or password is incorrect.\n")
        return False

      conn.send("You have " + str(data[0]) + " hours left.\n")
      conn.send("You live at: " + iplocate.get_location_str(conn.getpeername()[0]) + "\n")
      return True

    except Exception as e:
      print("ERROR: " + str(e))
      return False

if __name__ == "__main__":
  mydb = DatabaseInterface()
  cserver = CoordServer("", 44444, mydb)
  userver = UpdateServer("", 44445, mydb)
  drop_privileges()
  userver.listen()
  cserver.listen()