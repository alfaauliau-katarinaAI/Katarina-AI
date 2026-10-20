"""Transfer only an RSA-OAEP encrypted HF credential to the owner's existing VPS key."""
import base64,hashlib,os,subprocess
from pathlib import Path
def main():
    token=os.environ.get('HF_TOKEN','').strip()
    if not token or not token.startswith('hf_') or len(token)>318:
        raise SystemExit('HF_TOKEN_MISSING_OR_INVALID')
    key=Path('ops/credentials/katarina-gemini-transfer-public.pem')
    fingerprint=hashlib.sha256(key.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
    if fingerprint!='a99dde3e2a1f2bcded5db3b6ecffd77096773d13508aede36673ef708e6409f4':
        raise SystemExit('VPS_PUBLIC_KEY_MISMATCH')
    result=subprocess.run(['openssl','pkeyutl','-encrypt','-pubin','-inkey',str(key),
        '-pkeyopt','rsa_padding_mode:oaep','-pkeyopt','rsa_oaep_md:sha256',
        '-pkeyopt','rsa_mgf1_md:sha256'],input=token.encode('ascii'),capture_output=True,timeout=20)
    if result.returncode or len(result.stdout)!=384:
        raise SystemExit('HF_ENCRYPTION_FAILED')
    print('HF_RSA_OAEP_SHA256:'+base64.b64encode(result.stdout).decode('ascii'))
    print('HF_CREDENTIAL_SEALED_FOR_OWNER_VPS')
if __name__=='__main__':main()
