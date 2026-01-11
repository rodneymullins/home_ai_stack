#!/bin/bash
# Install HandBrake CLI on Gandalf
# Run this script on Gandalf to install HandBrake

echo "📦 Installing HandBrake CLI..."

# Ubuntu/Debian
if command -v apt-get &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y handbrake-cli ffmpeg
fi

# Check installation
if command -v HandBrakeCLI &> /dev/null; then
    echo "✅ HandBrake installed successfully!"
    HandBrakeCLI --version
else
    echo "❌ Installation failed"
fi
