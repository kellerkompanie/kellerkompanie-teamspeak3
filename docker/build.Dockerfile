FROM debian:trixie-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    debhelper \
    devscripts \
    fakeroot \
    wget \
    bzip2 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create build directory
WORKDIR /build/keko-ts3

# Copy debian packaging files
COPY debian/ /build/keko-ts3/debian/

# Copy scripts (for import_legacy.py)
COPY scripts/ /build/keko-ts3/scripts/

# Set working directory for dpkg-buildpackage
WORKDIR /build/keko-ts3
