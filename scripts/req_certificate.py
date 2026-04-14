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


class APIError(Exception):
    """Base exception for API errors."""
    def __init__(self, message: str, http_code: int):
        super().__init__(message)
        self.http_code = http_code


def parse_error_response(e: urllib.error.HTTPError) -> tuple[str, bool]:
    """
    Parse error response from API.
    Returns (error_message, is_internal_error).
    - HTTP 500: internal error, body contains session ID and help info
    - Other codes: rejection, body contains reason
    """
    body = e.read().decode("utf-8")
    http_code = e.code
    return body, http_code == 500


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
        error_body, is_internal = parse_error_response(e)
        if is_internal:
            raise APIError(
                f"获取Token失败: {error_body}",
                e.code
            )
        else:
            raise APIError(
                f"获取Token被拒绝: {error_body}",
                e.code
            )


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
        error_body, is_internal = parse_error_response(e)
        if is_internal:
            raise APIError(
                f"生成密钥对失败: {error_body}",
                e.code
            )
        else:
            raise APIError(
                f"生成密钥对被拒绝: {error_body}",
                e.code
            )


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
        error_body, is_internal = parse_error_response(e)
        if is_internal:
            raise APIError(
                f"签名证书失败: {error_body}",
                e.code
            )
        else:
            raise APIError(
                f"签名证书被拒绝: {error_body}",
                e.code
            )


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

    try:
        # Step 1: Get token
        token = request_token(args.username, args.password)

        # Step 2: Generate key pair
        key_pair = generate_key_pair(token, args.username)
        private_key = key_pair["private_key"]
        public_key = key_pair["public_key"]

        # Step 3: Sign certificate
        certificate = sign_cert(
            token,
            args.username,
            public_key,
            args.valid_time
        )

        # Step 4: Save files
        save_files(args.output_path, private_key, public_key, certificate)

        print(f"Done! SSH key and certificate have been stored into {args.output_path}")

    except APIError as e:
        print(f"{e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"未知错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()