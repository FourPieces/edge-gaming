# Sketch of code:
# Take IP as argument
# Send streamreq to IP
# On OK, start up ga-client
# On NO, return error
# On ga-client exit, send STREAMEND

import sys
import subprocess
import socket

if __name__ == "__main__":
  if len(sys.argv) != 2:
    print("USAGE: python client.py EDGE_IP EDGE_PORT")
    sys.exit(0)
  
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

  try:
    edge_ip = sys.argv[1]
    edge_port = int(sys.argv[2])
    sock.sendto(b"STREAMREQ", (edge_ip, edge_port))

    data, addr = sock.recvfrom(16)

    if data == bytes(b"OK"):
      print("Starting game.")
      game = subprocess.Popen(['.\\bin\\ga-client',
                               '.\\bin\\config\\client.rel.conf',
                               'rtsp://' + edge_ip + ":8554/desktop"],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      game.wait()
      print("Finished playing.")
      sock.sendto(b"STREAMEND", (edge_ip, edge_port))
    else:
      print("Server currently busy, please try again.")
  except:
    print("Something went wrong. Your game could not be started.")
  finally:
    sock.close()