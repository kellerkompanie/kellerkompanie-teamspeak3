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

# Set working directory for dpkg-buildpackage
WORKDIR /build/keko-ts3
