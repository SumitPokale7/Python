#!/bin/bash

array=( "eu-west-1" "ap-northeast-2" "ap-south-1" "ap-southeast-1" "ap-southeast-2" "eu-central-1" "eu-north-1" "eu-west-2" "eu-west-3" "us-east-1" "us-east-2" "us-west-2" )
for i in "${array[@]}"
do
	echo "$i"
    SEARCH_REGION="$i" python remove_sc.py &
done