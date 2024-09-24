import fire
import boto3


class IMDDSSettings(object):
    def __init__(self):
        self.client = boto3.client('ec2')

    def set_defaults(self, region):
        client = boto3.client('ec2', region_name=region)
        client.modify_instance_metadata_defaults(
            HttpTokens="required",
            HttpEndpoint="enabled",
            HttpPutResponseHopLimit=2
        )
        return self.fetch_defaults(region)

    def fetch_defaults(self, region):
        client = boto3.client('ec2', region_name=region)
        response = client.get_instance_metadata_defaults()["AccountLevel"]
        return response


if __name__ == '__main__':
    settings = IMDDSSettings()
    fire.Fire(settings)
