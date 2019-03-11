# Edge Gaming
Project for CS293B - Bringing video game streaming to the edge.

Coordinating server runs in cloud, manages authentication/which edge devices are available.

## Requirements
Before running the project, three components are required:
  1. A device running Windows 7 or later, to act as the edge device,
  2. A VM in a public or private cloud, to act as the coordinating server,
  3. A device running Windows 7 or later, or Linux, for which to stream the games to.

The edge device must also have installed on it the game you wish to play. An extension of this project could allow authorized games to be downloaded from an S3 bucket if the user selects an edge device that does not have the games available.

## Starting the Coordinating Server
Before running your server, you should fill out `config.py` as appropriate, and rename it to "custom_config.py". It is expected that you have both a certificate and corresponding private key for your VM that will be used to create the TLS connection with the client.

The coordinating server is intended to be run on a VM in the cloud.

### Required Packages
The cloud server relies on some packages being installed beforehand. On a Centos 7 VM image, the following command will install the necessary packages:
```
# yum install -y python.x86_64 mysql-server openssl.x86_64 python-pip
```
From there you just need to install the mysql connector via pip:
```
$ pip install --user mysql-connector-python
```
You should now have all the necessary packages installed on your VM to run your coordinating server.

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

`edgeservers` should have four fields:
  - `userid`: a single byte to represent the ID of the edge server
  - `ipaddr`: a character field to contain the IP associated with that edge server
  - `lastupdated`: an INT(8) field to represent the last UNIX timestamp at which an update was received
  - `available`: a BIT field to represent whether or not an edge server is currently available

Having a database with those two tables and fields will be enough to properly run the server.

### Running the Coordinating Server
The coordinating server can simply be run as follows:
```
sudo python server.py
```
Running as root is necessary to access the certificate and private key files. However, once configured (and before listening for connections), the server will drop root privileges.


## Starting the Edge Server
Before starting the edge server, you should fill out `streamserver.py` with the appropriate authentication key defined in your `config.py` for your cloud server.

Additionally, you must download the Gaming-Anywhere precompiled binaries for Windows x86, located here: http://gaminganywhere.org/dl/gaminganywhere-0.8.0-bin.win32.zip

That folder should be extracted to the `stream-server` directory, so that the `gaminganywhere-0.8.0` directory is a subdirectory of `stream-server`.

Additionally, you should configure your firewall to allow through ports 55555, 8554, and 8555.

Finally, alter one of the included `server.*.conf` files to correspond to the game you want to play.

If you would like to play a different game, follow the config file format in order to choose which game/application to execute. Be sure to modify line 129 in `streamserver.py` to correspond to your created configuration file.

After configuration is complete, you can run the stream server by simply typing:
```
python ./streamserver.py
```
This server will automatically send updates to the cloud, as well as listen for incoming gaming connections.

### Testing the Edge Server
The edge server has only been tested with the game "Stardew Valley," which is a proprietary game. The example config file `server.stardew.conf` has been included. Should you wish to play this game, you should modify the `game-exe` parameter in that file to point to your own installation of Stardew Valley. Then, you can place that file in the `gaminganywhere-0.8.0/bin/config` directory in order to make it playable.

A non-playable (and free!) application has also been used for testing - the d3dex samples. The samples are located here: http://gaminganywhere.org/dl/games/D3D.zip
In order to test those samples, simply modify the `gaminganywhere-0.8.0/bin/config/server.d3dex.conf` file to point to where the samples are located on your edge server.

## Starting the Client
The client can be run on either Windows or Linux, though Windows requires the Linux Subsystem to be installed. Gaming anywhere should be downloaded and extracted via the link above, and the `client.py` file should be placed within the `bin` directory. Then, just proceed as follows:
  1. Open Linux Subsystem for Windows (or a Terminal if on Linux)
  2. Use the command `openssl s_client -connect CLOUD_HOST:CLOUD_PORT` to open a connection to the stream server.
  3. Login or register to obtain an IP of an edge device ready for streaming.
  4. Using that IP, open a connection to the streaming server: `python client.py STREAMING_IP STREAMING_PORT`. The default streaming port is 55555.
  5. Play your game and enjoy! The client will inform the server when the connection has been killed, and the streaming server will automatically kill the game and prepare for more connections.

If you'd like to instead run the test application rather than a game, you can add a parameter to the client execution:
```
python client.py STREAMING_IP STREAMING_PORT test
```