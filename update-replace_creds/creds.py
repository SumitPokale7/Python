#!/usr/bin/env python3

import argparse
import os

def replace_default_values(filename, new_access_key_id, new_secret_access_key, aws_region, aws_profile):
    
    if not os.path.exists(filename):
        print(f"Error: File '{filename}' does not exist.")
        return
    
    with open(filename, 'r') as file:
        lines = file.readlines()

    with open(filename, 'w') as file:
        found_profile_section = False
        found_existing_profile = False
        for line in lines:
            if line.strip() == f'[{aws_profile}]':
                found_profile_section = True
                found_existing_profile = True
                file.write(line)
                continue
            elif found_profile_section:
                if line.strip().startswith('[') and line.strip().endswith(']'):
                    found_profile_section = False
                elif line.strip().startswith("aws_access_key_id"):
                    file.write(f'aws_access_key_id = {new_access_key_id}\n')
                elif line.strip().startswith("aws_secret_access_key"):
                    file.write(f'aws_secret_access_key = {new_secret_access_key}\n')
                elif line.strip().startswith("region"):
                    file.write(f'region = {aws_region}\n')
            file.write(line)
            
        if not found_existing_profile:
            file.write(f'\n[{aws_profile}]\n')
            file.write(f'aws_access_key_id = {new_access_key_id}\n')
            file.write(f'aws_secret_access_key = {new_secret_access_key}\n')
            file.write(f'region = {aws_region}\n')

def main():
    # Accepting CLI args
    parser = argparse.ArgumentParser()
    parser.add_argument("--aws-profile", help="", type=str, required=True)
    parser.add_argument("--access-key", help="", type=str, required=True)
    parser.add_argument("--secret-key", help="", type=str, required=True)
    parser.add_argument("--aws-region", help="", type=str, default="us-east-1")
    args = parser.parse_args()
    
    # Assigning args to internal variables
    aws_profile = args.aws_profile
    access_key  = args.access_key
    secret_key  = args.secret_key
    aws_region  = args.aws_region
    filename    = ''  # Add your Creds file path
    
    replace_default_values(filename, access_key, secret_key, aws_region, aws_profile)

if __name__ == "__main__":
    main()

# Command to Run Script 
# python3 creds.py --aws-profile Default --access-key *****  --secret-key *****
