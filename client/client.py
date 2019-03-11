# Should be placed in the gaming-anywhere/bin directory

import sys
import subprocess
import socket

if __name__ == "__main__":
  if len(sys.argv) != 3 and len(sys.argv) != 4:
    print("USAGE: python client.py EDGE_IP EDGE_PORT [test]")
    sys.exit(0)
  
  testing = False
  confpath = './config/client.abs.conf'

  if len(sys.argv) == 4:
    testing = True

  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

  try:
    sock.settimeout(15)
    edge_ip = sys.argv[1]
    edge_port = int(sys.argv[2])

    if not testing:
      sock.sendto(b"STREAMREQ", (edge_ip, edge_port))
    else:
      sock.sendto(b"STREAMTST", (edge_ip, edge_port))

    data, addr = sock.recvfrom(16)

    if data == bytes(b"OK"):
      print("Starting game.")
      game = subprocess.Popen(['./ga-client',
                               confpath,
                               'rtsp://' + edge_ip + ":8554/desktop"])
      game.wait()
      print("Finished playing.")
      sock.sendto(b"STREAMEND", (edge_ip, edge_port))
    else:
      print("Server currently busy, please try again.")
  except:
    print("Something went wrong. Your game could not be started.")
  finally:
    sock.close()