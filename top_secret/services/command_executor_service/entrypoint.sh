#!/bin/bash

# Check if the SSH private key does not exist and generate a new key pair if needed
if [ ! -f /root/.ssh/id_rsa ]; then
    ssh-keygen -t rsa -b 4096 -f /root/.ssh/id_rsa -N ""
    echo "SSH key pair generated."
    # Optionally, output the public key and instruct the user to add it to the authorized_keys on the target server
    echo "Please add the following public key to the authorized_keys on the target server:"
    cat /root/.ssh/id_rsa.pub
fi

# Ensure proper permissions
chmod 600 /root/.ssh/id_rsa
chmod 644 /root/.ssh/id_rsa.pub

# Start the application
exec "$@"
