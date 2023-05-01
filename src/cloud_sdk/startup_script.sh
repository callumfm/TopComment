#!/bin/bash
sudo apt-get update
sudo apt-get install -y git
sudo apt-get install -y python3-pip
sudo apt-get install wget
sudo apt-get install unzip
sudo apt install --fix-broken
sudo apt-get install python3 build-essential libssl-dev libffi-dev python-dev

# Install selenium and Chromedriver
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg --install google-chrome-stable_current_amd64.deb
sudo apt-get --assume-yes install -f
wget https://chromedriver.storage.googleapis.com/94.0.4606.61/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
sudo mv chromedriver /usr/local/bin/
sudo chown root:root /usr/local/bin/chromedriver
sudo chmod +x /usr/local/bin/chromedriver

# Clone the private Git repository
mkdir ~/TopComment
git clone https://github.com/callumfm/TopComment.git ~/TopComment

# Install requirements
cd ~/TopComment/src || exit
pip3 install --upgrade pip
pip3 install -r requirements.txt
