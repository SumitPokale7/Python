[H&S] Deploy NAT GWs in Zscaler Calgary account

## Overview

The template automates the following tasks:

- **NAT Gateways Creation**: Sets up NAT Gateways to enable instances in private subnets to initiate outbound traffic to the internet.
- **Route Configuration**: Configures routes in private subnet route tables to direct specific internal traffic through a Transit Gateway.

## Parameters

- `PublicSubnetId1`, `PublicSubnetId2`, `PublicSubnetId3`: The IDs of the public subnets where the NAT Gateways will be deployed.
- `PrivateRouteTableA`, `PrivateRouteTableB`, `PrivateRouteTableC`: The IDs of the private route tables to be associated with the NAT Gateways.
- `TransitGatewayId`: The ID of the Transit Gateway for routing internal AWS traffic.

### Resources Created

- **NAT Gateways**: Three NAT Gateways are created, each associated with a unique Elastic IP (EIP) address for public internet access.
- **Routes**: CNX routes are created.

### Outputs

- **NatGatewayPublicIp[1-3]**: Outputs the public IP addresses of the created NAT Gateways, providing easy access to these details for further configuration or monitoring.

## Stack Name

The naming convention for the stack should be WS-0xxx-NETWORK-STACK-NATGW

## Note

The stack name in the account WS-00KL(497523188783) is set to WS-00KL-NETWORK-LOCAL-EGRESS