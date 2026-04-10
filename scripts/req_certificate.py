#!/usr/bin/env python3
"""
Request SSH key and certificate from SJTU HPC API.

This script performs the following steps:
1. Authenticate with HPC API to get a bearer token
2. Generate SSH key pair using the token
3. Sign the public key to get SSH certificate

Usage:
    python req_certificate.py <username> <password> <output_path>

Arguments:
    username: HPC account username (operator)
    password: HPC account password
    output_path: Directory to save the SSH key and certificate files
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

API_BASE_URL = "https://api.hpc.sjtu.edu.cn"


def request_token(operator: str, password: str) -> str:
    """Request bearer token from HPC API."""
    url = f"{API_BASE_URL}/token"
    payload = {
        "domain": "pi",
        "operator": operator,
        "password": password
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "text/plain"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as response:
            token = response.read().decode("utf-8")
            # Token format is "Bearer ..."
            if token.startswith("Bearer "):
                token = token[7:]
            return token
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        raise Exception(f"Failed to get token: {e.code} - {error_msg}")


def generate_key_pair(token: str, hpc_user: str) -> dict:
    """Generate SSH key pair using HPC API."""
    url = f"{API_BASE_URL}/gen_key"
    payload = {
        "domain": "pi",
        "hpc_user": hpc_user
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        raise Exception(f"Failed to generate key pair: {e.code} - {error_msg}")


def sign_cert(token: str, hpc_user: str, public_key: str, valid_time: int = 3600) -> str:
    """Sign SSH public key to get certificate."""
    url = f"{API_BASE_URL}/sign_cert"
    payload = {
        "domain": "pi",
        "hpc_user": hpc_user,
        "principals": [hpc_user],
        "public_key": public_key,
        "valid_time": valid_time
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "text/plain",
            "Authorization": f"Bearer {token}"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as response:
            cert = response.read().decode("utf-8")
            return cert
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        raise Exception(f"Failed to sign certificate: {e.code} - {error_msg}")


def save_files(output_path: str, private_key: str, public_key: str, certificate: str):
    """Save SSH key and certificate to files."""
    os.makedirs(output_path, exist_ok=True)

    # API always returns Ed25519 keys
    key_name = "id_ed25519"

    private_key_path = os.path.join(output_path, key_name)
    public_key_path = os.path.join(output_path, f"{key_name}.pub")
    cert_path = os.path.join(output_path, f"{key_name}-cert.pub")

    # Save private key
    with open(private_key_path, "w") as f:
        f.write(private_key)
    os.chmod(private_key_path, 0o600)

    # Save public key
    with open(public_key_path, "w") as f:
        f.write(public_key)

    # Save certificate
    with open(cert_path, "w") as f:
        f.write(certificate)

    print(f"SSH key and certificate saved to {output_path}:")
    print(f"  - Private key: {private_key_path}")
    print(f"  - Public key: {public_key_path}")
    print(f"  - Certificate: {cert_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Request SSH key and certificate from SJTU HPC API"
    )
    parser.add_argument("username", help="HPC account username (operator)")
    parser.add_argument("password", help="HPC account password")
    parser.add_argument("output_path", help="Directory to save SSH key and certificate")
    parser.add_argument(
        "--valid-time",
        type=int,
        default=3600,
        help="Certificate validity time in seconds (default: 3600)"
    )

    args = parser.parse_args()

    print(f"Requesting SSH certificate for user: {args.username}")
    print("Step 1: Authenticating to get bearer token...")

    try:
        # Step 1: Get token
        token = request_token(args.username, args.password)
        print("  Token obtained successfully.")

        # Step 2: Generate key pair
        print("Step 2: Generating SSH key pair...")
        key_pair = generate_key_pair(token, args.username)
        private_key = key_pair["private_key"]
        public_key = key_pair["public_key"]
        print("  Key pair generated successfully.")

        # Step 3: Sign certificate
        print("Step 3: Signing SSH certificate...")
        print("  Note: This step requires two-factor authentication.")
        print("  Please complete the authorization via JWB app or Email.")
        certificate = sign_cert(
            token,
            args.username,
            public_key,
            args.valid_time
        )
        print("  Certificate signed successfully.")

        # Step 4: Save files
        print("Step 4: Saving files...")
        save_files(args.output_path, private_key, public_key, certificate)

        print("\nDone! You can now SSH to HPC entry nodes using:")
        print(f"  ssh -i {args.output_path}/{os.listdir(args.output_path)[0].replace('.pub', '')} user@entry_node")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()