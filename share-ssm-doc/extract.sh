#!/bin/bash

# Define input and output file names
input_file="unshare-ssm-doc-logfile 2024-07-22 13_47_32.log"
output_file="extract.csv"
# Define the list of patterns to search for
patterns=(
    "BpPlatformServices_DomainJoinAutomation,"
    "BpPlatformServices_RHEL_DomainJoin,"
    "BpPlatformServices_SLES_DomainJoin,"
    "BpPlatformServices_Ubuntu_DomainJoin,"
    "BpPlatformServices_WIN_DomainJoin,"
)

# Clear the output file if it exists
> "$output_file"

# Loop through each pattern and search for matching lines
for pattern in "${patterns[@]}"; do
    grep "$pattern" "$input_file" >> "$output_file"
done

# Print a message indicating the script has finished
echo "Lines containing the pattern have been extracted to $output_file"
