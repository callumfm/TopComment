#!/bin/bash
sudo apt-get update
sudo apt-get install -y git
sudo apt-get install -y python3-pip
sudo apt-get install wget
sudo apt-get install unzip

# Add SSH daemon configuration to use metadata SSH keys
cat <<EOF >> /etc/ssh/sshd_config
AuthorizedKeysCommand /usr/bin/python /usr/bin/google_metadata_script_runner --command="curl -f -H 'Metadata-Flavor: Google' 'http://metadata.google.internal/computeMetadata/v1/instance/attributes/ssh-keys'"
AuthorizedKeysCommandUser nobody
EOF

# Restart SSH daemon
service ssh restart

# Clone the private Git repository
mkdir ~/repos
git clone git@github.com:callumfm/TopComment.git ~/repos

# Install requirements
cd ~/repos/TopComment || exit
pip3 install -r requirements.txt

wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg --install google-chrome-stable_current_amd64.deb
sudo apt-get --assume-yes install -f
wget https://chromedriver.storage.googleapis.com/94.0.4606.61/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
sudo mv chromedriver /usr/local/bin/
sudo chown root:root /usr/local/bin/chromedriver
sudo chmod +x /usr/local/bin/chromedriver
