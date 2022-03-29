# Linux Nester
A solution for creating and configuring many LXC containers with a csv input.

The problem: Our participants are dependent on using a machine that can run a VM. In the past our participants were often overconfident about their own PC's capabilities. They would fall behind when they needed to get a loaner laptop.

Old solution: We would spin up *.nano instances for the participant that had troubles. This brought a few problems: Security, everyone shared the same access key. Or everyone would need it's own key bogging down the KMS service with ephimeral keys. And it was a general waste of resources as either the box was too small for larger experiments, or would be underutilized by our excersizes. 

This solution offers the following: Ability to use one large instance and share its resources amoungst many participant. Automate access key generation. Cheaper hosting as it will make

## Goals
A way of providing a 'hosted' solution for simple Linux environment.
- Running a Linux 'simulation' in containers
- This solution should be able to run on any host that has the docker runtime
- Should be able to be approached through SSH
- Should be able to run ufw and other services

Achieved:
- Linux containers (LXC) are used instead of Docker containers. LXC is the technology that docker is based on.
- This solution can run on any host that can install LXD and LXC
- LXD has a builtin network forwarding tool that allows many ssh ports be active on the host, redirected to individual container instances.
- LXC is a full Linux container with its own init and systemd process. This allows for installing and running daemon tasks.

## Usage
### Preparations
Make sure the following is installed on your host:
- Python3
- Python3-pip
- Python3-venv
- Snapd
- zfsutils-linux
- Through snap: LXD

You can run the following command to install the dependencies and activate a virtual environemnt ready for execution.
```sh
. ./install.sh
```

### Host networking
When using a cloud computer as your host make certain the following inbound rules are applied to your (N)SG:

| Protocol | Port range    | Source    | Description                                         |
|----------|---------------|-----------|-----------------------------------------------------|
| TCP      | 22            | [Your IP] | Admin access to LXC host                            |
| TCP      | 52200 - 52299 | 0.0.0.0   | Forwarded ssh ports on host to LXC containers       |
| TCP      | 58000 - 58099 | 0.0.0.0   | Forwarded http / web ports on host to LXC container |

This table assumes you use the default port settings. Ranges can be shrunk or grown to fit the actual number of containers.

### Input
This program requires you to provide the following:
- A csv with the following headers: 'First_Name,Last_Name,~~E_Mail~~'
Note: `E_Mail` is not used for anything for now.
When not using the external IP, provide a local IP through the `-l` parameter.

The following command can be used for an example run when virtualenv is active:
`python3 nest.py input/example.csv -o -l [localIP]`

Optional parameters:
| Name               | Flag | Default Value | Description                                                                                                                       |
|--------------------|------|---------------|-----------------------------------------------------------------------------------------------------------------------------------|
| --output           | -o   | False         | Write .pem keyfiles in the output folder                                                                                          |
| --package_output   | -p   | False         | Write the output .csv and optional keyfiles to an archive                                                                         |
| --package_format   | -f   | 'tar'         | Use shutil to archive the output folder. Choices are 'tar', 'zip', 'gztar', 'bztar', 'xztar'.                                     |
| --sshportstart     | -s   | 52200         | Starting port from which SSH ports are opened on the LXC host                                                                     |
| --webportstart     | -w   | 58000         | Starting port from which HTTP ports are opened on the LXC host                                                                    |
| --external_address | -e   | False         | When enabled it will grab the current external IP address from aws and use that is the listening address, overrides `--localhost` |
| --local_address    | -l   | localhost     | Allows one to provide an IP address for debuggin                                                                                  |
| --ubuntu_version   | -u   | focal         | Defaults to focal (20.04). Allows for a different Ubuntu version to be deployed                                                   |

### Base command
You will most likely get the desired result with using the following command:
`python3 ./nest.py input/[file].csv -o -p -e`

### Output
The `./output`-folder is used for all runs. In this a subfolder is generated for each individual run: `./output/Nest-{UNIX_timestamp}/`. Within this folder a `output.csv` file will contain the following:
    - `container_name`: Name of the container. `Nest-First_Name[0:2]-Last_Name`
    - `ssh_port`: The opened SSH port for this container instance
    - `web_port`: The opened Web port for this container instance
    - `user`: The username of the user on the linux container. This is the first name of the participant.
    - `key64`: A base64 encoded private key for future reference.

Advice participants not to use this private key for anything other than this lab as its private key is known to us and assume it has traveled the internet unencrypted. 

When the `--output/-o` flag is present, a `key`-folder will be generated inside the `./output/Nest-{UNIX_timestamp}/`-folder that contains the access keys for the participants to login into their container instance. Keys are in `.pem` format and are named after their container names.

When the `-package_output\-p` flag is present, the `./output/Nest-{UNIX_timestamp}/`-folder and subfolders will be compressed to a `.tar` file and made available in the `./output`-folder with `Nest-{UNIX_timestamp}` as its name. The `-package_format\-f` allows one to change compresion methods. Default is a non-compression tar archive.

# Administration
This program uses LXC and LXD. LXD provides a comprehensive CLI tool for administrative functions. 

## Enter container

# End of life
A host that have outlived their stay should be removed as a whole. This script does not have an automated cleanup feature that allows recycling of hosts.