sudo snap remove --purge lxd
sudo snap install lxd
lxd init --auto
python3 nest.py ./input/example.csv -o -l 172.20.75.134 -p