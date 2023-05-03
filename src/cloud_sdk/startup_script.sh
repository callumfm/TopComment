#!/bin/bash
sudo apt-get update && sudo apt-get upgrade
sudo apt-get install -y git
sudo apt-get install -y python3-pip
sudo apt-get install wget
sudo apt-get install unzip
sudo apt install --fix-broken
sudo apt-get install python3 build-essential libssl-dev libffi-dev python-dev

# Disable cert refreshes
sudo sh -c 'echo "CLOUDSDK_CERT_REFRESH_DISABLE=1" >> /etc/environment'

# Set timezone
sudo timedatectl set-timezone Europe/London

# Install selenium and Chromedriver
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg --install google-chrome-stable_current_amd64.deb
sudo apt-get --assume-yes install -f
wget https://chromedriver.storage.googleapis.com/112.0.5615.49/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
sudo mv chromedriver /usr/local/bin/
sudo chown root:root /usr/local/bin/chromedriver
sudo chmod +x /usr/local/bin/chromedriver

# Clone the repo and install requirements
mkdir /TopComment
git clone https://github.com/callumfm/TopComment.git /TopComment
cd /TopComment/src || exit
pip3 install --upgrade pip
pip3 install -r requirements.txt

mv /TopComment /usr/local/
find /usr/local/TopComment -type d -exec chmod 777 {} \;
find /usr/local/TopComment -type f -exec chmod 777 {} \;
echo "Setup complete"
