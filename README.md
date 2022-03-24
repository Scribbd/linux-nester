# Linux Nester
A solution for running many Linux containers on a single host for our participants.

The problem: Our participants are dependent on using a machine that can run a VM. In the past our participants were often overconfident about their own PC's capabilities. They would fall behind when they needed to get a loaner laptop.

## Goals
A way of providing a 'hosted' solution for simple Linux CLI
- Running a Linux 'simulation' in containers
- This solution should be able to run on any host that has the docker runtime
- Should be able to be approached through SSH
- Should be able to run ufw and other services

## Usage
### Preparations
Make sure the following is installed on your host:
- Python3
- Python3-venv
- LXD

You can run the following command to install the dependencies and activate venv.
```sh
chmod +x ./install.sh
./install.sh
```

### Input
This program requires you to provide the following:
- A csv with the following headers: 'First_Name,Last_Name,E_Mail'

Optional flags:
- `-m / --mail` mail private keys to participants using the E_Mail 
- `-o / --output` output SSH-keys to files in `./output/`

### Output
The following output will be generated:
- CSV file with the following
    - `ssh_port`:
    - `web_port`:
    - `user`:
    - `key64`: