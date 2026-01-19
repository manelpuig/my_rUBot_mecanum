#!/usr/bin/env bash
set -e

# Update apt cache (safe to run multiple times)
apt-get update

# Fix rosdep permissions (safe if already done)
rosdep fix-permissions || true

# Update rosdep database
rosdep update

exec "$@"