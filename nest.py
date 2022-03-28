#!/bin/env python3

# LXC container generator for Linux Labs
# Steps in loop:
# - Gen SSH key
# - Start LXD container
# - Get into container
# - Runs commands to prep container for user
# - Add row of login data to csv

import argparse, yaml, os, base64
from time import sleep
from csv import DictReader, DictWriter
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa

import pylxd
import pylxd.models.instance as InstanceModel

parser = argparse.ArgumentParser(description="Linux Nester. Creates LXD containers for use with the Linux exercises of the TechGrounds Cloud Engineer.")
parser.add_argument('participant_file', type=argparse.FileType('r', encoding='UTF-8-sig'), help="Path to csv file with at least the following headers: First_Name,Last_Name,E_Mail.")
parser.add_argument('--mail', '-m', action='store_true', help="Include flag to also send emails to the participants.")
parser.add_argument('--output', '-o', action='store_true', help="Include flag to also output seperate keyfiles.")
parser.add_argument('--sshportstart', '-s', type=int, default=52200, help="Ports will be opened for ssh from the given value forward.")
parser.add_argument('--webportstart', '-w', type=int, default=58000, help="Ports will be opened for web from the given value forward.")

_network_name = "nestbr0"
_listen_address = "127.0.0.1"
_profile_name = "nestpr0"
_first_name_cname = "First_Name"
_last_name_cname = "Last_Name"
_ubuntu_version = "hirsute"
_target_sshport = 22
_target_webport = 80

def main(args):
    print("TG Linux Nester.")
    
    # Get Reader from inputfile
    csv_reader = DictReader(args.participant_file, delimiter=",")
    # Prepare output file
    output_headers = ['ssh_port', 'web_port', 'user', 'key64']
    output_rows = []

    client = pylxd.Client()
    
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
            "ipv6.address": "none"
        })
        print(client.networks.get('nestbr0'))
        os.system(f"lxc network forward create {_network_name} {_listen_address}")
    
    # Create a Profile when none exists
    # instructs the usage of latest Ubuntu version with cloud-init support
    # and that it will network with the custom bridge network
    if client.profiles.exists(_profile_name):
        print(f"Profile '{_profile_name}' already exists. None added.")
    else:
        print(f"Creating instance profile '{_profile_name}'.")
        client.profiles.create(_profile_name, config={}, devices={
            "eth0": {
                "name": "eth0",
                "network": _network_name,
                "type": "nic"
            },
            "root": {
                "path": "/",
                "pool": "default",
                "type": "disk"
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
        print(user_data)
        # Create container
        instance = client.instances.create({
            "name": container_name,
            "type": "container",
            "source": {
                "type": "image",
                "alias": _ubuntu_version,
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
        forward_port(client, instance, _target_sshport, current_sshport)
        forward_port(client, instance, _target_webport, current_webport)

        ### Create output ###
        output_rows.append({
            output_headers[0]: current_sshport, #sshport
            output_headers[1]: current_webport, #webport
            output_headers[2]: username, #user
            output_headers[3]: base64.b64encode(private_key).decode("UTF-8") #key64
        })

        if args.output:
            with open(f"output/{container_name}.pem", 'w', encoding='UTF8', newline='') as f:
                f.write(key.private_bytes(
                    crypto_serialization.Encoding.PEM,
                    crypto_serialization.PrivateFormat.TraditionalOpenSSL,
                    crypto_serialization.NoEncryption()
                ).decode('UTF-8'))

        current_sshport += 1
        current_webport += 1
        
    # Write output file for reference
    with open("output/nested_list.csv", 'w', encoding='UTF-8', newline='') as f:
        writer = DictWriter(f, fieldnames=output_headers)
        writer.writeheader()
        writer.writerows(output_rows)

####
# Implementening network forward
####

def forward_port(client: pylxd.Client, instance:InstanceModel.Instance, target_port:int, source_port:int):
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

    os.system(f"lxc network forward port add {_network_name} {_listen_address} tcp {source_port} {inet[0]['address']} {target_port}")

if __name__ == "__main__":
    main(parser.parse_args())