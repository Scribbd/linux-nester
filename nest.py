#!/bin/env python3

# LXC container generator for Linux Labs
# Steps in loop:
# - Gen SSH key
# - Start LXD container
# - Get into container
# - Runs commands to prep container for user
# - Add row of login data to csv

import argparse, yaml
import base64
from csv import DictReader, DictWriter
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa

import pylxd

parser = argparse.ArgumentParser(description="Linux Nester. Creates LXD containers for use with the Linux exercises of the TechGrounds Cloud Engineer.")
parser.add_argument('participant_file', type=argparse.FileType('r', encoding='UTF-8-sig'), help="Path to csv file with at least the following headers: First_Name,Last_Name,E_Mail.")
parser.add_argument('--mail', '-m', action='store_true', help="Include flag to also send emails to the participants.")
parser.add_argument('--output', '-o', action='store_true', help="Include flag to also output seperate keyfiles.")
parser.add_argument('--sshportstart', '-s', type=int, default=52200, help="Ports will be opened for ssh from the given value forward.")
parser.add_argument('--webportstart', '-w', type=int, default=58000, help="Ports will be opened for web from the given value forward.")

_network_name = "nestbr0"
_profile_name = "nestpr0"

def main(args):
    print("TG Linux Nester.")
    
    # Get Reader from inputfile
    csv_reader = DictReader(args.participant_file, delimiter=";")
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
            "ipv4.address": "10.0.0.1/24",
            "ipv4.nat": "true",
            "ipv6.address": "none"
        })
    
    # Create a Profile when none exists
    # instructs the usage of latest Ubuntu version with cloud-init support
    # and that it will network with the custom bridge network
    if client.profiles.exists(_profile_name):
        print(f"Profile '{_profile_name}' already exists. None added.")
    else:
        print(f"Creating instance profile '{_profile_name}'.")
        client.profiles.create(_profile_name, description="A profile for Nested Linux Labs", config={
                "source": {
                    "type": "image",
                    "alias": "ubuntu",
                    "server": "https://cloud-images.ubuntu.com/releases 1",
                }
            }, devices={
            "eth0": {
                "name": "eth0",
                "parent": _network_name,
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
    current_ssh = args.sshportstart
    current_web = args.webportstart
    for row in csv_reader:
        username = row["First_Name"].replace(" ", "_")
        container_name = "Nest_" + row["First_Name"][0:2].replace(" ", "_") + "_" + row["Last_Name"].replace(" ", "_")
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

        # Create container
        instance = client.instances.create({
            "name": container_name,
            "type": "container",
            "config.cloud-init.user-data": "#cloud-config\n" + yaml.dump({
                "users": [{
                    "name": username,
                    "ssh-authorized-keys": [
                        key.public_key().public_bytes(
                            crypto_serialization.Encoding.OpenSSH,
                            crypto_serialization.PublicFormat.OpenSSH
                        )],
                    "sudo": ["ALL=(ALL) NOPASSWD:ALL"],
                    "groups": "sudo",
                    "shell": "/bin/bash"
                }]
            }),
            "profiles": ["default", _profile_name]
        }, wait=True) # Wait is needed as other steps require an existing instancec

        output_rows.append({
            output_headers[0]: current_ssh, #sshport
            output_headers[1]: current_web, #webport
            output_headers[2]: username, #user
            output_headers[3]: base64.b64encode(private_key) #key64
        })
        
        if args.output:
            with open(f"output/{container_name}.pem", 'w', encoding='UTF8', newline='') as f:
                f.write(key.private_bytes(
                    crypto_serialization.Encoding.PEM,
                    crypto_serialization.PrivateFormat.TraditionalOpenSSL,
                    crypto_serialization.NoEncryption()
                ))
        
        current_ssh += 1
        current_web += 1
        

    with open("output/nested_list.csv", 'w', encoding='UTF8', newline='') as f:
        writer = DictWriter(f, fieldnames=output_headers)
        writer.writeheader(output_headers)
        writer.writerows(output_rows)

####
# Implementening network forward
####

def port_forward(client: pylxd.Client, instance: I):
    client.api.post()

if __name__ == "__main__":
    main(parser.parse_args())