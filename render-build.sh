#!/usr/bin/env bash
set -e

STORAGE_DIR=/opt/render/project/.render

# Install dependencies
apt-get update
apt-get install -y wget ca-certificates unzip

# Download and install Google Chrome
if [[ ! -d $STORAGE_DIR/chrome ]]; then
  echo "...Downloading Chrome"
  mkdir -p $STORAGE_DIR/chrome
  cd $STORAGE_DIR/chrome
  wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  dpkg -x google-chrome-stable_current_amd64.deb $STORAGE_DIR/chrome
  rm google-chrome-stable_current_amd64.deb
else
  echo "...Using cached Chrome"
fi

# Download and install ChromeDriver
if [[ ! -f $STORAGE_DIR/chromedriver/chromedriver ]]; then
  echo "...Downloading Chromedriver"
  mkdir -p $STORAGE_DIR/chromedriver
  cd $STORAGE_DIR/chromedriver
  wget -q https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip
  unzip chromedriver_linux64.zip
  rm chromedriver_linux64.zip
else
  echo "...Using cached Chromedriver"
fi

# Clean up
apt-get clean

# Add Chrome to PATH
echo "export PATH=\$PATH:$STORAGE_DIR/chrome/opt/google/chrome" > /etc/profile.d/chrome.sh
