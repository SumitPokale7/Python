#!/bin/bash

# Define the list of SSM document names
documents=("bp-ssm-test-crossplatform-domainTag" "bp-ssm-test-crossplatform-domainTag")

# Iterate over the document names
for document in "${documents[@]}"; do
  # Execute the document
  execution=$(aws ssm start-automation-execution --document-name "$document" --query "AutomationExecutionId" --output text)
  echo "Started execution of $document. Execution ID: $execution"

  # Wait for the execution to complete
  aws ssm wait automation-execution-complete --automation-execution-id "$execution"
  echo "Execution of $document completed"
done

echo "All SSM documents executed successfully"
