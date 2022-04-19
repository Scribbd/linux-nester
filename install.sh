#!/bin/bash

echo "Installing python3 snapd, and snap lxd in place."

sudo apt-get update
sudo apt-get install python3 python3-venv python3-pip snapd zfsutils-linux -y
sudo snap remove --purge lxd
sudo snap install lxd
sudo lxd init --auto

echo "Setting up virtual environment"

python3 -m venv .venv
. ./.venv/bin/activate
python3 -m pip install -r requirements.txt

echo "You are ready to go. Run python3 nest.py [INPUT]"