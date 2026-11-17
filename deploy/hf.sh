#!/usr/bin/env bash
# Deploy SIDAMA's public site to Hugging Face Spaces — free, no credit card.
#
# 1. Create a free account at https://huggingface.co/join (email only, no card)
# 2. Create a write token at https://huggingface.co/settings/tokens (role: write)
# 3. Create an empty Space: https://huggingface.co/new-space
#      SDK: Docker   ·   Blank template   ·   visibility: Public
# 4. Run this script:
#      HF_TOKEN=hf_xxxxxxxx ./deploy/hf.sh <hf-username> [space-name]
#
# The Space builds the Dockerfile from the `hf` branch and serves the public
# transparency site on https://<hf-username>-<space-name>.hf.space
set -euo pipefail

: "${HF_TOKEN:?Set HF_TOKEN first (write token from https://huggingface.co/settings/tokens)}"
HF_USER="${1:?Usage: HF_TOKEN=... ./deploy/hf.sh <hf-username> [space-name]}"
SPACE="${2:-sidama}"

echo "→ pushing branch 'hf' to huggingface.co/spaces/${HF_USER}/${SPACE}"
git push "https://${HF_USER}:${HF_TOKEN}@huggingface.co/spaces/${HF_USER}/${SPACE}" hf:main

echo "→ selesai. Space akan build otomatis (±3–5 menit)."
echo "   URL: https://${HF_USER}-${SPACE}.hf.space"
