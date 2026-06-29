# filepath: .devcontainer/Dockerfile
FROM golang:1.18

# Install any additional tools you need here
RUN apt-get update && apt-get install -y \
    git \
    libi2c-dev \
    i2c-tools \    
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /workspace

# Copy the current project to the container
COPY . /workspace