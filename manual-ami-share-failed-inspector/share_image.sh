#!/bin/bash

echo "" > copy_image.log
regions=("eu-west-1" "us-east-2" "ap-southeast-1" "ap-southeast-2" "ap-south-1"  "eu-central-1" "eu-north-1" "eu-west-2" "eu-west-3" "us-east-1" "us-west-2")
source_ami="$1"
account_id="$2"
org_id=arn:aws:organizations::${account_id}:organization/o-1isru3nu35
os="$3"

for i in "${regions[@]}"; do
    echo "Sharing the Image is starting for ${i}..."
    # H3
    python3 main.py --ami-id ${source_ami} --mr-kms-key-arn "arn:aws:kms:${i}:${account_id}:key/mrk-18aaef2ce2224a2ab78041aa832c9e8e" --region ${i} --os ${os} --org-arn ${org_id} &
sleep 10
done
jobs
wait
Echo "Share image task is Finished...!!"

Echo "Unshare the core AMI and apply tags..!!"
#H3
python3 unshare.py --ami-id "${source_ami}" --mr-kms-key-arn "arn:aws:kms:eu-west-1:${account_id}:key/mrk-18aaef2ce2224a2ab78041aa832c9e8e" --region "eu-west-1" --os ${os} --org-arn "${org_id}"
Echo "Unshare image task is Finished...!!"
