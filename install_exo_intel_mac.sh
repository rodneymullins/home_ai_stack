#!/bin/bash
# Exo Installation Script for Intel MacBook Pro
# Run this on your 2019 Intel Mac

set -e  # Exit on error

echo "🚀 Installing Exo on Intel MacBook Pro..."
echo ""

# Step 1: Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "📦 Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "✓ Homebrew already installed"
fi

# Step 2: Install dependencies
echo ""
echo "📦 Installing dependencies (uv, node)..."
brew install uv node

# Step 3: Install Rust
if ! command -v rustc &> /dev/null; then
    echo ""
    echo "📦 Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source $HOME/.cargo/env
else
    echo "✓ Rust already installed"
fi

# Install nightly toolchain
echo "📦 Installing Rust nightly..."
rustup toolchain install nightly

# Step 4: Clone Exo repository
echo ""
echo "📥 Cloning Exo repository..."
cd $HOME
if [ -d "exo" ]; then
    echo "⚠️  exo directory already exists. Removing..."
    rm -rf exo
fi
git clone https://github.com/exo-explore/exo

# Step 5: Checkout matching version
echo ""
echo "🔖 Checking out v1.0.60-alpha.1..."
cd exo
git checkout v1.0.60-alpha.1

# Step 6: Build dashboard
echo ""
echo "🏗️  Building dashboard..."
cd dashboard
npm install
npm run build
cd ..

echo ""
echo "✅ Installation complete!"
echo ""
echo "To start Exo, run:"
echo "  cd ~/exo"
echo "  uv run exo"
echo ""
echo "Dashboard will be available at: http://localhost:52415"
echo ""
