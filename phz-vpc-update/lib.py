import boto3
from botocore.exceptions import ClientError


def create_creds(role, region):
    sts_client = boto3.client("sts")
    # print(f"Assuming {role} in {region}")
    return sts_client.assume_role(RoleArn=role, RoleSessionName="AssumeRoute53")


def create_client(service, role, region):
    """Creates a BOTO3 client using the correct target accounts Role."""
    creds = create_creds(role, region)
    client = boto3.client(
        service,
        aws_access_key_id=creds["Credentials"]["AccessKeyId"],
        aws_secret_access_key=creds["Credentials"]["SecretAccessKey"],
        aws_session_token=creds["Credentials"]["SessionToken"],
        region_name=region,
    )
    return client


class PHZAssociation:
    def __init__(self, dns_hub_account, account=None):
        self.target_role_arn = (
            f"arn:aws:iam::{account}:role/AWSCloudFormationStackSetExecutionRole"
        )
        self.dns_hub_role_arn = f"arn:aws:iam::{dns_hub_account}:role/AWSCloudFormationStackSetExecutionRole"
        self.region = "eu-west-1"

        self._r53_client = None
        self._dns_hub_r53_client = None

    @property
    def r53_client(self):
        if self._r53_client is None:
            self._r53_client = create_client(
                "route53", self.target_role_arn, self.region
            )
        return self._r53_client

    @property
    def dns_hub_r53_client(self):
        if self._dns_hub_r53_client is None:
            self._dns_hub_r53_client = create_client(
                "route53", self.dns_hub_role_arn, self.region
            )
        return self._dns_hub_r53_client

    def _list_hosted_zones(self, dns_hub_vpc_ireland):
        response = self.dns_hub_r53_client.list_hosted_zones_by_vpc(
            VPCId=dns_hub_vpc_ireland, VPCRegion=self.region
        )["HostedZoneSummaries"]
        return response

    def _get_associated_vpc_list(self, hosted_zone_id):
        """Get the list of associated VPCs"""
        try:
            vpc_ids = []
            assoc_vpcs = self.r53_client.get_hosted_zone(
                Id=hosted_zone_id,
            )["VPCs"]
            for vpc_id in assoc_vpcs:
                vpc_ids.append(vpc_id["VPCId"])
            return vpc_ids
        except ClientError as e:
            print(f"An error occurred getting associated dns hub VPCs.\n Error: {e}")
            raise

    def _create_vpc_association(self, hosted_zone_id, dns_hub_vpc_id, region):
        response = self.r53_client.create_vpc_association_authorization(
            HostedZoneId=hosted_zone_id,
            VPC={
                "VPCId": dns_hub_vpc_id,
                "VPCRegion": region,
            },
        )
        return response

    def _associate_vpc_with_hosted_zone(self, hosted_zone_id, dns_hub_vpc_id, region):
        response = self.dns_hub_r53_client.associate_vpc_with_hosted_zone(
            HostedZoneId=hosted_zone_id,
            VPC={
                "VPCId": dns_hub_vpc_id,
                "VPCRegion": region,
            },
        )
        return response

    def _delete_vpc_association(self, hosted_zone_id, dns_hub_vpc_id, region):
        response = self.r53_client.delete_vpc_association_authorization(
            HostedZoneId=hosted_zone_id,
            VPC={
                "VPCId": dns_hub_vpc_id,
                "VPCRegion": region,
            },
        )
        return response

    def _apply_phz_dns_hub_association(
        self, hosted_zone_id, vpc_ids, dns_hub_vpc_id, region
    ):
        """
        Apply PHZ Id association to DNS Hub VPC for each enabled/active region
        """
        if dns_hub_vpc_id in vpc_ids:
            print(
                f"Sydney DNS Hub VPC is already associated with {hosted_zone_id} PHZ."
            )
        else:
            print("Associate Sydney VPC")
            # Step 1: Create the VPC association authorization
            try:
                self._create_vpc_association(hosted_zone_id, dns_hub_vpc_id, region)
                print(f"VPC Association Authorization created for: {hosted_zone_id}")
            except ClientError as e:
                print(
                    f"An error occurred creating VPC association authorization.\n Error: {e}"
                )
                raise

            # Step 2: Associate the regional DNS VPC with the PHZ
            print(f"Associating the {dns_hub_vpc_id} with PHZ: {hosted_zone_id}...")
            try:
                self._associate_vpc_with_hosted_zone(
                    hosted_zone_id, dns_hub_vpc_id, region
                )
                print(f"VPC associated with: {hosted_zone_id}")
            except Exception as e:
                print("Issue Associating the PHZ with the DNS")
                print(e)

            # Step 3: Delete the VPC association authorization
            print("Deleting VPC association authorization")
            try:
                self._delete_vpc_association(hosted_zone_id, dns_hub_vpc_id, region)
                print(f"VPC Association Authorization deleted for: {hosted_zone_id}")
            except ClientError as e:
                print(
                    f"An error occurred deleting VPC association authorization in {region}.\n Error: {e}"
                )
                raise
