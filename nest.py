#!/bin/env python3

# LXC container generator for Linux Labs
# Steps in loop:
# - Gen SSH key
# - Start LXD container
# - Add row of login data to csv
# - output keys / compress output

import argparse, yaml, os, base64, requests, shutil
from time import sleep, time
from csv import DictReader, DictWriter

# External libraries
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import pylxd, pylxd.models
import pylxd.models.instance as InstanceModel

parser = argparse.ArgumentParser(description="Linux Nester. Creates LXD containers for use with the Linux exercises of the TechGrounds Cloud Engineer.")
parser.add_argument('participant_file', type=argparse.FileType('r', encoding='UTF-8-sig'), help="Path to csv file with at least the following headers: First_Name,Last_Name,E_Mail.")
parser.add_argument('--output', '-o', action='store_true', help="Include flag to also output seperate keyfiles.")
parser.add_argument('--package_output', '-p', action='store_true', help="Include flag to compress all key files")
parser.add_argument('--package_format', '-f', type=str, choices=['tar', 'zip', 'gztar', 'bztar', 'xztar'], default='tar', help="Set archiving method. Uses shutil. Look at shutil documentation what the options are.")
parser.add_argument('--sshportstart', '-s', type=int, default=52200, help="Ports will be opened for ssh from the given value forward.")
parser.add_argument('--webportstart', '-w', type=int, default=58000, help="Ports will be opened for web from the given value forward.")
parser.add_argument('--external_address', '-e', action='store_true', help="Get external address and use that as listening address. Overides -l paramater")
parser.add_argument('--local_address', '-l', type=str, help="Specify when you are in a situation where the external IP for the listening address is not desirable.", default='localhost')
parser.add_argument('--ubuntu-version', '-u', type=str, default="focal", help="Version of Ubuntu the containers will use. Default to focal (20.04). Advised is hirsute or focal")

# Some hard coded options as I see this not changing.
_network_name = "nestbr0"
_profile_name = "nestpr0"
_first_name_cname = "First_Name" # Column name of First name data
_last_name_cname = "Last_Name" # Column name of Last Name data
_email_cname = "E_Mail" # Column name of Email data
_target_sshport = 22
_target_webport = 80

