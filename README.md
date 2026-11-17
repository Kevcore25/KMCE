# KCKMCE
This is the main repository for KCKMCE, a custom global account system that unifies my Minecraft servers.

## Context
For personal reasons, I created a Python to Minecraft Server interface using RCON and log files to use Python to communicate with the server, in which I named it KMCE (or Kevcore's Minecraft Extractor).

A sample KMCEv3.py file can be found in [my MCTools repository](https://github.com/Kevcore25/MCTools) which is more tailored to a generic Python to Minecraft layer. It also includes a base KCKMCE class.

This builds onto my KMCE system by integrating an account system. In particular, this is for my global economy account system that can be used across multiple servers (and in different backend servers too). 

## What is in this repo
### Client
The client folder simply contains the KMCEv3.py that focuses more on developing the KCKMCE object (which adds this account system). 
For now it is just one file (to make it easier to download/run).

### Server
The server folder contains the backend server for KMCE. For now, it focuses on getting things to work without paying too much attention to security (it does not contain any critical sensitive information anyway) and uses IP whitelisting as a basic security measure.