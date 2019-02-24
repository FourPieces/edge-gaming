# Edge Gaming
Project for CS293B - Bringing video game streaming to the edge.

Coordinating server runs in cloud, manages authentication/which edge devices are available.


## Starting the Coordinating Server
Before running your server, you should fill out `config.py` as appropriate, and rename it to "custom_config.py". It is expected that you have both a certificate and corresponding private key for your VM that will be used to create the TLS connection with the client.

The coordinating server is intended to be run on a VM in the cloud.

### Configuring Your Security Group
The security group should have the following allowed connections:
 - Port 44444 (TCP) should be open to allow client connections  
 - Port 44445 (UDP) should be open to allow updates from the edge devices

No other security group settings are required for your VM.

### Configuring Your Database
It is intended that MySQL be the DBMS running on the VM. The database on this server should have two tables: `users` and `edgeservers`. Currently, new edge server IDs need to be manually insertted into the `edgeservers` table.

`users` should have four fields:
  - `username`: a character field to contain the username (the key),
  - `passwordhash`: a character field to contain the hash of the password (SHA256),
  - `passwordsalt`: a character field to contain a unique salt to be appended to the password for hashing,
  - `hours`: the number of hours a user has left for playing.

`edgeservers` should have two fields:
  - `userid`: a single byte to represent the ID of the edge server
  - `ipaddr`: a character field to contain the IP associated with that edge server

Having a database with those two tables and fields will be enough to properly run the server.

### Running the Coordinating Server
The coordinating server can simply be run as follows:
```
sudo python server.py
```
Running as root is necessary to access the certificate and private key files. However, once configured (and before listening for connections), the server will drop root privileges.