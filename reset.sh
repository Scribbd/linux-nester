sudo snap remove --purge lxd
sudo snap install lxd
lxd init --auto
python3 nest.py ./input/example.csv -e -l 172.31.43.247