#!/bin/bash
 
echo "🚀 Installing CIP Agent..."
 
# Install dependencies
sudo apt update -y
sudo apt install python3-pip -y
 
pip3 install psutil requests
 
# Create folder
mkdir -p ~/cip
 
# Copy agent
cat <<EOF > ~/cip/cip_agent.py
<PASTE cip_agent.py CONTENT HERE>
EOF
 
# Create systemd service
sudo cp cip.service /etc/systemd/system/cip.service
 
# Reload + enable
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable cip
sudo systemctl start cip
 
echo "✅ CIP Agent Installed & Running"