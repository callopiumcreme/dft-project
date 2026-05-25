#!/usr/bin/env bash
# Generate a dev self-signed PKCS#12 bundle used by the PDF signer service.
#
# Output:
#   data/signing/dev_cert.pem  — self-signed X.509 cert (PEM)
#   data/signing/dev_cert.key  — RSA-2048 private key (PEM)
#   data/signing/dev_cert.p12  — PKCS#12 bundle (cert + key), passphrase below
#
# WARNING: dev-only. data/signing/ is gitignored. NEVER commit the .p12
# or .key. Prod signing uses a real CA-issued cert handed off out-of-band.
#
# Usage:  scripts/gen_signing_cert.sh [PASSPHRASE]
# Default passphrase: dft-dev-signer (env: DFT_SIGNING_PASSPHRASE)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${REPO_ROOT}/data/signing"
PASSPHRASE="${1:-${DFT_SIGNING_PASSPHRASE:-dft-dev-signer}}"

SUBJECT="/C=CH/ST=Zug/L=Baar/O=OisteBio GmbH/OU=DFT Verifier/CN=DFT verifier (DEV)/emailAddress=compliance@oistebio.com"

mkdir -p "${OUT_DIR}"
cd "${OUT_DIR}"

# Self-signed cert + key in one shot (no CSR step needed for a dev cert).
openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
    -keyout dev_cert.key \
    -out dev_cert.pem \
    -subj "${SUBJECT}" \
    -addext "keyUsage=digitalSignature,nonRepudiation" \
    -addext "extendedKeyUsage=emailProtection,clientAuth" \
    2>/dev/null

# Bundle into PKCS#12 (pyhanko's SimpleSigner.load_pkcs12 reads this).
openssl pkcs12 -export \
    -inkey dev_cert.key \
    -in dev_cert.pem \
    -out dev_cert.p12 \
    -name "DFT verifier (DEV)" \
    -passout "pass:${PASSPHRASE}" \
    -legacy 2>/dev/null || \
openssl pkcs12 -export \
    -inkey dev_cert.key \
    -in dev_cert.pem \
    -out dev_cert.p12 \
    -name "DFT verifier (DEV)" \
    -passout "pass:${PASSPHRASE}"

chmod 600 dev_cert.key dev_cert.p12

echo "Generated:"
echo "  ${OUT_DIR}/dev_cert.pem"
echo "  ${OUT_DIR}/dev_cert.key  (chmod 600)"
echo "  ${OUT_DIR}/dev_cert.p12  (chmod 600, passphrase '${PASSPHRASE}')"