def main(args):
    print("TG Linux Nester.")
    
    # Get Reader from inputfile
    csv_reader = DictReader(args.participant_file, delimiter=",")
    # Prepare output environment and file variables
    timestamp = time()
    output_dir = f"output/nest_{timestamp}"
    keys_dir = f"{output_dir}/keys"
    # Create output dirs
    os.makedirs(output_dir)
    if args.output: os.makedirs(keys_dir)
    # Set output variables for DictWriter
    output_headers = ['container_name','ssh_port', 'web_port', 'user', 'e_mail', 'key64']
    output_rows = []

    # Init clients
    client = pylxd.Client()
    
    # Set listen address based on config
    listen_address = args.local_address
    if args.external_address:
        listen_address = requests.get('https://checkip.amazonaws.com').text.strip()
        print(f"Using external IP: {listen_address}")

    ### Setup network and profile for the Nested Linux Containers.
    print("Setting up lxd profiles.")
    # Create Network when none exists.
    # Network will use default settings with ipv4 and no ipv6
    if client.networks.exists(_network_name):
        print(f"Network profile '{_network_name}' found. None added.")
    else:
        print(f"Creating network profile '{_network_name}'")
        client.networks.create(_network_name, description="Nested Network for Linux Labs", type="bridge", config={
            "ipv4.address": "auto",
            "ipv4.nat": "true",
            "ipv6.address": "none",
        })
        # print(client.networks.get('nestbr0'))
        # Create forward system
        os.system(f"lxc network forward create {_network_name} {listen_address}") #TODO use pylxd api instead of CLI tool     
        # response = client.api.networks[_network_name].forwards.post(params={
        #     "forward": {
        #         "config": {},
        #         "description": "Test",
        #         "listen_address": listen_address,
        #         "ports": [
        #             {
        #                 "description": "",
        #                 "listen_port": "80",
        #                 "protocol": "tcp",
        #                 "target_address": "127.0.0.1",
        #                 "target_port": "80"
        #             }
        #         ]
        #     }
        # })
        # print(response)
    
    # Create a Profile when none exists
    # instructs the usage of latest Ubuntu version with cloud-init support
    # and that it will network with the custom bridge network
    if client.profiles.exists(_profile_name):
        print(f"Profile '{_profile_name}' already exists. None added.")
    else:
        print(f"Creating instance profile '{_profile_name}'.")
        client.profiles.create(_profile_name, config={
                "security.nesting": "true",
                "limits.memory": "1GB",
                "limits.memory.enforce": "soft",
                "limits.cpu": "2"
            }, devices={
            "eth0": {
                "name": "eth0",
                "network": _network_name,
                "type": "nic"
            },
            "root": {
                "path": "/",
                "pool": "default",
                "type": "disk",
                "size": "5GB"
            }
        })

    # Create the individual containers for each participant present in CSV
    print("Starting to create individual containers.")
    current_sshport = args.sshportstart
    current_webport = args.webportstart
    for row in csv_reader:
        username = row[_first_name_cname].replace(" ", "_").lower()
        container_name = "Nest-" + row[_first_name_cname][0:2].replace(" ", "-") + "-" + row[_last_name_cname].replace(" ", "-")
        print(f"Creating container: {container_name}")

        # Create SSH Key for participant
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        private_key = key.private_bytes(
            crypto_serialization.Encoding.PEM,
            crypto_serialization.PrivateFormat.TraditionalOpenSSL,
            crypto_serialization.NoEncryption()
        )

        user_data = "#cloud-config\n" + yaml.dump({
                "users": [{
                    "name": username,
                    "ssh-authorized-keys": [
                        key.public_key().public_bytes(
                            crypto_serialization.Encoding.OpenSSH,
                            crypto_serialization.PublicFormat.OpenSSH
                        ).decode('UTF-8')],
                    "sudo": ["ALL=(ALL) NOPASSWD:ALL"],
                    "groups": "sudo",
                    "shell": "/bin/bash"
                }]
            })
        # print(user_data)
        # Create container
        instance = client.instances.create({
            "name": container_name,
            "type": "container",
            "source": {
                "type": "image",
                "alias": args.ubuntu_version,
                "server": "https://cloud-images.ubuntu.com/releases",
                "protocol": "simplestreams",
            },
            "config": {
                "user.user-data": user_data
            },
            "profiles": ["default", _profile_name]
        }, wait=True) # Wait is needed as other steps require an existing instance
        instance.start(wait=True)
        # Create forwarding rules
        print("Setting up port forwards.")
        forward_port(client, listen_address, instance, _target_sshport, current_sshport)
        forward_port(client, listen_address, instance, _target_webport, current_webport)

        ### Create output ###
        output_rows.append({
            output_headers[0]: container_name, #container_name
            output_headers[1]: current_sshport, #ssh_port
            output_headers[2]: current_webport, #web_port
            output_headers[3]: username, #user
            output_headers[4]: row[_email_cname], #e_mail
            output_headers[5]: base64.b64encode(private_key).decode("UTF-8") #key64
        })

        if args.output:
            with open(f"{keys_dir}/{container_name}.pem", 'w', encoding='UTF8', newline='') as f:
                f.write(key.private_bytes(
                    crypto_serialization.Encoding.PEM,
                    crypto_serialization.PrivateFormat.TraditionalOpenSSL,
                    crypto_serialization.NoEncryption()
                ).decode('UTF-8'))

        current_sshport += 1
        current_webport += 1
        
    # Write output file for reference
    with open(f"{output_dir}/nested_list.csv", 'w', encoding='UTF-8', newline='') as f:
        writer = DictWriter(f, fieldnames=output_headers)
        writer.writeheader()
        writer.writerows(output_rows)

    # Compress output when flag is set for easy scp-ing
    if args.package_output:
        package = shutil.make_archive(f"output/Nest_{timestamp}", args.package_format, output_dir)
        print(f"Easily copy this out of your VM by using a tool like scp: 'scp {os.getlogin()}@{listen_address}:{package} .' Or use WinSCP.")

####
# Implementening network forward
####

def forward_port(client:pylxd.Client, listen_address:str, instance:InstanceModel.Instance, target_port:int, source_port:int):
    # Get ipv4 from current instance
    # Ipv4 takes a bit to get going it seems compared to Ipv6
    inet = []
    while not inet:
        address_state = instance.state().network['eth0']['addresses']
        inet = [dict_ for dict_ in address_state if dict_['family'] == "inet"]
        if not inet: sleep(1)
    
    # I cannot figure out how to use pylxd api to do this within the api.
    # client.api.post(path=f"/networks/{_network_name}/forwards", params={
    #     "listen_address": "0.0.0.0",
    #     "ports": [{
    #         "listen_port": source_port,
    #         "protocol": "tcp",
    #         "target_address": inet[0]['address'],
    #         "target_port": target_port
    #     }]
    # })

    # Using the cli tool for now. TODO find a way to us pyxld
    os.system(f"lxc network forward port add {_network_name} {listen_address} tcp {source_port} {inet[0]['address']} {target_port}")

if __name__ == "__main__":
    main(parser.parse_args())