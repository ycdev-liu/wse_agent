#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
RUNTIME_DIR="$ROOT_DIR/runtime/python"
BUILD_DIR="$ROOT_DIR/.python_build"

PYTHON_VERSION="3.12.7"
PYTHON_TGZ="Python-${PYTHON_VERSION}.tgz"
PYTHON_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/${PYTHON_TGZ}"

echo "[1/6] install build dependencies"

sudo apt update

sudo apt install -y \
    build-essential \
    wget \
    curl \
    libssl-dev \
    zlib1g-dev \
    libncurses5-dev \
    libncursesw5-dev \
    libreadline-dev \
    libsqlite3-dev \
    libgdbm-dev \
    libdb5.3-dev \
    libbz2-dev \
    libexpat1-dev \
    liblzma-dev \
    tk-dev \
    libffi-dev \
    uuid-dev

echo "[2/6] prepare directories"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
mkdir -p "$RUNTIME_DIR"

cd "$BUILD_DIR"

echo "[3/6] download Python ${PYTHON_VERSION}"

wget "$PYTHON_URL"

echo "[4/6] extract"

tar -xzf "$PYTHON_TGZ"

cd "Python-${PYTHON_VERSION}"

echo "[5/6] configure"

./configure \
    --prefix="$RUNTIME_DIR" \
    --enable-optimizations \
    --with-ensurepip=install

echo "[6/6] build"

make -j"$(nproc)"

make install

echo
echo "Python runtime ready:"
echo "$RUNTIME_DIR/bin/python3"

"$RUNTIME_DIR/bin/python3" --version
