#!/bin/bash

echo "Installing python3 snapd, and snap lxd in place."

sudo apt-get update
sudo apt-get install python3 python3-venv snapd zfsutils-linux
sudo snap install lxd

echo "You will enter the lxd init wizard. Default values are advised."
sudo lxd init

. ./activate
python3 -m pip install -r requirements.txt

echo "You are ready to go. Run python3 nestgen.py [INPUT]"