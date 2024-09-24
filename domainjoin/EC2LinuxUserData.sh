#!/bin/bash

# Detect the Linux distribution
ARCH=$(uname -m)
if [ -f /etc/os-release ]; then
    source /etc/os-release
    if [ "$ID" == "sles" ]; then
        # For SLES use zypper package manager
        sudo zypper install -y https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/linux_amd64/amazon-ssm-agent.rpm
    elif [ "$ID" == "rhel" ]; then
          if [ "$ARCH" == "aarch64" ]; then
          sudo yum install -y https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/linux_arm64/amazon-ssm-agent.rpm
          else
          sudo yum install -y https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/linux_amd64/amazon-ssm-agent.rpm
          fi
    else
        echo "Unsupported Linux distribution: $ID"
        exit 1
    fi
else
    echo "Unable to detect the Linux distribution"
    exit 1
fi
# Setup debug logs
sudo cp /etc/amazon/ssm/seelog.xml.template /etc/amazon/ssm/seelog.xml
sudo sed -i 's/minlevel="info"/minlevel="debug"/' /etc/amazon/ssm/seelog.xml
# Start and enable the SSM Agent
systemctl start amazon-ssm-agent
systemctl enable amazon-ssm-agent

# Wait for the SSM Agent to be in 'Running' state
while [[ $(systemctl is-active amazon-ssm-agent) != "active" ]]; do
    sleep 5
done
# Get the instance ID and region dynamically
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)

# Run the AWS SSM command
aws ssm send-command \
    --document-name "AWS-UpdateSSMAgent" \
    --document-version "1" \
    --targets '[{"Key":"InstanceIds","Values":["'"$INSTANCE_ID"'"]}]' \
    --region "$REGION"