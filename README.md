# Linux Nester
A solution for creating and configuring many LXD containers with a csv input.

The problem: Our participants are dependent on using a machine that can run a VM. In the past our participants were often overconfident about their own PC's capabilities. They would fall behind when they needed to get a loaner laptop.

Old solution: We would spin up *.nano instances for the participant that had troubles. This brought a few problems: Security, everyone shared the same access key. Or everyone would need it's own key bogging down the KMS service with ephimeral keys. And it was a general waste of resources as either the box was too small for larger experiments, or would be underutilized by our excersizes. 

This solution offers the following: Ability to use one large instance and share its resources amoungst many participant. Automate access key generation. Cheaper hosting as it will make allows for increased resource utilization.

## Goals
A way of providing a 'hosted' solution for simple Linux environments.
- Running a Linux 'simulation' in containers
- This solution should be able to run on any host that has the docker runtime
- Should be able to be approached through SSH
- Should be able to run ufw and other services

Achieved:
- Linux containers (LXC) are used instead of Docker containers. LXC is the technology that docker is based on.
- LXD is an abstraction layer that provides a REST API and a CLI tool that makes LXC administration a lot easier.
- This solution can run on any host that can install LXD and LXC.
- LXD has a builtin network forwarding tool that allows many ssh ports be active on the host, redirected to individual container instances.
- LXD containters are full Linux container with its own init and systemd processes. This allows for installing and running daemon tasks inside the containers.
- The containers are configured to be able to run Docker inside. However, this is not recommended.

## Requirements
- Ubuntu 20.04 or later
- A skew / instance type that can handle your container load.
- A roomy HD for the base install and the many containers you are going to use.

Recommended for a group of 15 (feel free to update):
- 4 vCPUs
- 4 GB of RAM
- 50 GB of gp3 storage

The current limitations set for each container:
- CPU limit: 2 threads
- Memory limit: 1GB
- Disk storage limit: 5GB

## Preparations
### Host networking
When using a cloud computer as your host make certain the following inbound ALLOW rules are applied to your (N)SG:

| Protocol | Port range    | Source    | Description                                         |
|----------|---------------|-----------|-----------------------------------------------------|
| TCP      | 22            | [Your IP] | Admin access to LXD host                            |
| TCP      | 52200 - 52299 | 0.0.0.0   | Forwarded ssh ports on host to LXD containers       |
| TCP      | 58000 - 58099 | 0.0.0.0   | Forwarded http / web ports on host to LXD container |

This table assumes you use the default port settings. Ranges can be shrunk or grown to fit the actual number of containers.

### Cloning
This repository is internal so you might need to login with a PAT.

When you have a PAT token for Github:
This you have to do yourself. First install `git`:
- `sudo apt update && sudo apt install git -y`
Then clone this repository.
- `git clone https://github.com/techgrounds/linux-nester.git`

