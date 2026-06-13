#!/usr/bin/env bash
# ============================================================
#  build_and_push.sh
#  Run this whenever requirements.txt or Dockerfile changes.
#  This is run from your dev machine (NOT the hospital laptops).
#  Usage:  bash scripts/build_and_push.sh <github-username>
# ============================================================
set -e

GITHUB_USER=${1:?"Usage: bash scripts/build_and_push.sh <github-username>"}
IMAGE="ghcr.io/${GITHUB_USER}/pocl-node"
TAG=$(git rev-parse --short HEAD)

echo "Building: ${IMAGE}:${TAG}"

# Build from repo root so COPY instructions work
docker build \
    -f docker/Dockerfile \
    -t "${IMAGE}:${TAG}" \
    -t "${IMAGE}:latest" \
    .

echo "Pushing to GitHub Container Registry..."
echo "  (Make sure you ran: echo YOUR_PAT | docker login ghcr.io -u ${GITHUB_USER} --password-stdin)"
docker push "${IMAGE}:${TAG}"
docker push "${IMAGE}:latest"

echo ""
echo "Done! Image pushed:"
echo "  ${IMAGE}:latest"
echo "  ${IMAGE}:${TAG}"
echo ""
echo "Hospital laptops will pull this on next pipeline run."