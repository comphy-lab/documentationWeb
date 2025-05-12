#!/bin/zsh
# tested on MacOS only. Let us know if you find issues running with Linux by opening an issue. 
# modify using http://basilisk.fr/src/INSTALL 
# ensures that we are always using the latest version of basilisk

# Check if --hard flag is passed
HARD_RESET=false
if [[ "$1" == "--hard" ]]; then
    HARD_RESET=true
fi

# Function to install basilisk
install_basilisk() {
    darcs clone http://basilisk.fr/basilisk
    cd basilisk/src

    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Using MacOS"
        ln -s config.osx config
    else
        echo "Using Linux"
        ln -s config.gcc config
    fi
    make -k
    make
}

# Remove project config always
rm -rf .project_config

# Check if basilisk needs to be installed
if [[ "$HARD_RESET" == true ]] || [[ ! -d "basilisk" ]]; then
    echo "Installing basilisk..."
    rm -rf basilisk
    install_basilisk
else
    echo "Using existing basilisk installation..."
    cd basilisk/src
fi

# Setup environment variables
echo "export BASILISK=$PWD" >> ../../.project_config
echo "export PATH=\$PATH:\$BASILISK" >> ../../.project_config

source ../../.project_config

# Check if qcc is working properly
echo "\nChecking qcc installation..."
if ! qcc --version > /dev/null 2>&1; then
    echo "\033[0;31mError: qcc is not working properly.\033[0m"
    echo "Please ensure you have Xcode Command Line Tools installed."
    echo "You can install them by running: xcode-select --install"
    echo "For more details, visit: http://basilisk.fr/src/INSTALL"
    exit 1
else
    echo "\033[0;32mqcc is properly installed.\033[0m"
    qcc --version
fi

# Install Python dependencies needed for documentation generation
echo "\nInstalling Python dependencies for documentation..."
if command -v pip3 &> /dev/null; then
    if [ -f ".github/scripts/requirements.txt" ]; then
        pip3 install -r .github/scripts/requirements.txt
        echo "\033[0;32mPython dependencies installed successfully.\033[0m"
    else
        echo "\033[0;33mWarning: requirements.txt not found at .github/scripts/requirements.txt\033[0m"
    fi
else
    echo "\033[0;33mWarning: pip3 not found. Please install Python 3 and pip to use documentation features.\033[0m"
fi
