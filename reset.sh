sudo snap remove --purge lxd
sudo snap install lxd
lxd init --auto
python3 nest.py ./example/input.csv -o -l