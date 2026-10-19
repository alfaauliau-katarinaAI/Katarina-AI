"""Seal an explicitly supplied Actions secret for the owner's VPS; no plaintext artifact."""
import argparse
import os
from pathlib import Path
import re
import subprocess

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--public-key', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not re.fullmatch(r'[A-Za-z0-9_-]{20,256}', key):
        raise SystemExit('GEMINI_SECRET_NOT_CONFIGURED')
    try:
        result = subprocess.run(['openssl', 'pkeyutl', '-encrypt', '-pubin',
            '-inkey', a.public_key, '-pkeyopt', 'rsa_padding_mode:oaep',
            '-pkeyopt', 'rsa_oaep_md:sha256', '-pkeyopt', 'rsa_mgf1_md:sha256'],
            input=key.encode('ascii'), capture_output=True, timeout=15)
        if result.returncode != 0 or len(result.stdout) != 384:
            raise ValueError()
        output = Path(a.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(result.stdout)
    except Exception:
        raise SystemExit('GEMINI_SECRET_SEAL_FAILED') from None
    print('ENCRYPTED_GEMINI_CREDENTIAL_READY')

if __name__ == '__main__':
    main()
