import mysql.connector as mysqlc
import config
import iplocate
import socket, ssl
import hashlib
import threading
import random, string
import os, pwd, grp

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
    old_umask = os.umask(077)

class CoordServer(object):
  def __init__(self, host, port, udpport):
    self.host = host
    self.port = port
    self.udpport = udpport

    # To listen for client connections
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.sock.bind((self.host, self.port))
    
    # To listen for updates
    self.udpsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.udpsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.udpsock.bind((self.host, self.udpport))

    self.context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    self.context.load_cert_chain(certfile=config.Config.certinfo()['cert'], keyfile=config.Config.certinfo()['key'])
    self.context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
    self.context.set_ciphers("EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EHD")
        
    self.cnx = mysqlc.connect(**config.Config.dbinfo())
    self.cursor = self.cnx.cursor()

  def listen(self):
    # Start the UDP server to listen for updates from streaming servers
    threading.Thread(target = self.updateHosts).start()

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
    finally:
      self.cursor.close()
      self.cnx.close()

  # UDP Socket thread listening for updates from streaming servers
  def updateHosts(self):
    try:
      while True:
        data, addr = self.udpsock.recvfrom(1024)
        print("Received message: " + data)
    except:
      self.udpsock.close()

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

      except ValueError as verr:
        conn.send("Process failed, please try again.\n")

      except Exception as ex:
        conn.close()
        return
      
    conn.shutdown(1)
    conn.close()

  # Register a new client with username/password
  def processRegistration(self, conn, address):
    try:
      conn.send("Create a username: ")
      client_user = conn.recv(32).rstrip()
      self.cursor.execute("SELECT * FROM users WHERE username = %s", (client_user,))

      data = self.cursor.fetchall()
      
      if len(data) > 0:
        conn.send("Username already exists.\n")
        return False

      conn.send("Choose a password: ")
      client_pass = conn.recv(128).rstrip()

      # Generate a random 10 character salt
      client_salt = "".join(random.SystemRandom().choice(string.printable) for _ in range(10))
      client_pass = hashlib.sha256(client_pass + client_salt).hexdigest().upper()

      self.cursor.execute("INSERT INTO users VALUES (%s, %s, %s, %s)", (client_user, client_pass, client_salt, "100"))

      self.cnx.commit()
      
      conn.send("Registered successfully. Please reconnect to login.\n")
      return True

    except:
      print("ERROR: " + str(e))
      return False

  def processLogin(self, conn, address):
    try:
      conn.send("Enter username: ")
      client_user = conn.recv(32).rstrip()
    
      conn.send("Enter password: ")
      client_pass = conn.recv(128).rstrip()
  
      self.cursor.execute("SELECT passwordsalt FROM users WHERE username = %s", (client_user,))

      data = self.cursor.fetchone()

      if data is None:
        conn.send("Username or password is incorrect.\n")
        return False	

      client_pass += data[0]
      client_pass = hashlib.sha256(client_pass).hexdigest().upper()
    
      self.cursor.execute("SELECT hours FROM users WHERE username = %s AND passwordhash = %s", (client_user, client_pass))
      
      data = self.cursor.fetchone()

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
  cserver = CoordServer("", 44444, 44445)
  drop_privileges()
  cserver.listen()