If you don't want to use PATs you can also use VSCode. It will bring over your GitHub credentials to the remote or allow you to authenticate with the browser on your localhost.
- In VSCode install the following plugin: [Remote - SSH](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-ssh).
- Optional: When using key authentication add your key to your SSH-agent with `ssh-add` from [OpenSSH](https://winaero.com/enable-openssh-client-windows-10/).
- Then use `CTRL`+`SHIFT`+`P` to get the command pallet.
- Type `>Remote-SSH: Connect to Host...` autocomplete should also be able to pin it down with `SSH connect`.
- Use `ubuntu` as username, this is the default for Ubuntu images on AWS.
- Clone the repo!
- You can get into a remote terminal with `ctrl`+\` and install git if the options are greyed out.

### Install-script
You can run the following command to install the dependencies and activate a virtual environemnt ready for execution.
```sh
. ./install.sh
```

Make sure the following is installed on your host:
- Python3
- Python3-pip
- Python3-venv
- Snapd
- zfsutils-linux
- Through snap: LXD

## Usage
### Input
This program requires you to provide the following:
- A csv with the following headers: 'First_Name,Last_Name,E_Mail'

When not using the external IP, provide a local IP through the `-l` parameter.

The following command can be used for an example run when virtualenv is active:
`python3 nest.py input/example.csv --manual-address [localIP]`

Optional parameters:
| Name               | Flag | Default Value | Description                                                                                                                           |
|--------------------|------|---------------|---------------------------------------------------------------------------------------------------------------------------------------|
| --output           | -o   | True          | Write .pem keyfiles in the output folder                                                                                              |
| --package_output   | -p   | True          | Write the output .csv and optional keyfiles to an archive                                                                             |
| --package_format   | -f   | 'zip'         | Use shutil to archive the output folder. Choices are 'tar', 'zip', 'gztar', 'bztar', 'xztar'.                                         |
| --sshportstart     | -s   | 52200         | Starting port from which SSH ports are opened on the LXC host                                                                         |
| --webportstart     | -w   | 58000         | Starting port from which HTTP ports are opened on the LXC host                                                                        |
| --external_address | -e   | False         | When enabled it will grab the current external IP address from aws and use that is the listening address, overrides `--local_address` |
| --manual_address   | -m   | localhost     | Allows one to provide an IP address for debugging                                                                                     |
| --ubuntu_version   | -u   | focal         | Defaults to focal (20.04). Allows for a different Ubuntu version to be deployed                                                       |

### Base command
On AWS, you will most likely get the desired result with using the following command:
`python3 ./nest.py input/[file].csv`

If you use linux opt for a tar archive:
`python3 ./nest.py input/[file].csv -f tar`

If you wish to use the external IP:
`python3 ./nest.py input/[file].csv -e`

## Output
The `./output`-folder is used for all runs. In this a subfolder is generated for each individual run: `./output/Nest-{UNIX_timestamp}/`. Within this folder a `output.csv` file will contain the following:
    - `container_name`: Name of the container. `Nest-First_Name[0:2]-Last_Name`
    - `ssh_port`: The opened SSH port for this container instance
    - `web_port`: The opened Web port for this container instance
    - `user`: The username of the user on the linux container. This is the first name of the participant.
    - `e_mail`: Email address of the user, will be used in Nest-Mailer
    - `key64`: A base64 encoded private key for future reference.

Advise participants not to use this private key for anything other than this lab as this private key is known to us and should be assumed it has traveled the internet unencrypted.

By default a `key`-folder will be generated inside the `./output/Nest-{UNIX_timestamp}/`-folder that contains the access keys for the participants to login into their container instance. Keys are in `.pem` format and are named after their container names. This can be dissabled with the `--no_output/-o` flag.

By default the `./output/Nest-{UNIX_timestamp}/`-folder and subfolders will be compressed to a `.zip` archive and made available in the `./output`-folder with `Nest-{UNIX_timestamp}` as its name. The `-package_format\-f` allows one to change compresion methods. This can be dissabled with the `-no_package_output\-p` flag.

## Mailing the keys
There is a companion script over at [Nest-Mailer](https://github.com/Scribbd/nest-mailer/blob/main/input/example.csv) that uses the output CSV-file to send the keys to participants with connection information.

What you need is:
- The output CSV-file
- The IP of the listener `lxc network forward list nestbr0`

# Administration
This program uses LXC and LXD. LXD provides a comprehensive CLI tool for administrative functions for LXC. You can find an introduction [here](https://linuxcontainers.org/lxd/introduction/). A more comprehensive guide to all commands can be found [here](https://linuxcontainers.org/lxd/docs/master/).

## Troubleshooting
When you need to administer a specific container you can do the following:
- SSH into the LXD host
- Use `lxc list` to identify if the container is running
    - Should it have stopped you can use `lxc start [NAME]`
- If the problem started with a firewall blocking SSH traffic you can get root access with the following: `lxc exec [NAME] bash`
    - You are now root in the given container and can now fix the firewall issue.
- If no one is able to access the containers it might mean your public IP got reasigned.
    - Check current IP in the console
    - Use the following command `lxc network forward list nestbr0`
    - Check if this listener address is still the same
    - If not use the following command `lxc network forward edit nestbr0 [LISTENER_IP]`
    - Update the `listener_address:` line, save, and reload the daemon with `sudo snap restart lxd.daemon`
- If the container is beyond repair. 
    - Identify the container name from the `nested_list.csv`
    - Delete it with `lxc delete [name] --force`
    - From here on out you have two options:
        - Launch a new instance with the profiles:
            - All containers have their own profile available. They are named after the container like: `Test-Te-Tester-pr0`
            - You can use `lxc profile list` to see all profiles
            - Launch the container with `lxc launch images:ubuntu/20.04 [CONTAINER_NAME] -p default -p nestpr0 -p [CONTAINER_PROFILE_NAME]`
            - Get the current IP from the new container with `lxc list --columns "n4"`
            - Edit the forward configuration with `lxc network forward edit nestbr0 [HOST_IP]`
        - Run the nest.py program with a modified csv file that contains only the broken container.
            - Delete the port forwards to the system `lxc network forward port remove nestbr0 [HOST IP] 580xx` and `lxc network forward port remove nestbr0 [HOST_IP] 522xx`
            - Delete the profile of the container with `lxc profile delete [CONTAINER_PROFILE_NAME]`
            - Run nest.py with a modified file using the `-s` en `-w` flags on the old port numbers. `python3 nest.py input/[file].csv -s 522xx -w 580xx`
            - Send over the newly generated key to the participant
# End of life
A host that has outlived their stay should be removed as a whole. This script does not have an automated cleanup feature that enables recycling of hosts. Cattle not pets.
