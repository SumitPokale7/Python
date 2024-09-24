import time

from botocore.exceptions import ClientError
import logging
import botocore.exceptions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


LONG_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
WAITING_SECONDS = 2


def extract_ce_resources(all_args):
    ce_name, _region, resources_client = all_args

    result = []
    try:
        if resources_client:
            paginator = resources_client.get_paginator("get_resources")
            response_iterator = paginator.paginate(
                TagFilters=[{"Key": "cloud-environment", "Values": [ce_name]}]
            )

            for response in response_iterator:
                for resource in response["ResourceTagMappingList"]:
                    result.append(
                        {
                            "ce_name": ce_name,
                            "resource": resource["ResourceARN"],
                            "region": _region,
                        }
                    )
            return result
        else:
            return []

    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role for {ce_name} because of {err}"
            )
            return []
        elif err.response["Error"]["Code"] == "InvalidClientTokenId":
            logger.error(
                f"the security token included in the request is invalid {err} "
                f"for account id {ce_name} and region {_region}"
            )
            return []
        else:
            logger.error(f"{err} " f"for account id {ce_name} and region {_region}")
            raise err
    except Exception as ex:
        logger.error(f"{ex} " f"for account id {ce_name} and region {_region}")
        raise ex


def extract_ses_verified_identities(all_args):
    _account_id, _region, ses_client = all_args
    result = []
    try:
        if ses_client:
            paginator = ses_client.get_paginator("list_identities")
            response_iterator = paginator.paginate()

            for response in response_iterator:
                for identity in response["Identities"]:
                    result.append(
                        {
                            "identity": identity,
                            "account_id": _account_id,
                            "region": _region,
                        }
                    )

            return result
        else:
            return []

    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.error(
                f"cannot assume the role for the role because of {err} "
                f"for account id {_account_id} and region {_region}"
            )
            return []
        elif err.response["Error"]["Code"] == "InvalidClientTokenId":
            logger.error(
                f"the security token included in the request is invalid {err} "
                f"for account id {_account_id} and region {_region}"
            )
            return []
        else:
            logger.error(f"{err} " f"for account id {_account_id} and region {_region}")
            raise err
    except Exception as ex:
        if isinstance(ex, botocore.exceptions.EndpointConnectionError):
            logger.error(f"{ex} " f"for account id {_account_id} and region {_region}")
            raise ex
        else:
            logger.error(f"{ex} " f"for account id {_account_id} and region {_region}")
            raise ex


def extract_ami_ebs_block_public_access(all_args):
    try:
        _account_id, _region, ec2_client = all_args
        if ec2_client:
            response_ami = ec2_client.get_image_block_public_access_state()
            response_ebs = ec2_client.get_ebs_encryption_by_default()
            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "AMI_block_public_access": response_ami[
                        "ImageBlockPublicAccessState"
                    ],
                    "EBS_encryption_by_default": response_ebs["EbsEncryptionByDefault"],
                }
            ]
        else:
            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "AMI_block_public_access": "AccessDenied",
                    "EBS_encryption_by_default": "AccessDenied",
                }
            ]
    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(f"cannot assume the role for:{_account_id} because of {err}")
            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "AMI_block_public_access": "AccessDenied",
                    "EBS_encryption_by_default": "AccessDenied",
                }
            ]

        else:
            logger.error(f"{err} " f"for account id {_account_id} and region {_region}")
            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "AMI_block_public_access": "GenericError",
                    "EBS_encryption_by_default": "GenericError",
                }
            ]


def extract_ssm_documents(all_args):
    _account_id, _region, ssm_client = all_args

    result = []
    try:
        if ssm_client:
            paginator = ssm_client.get_paginator("list_documents")
            response_iterator = paginator.paginate(
                Filters=[
                    {"Key": "Owner", "Values": ["Self"]},
                ]
            )

            for response in response_iterator:
                for document in response["DocumentIdentifiers"]:
                    if document["Name"].find("SSM-SessionManagerRunShell") > -1:
                        result.append(
                            {
                                "account_id": _account_id,
                                "region": _region,
                            }
                        )
            return result
        else:
            return []

    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role for {_account_id} because of {err}"
            )
            return []
        elif err.response["Error"]["Code"] == "InvalidClientTokenId":
            logger.error(
                f"the security token included in the request is invalid {err} "
                f"for account id {_account_id} and region {_region}"
            )
            return []
        else:
            logger.error(f"{err} " f"for account id {_account_id} and region {_region}")
            raise err
    except Exception as ex:
        logger.error(f"{ex} " f"for account id {_account_id} and region {_region}")
        raise ex


def extract_log_groups(all_args):
    _account_id, _region, logs_client = all_args
    try:
        # iterate over only spoke accounts
        if logs_client:
            paginator = logs_client.get_paginator("describe_log_groups")
            response_iterator = paginator.paginate(PaginationConfig={"PageSize": 50})

            result = []
            for response in response_iterator:
                for one in response["logGroups"]:
                    result.append(
                        {
                            "account_id": _account_id,
                            "log_group_name": one["logGroupName"],
                            "region": _region,
                            "creation": one["creationTime"],
                            "retention": one.get("retentionInDays", "Never"),
                        }
                    )
            return result
        else:
            return []
    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{_account_id} because of {err}"
            )
            return None
        elif err.response["Error"]["Code"] == "InvalidClientTokenId":
            logger.error(
                f"the security token included in the request is invalid {err} "
                f"for account id {_account_id} and region {_region}"
            )
            return []
        elif err.response["Error"]["Code"] == "UnrecognizedClientException":
            logger.error(
                f"the security token included in the request is invalid {err} "
                f"for account id {_account_id} and region {_region}"
            )
            return []
        else:
            logger.error(f"{err} " f"for account id {_account_id} and region {_region}")
            raise err
    except Exception as ex:
        logger.error(f"{ex} " f"for account id {_account_id} and region {_region}")
        raise ex


def extract_roles(all_args):
    _account_id, _region, iam_client = all_args
    try:
        # iterate over only spoke accounts
        if iam_client:
            paginator = iam_client.get_paginator("list_roles")
            response_iterator = paginator.paginate(PaginationConfig={"PageSize": 50})

            result = []
            for response in response_iterator:
                for one in response["Roles"]:
                    result.append(
                        {
                            "account_id": _account_id,
                            "rolename": one["RoleName"],
                            "region": _region,
                            "Arn": one["Arn"],
                        }
                    )
            return result
        else:
            return []
    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{_account_id} because of {err}"
            )
            return None
        elif err.response["Error"]["Code"] == "InvalidClientTokenId":
            logger.error(
                f"the security token included in the request is invalid {err} "
                f"for account id {_account_id} and region {_region}"
            )
            return []
        elif err.response["Error"]["Code"] == "UnrecognizedClientException":
            logger.error(
                f"the security token included in the request is invalid {err} "
                f"for account id {_account_id} and region {_region}"
            )
            return []
        else:
            logger.error(f"{err} " f"for account id {_account_id} and region {_region}")
            raise err
    except Exception as ex:
        logger.error(f"{ex} " f"for account id {_account_id} and region {_region}")
        raise ex


def extract_virtual_gateways(all_args):
    _account_id, _region, dc_client = all_args
    try:
        # iterate over only spoke accounts
        if dc_client:
            response = dc_client.describe_virtual_gateways()

            result = []
            for one in response["virtualGateways"]:
                result.append(
                    {
                        "account_id": _account_id,
                        "virtualGatewayId": one["virtualGatewayId"],
                        "virtualGatewayState": one["virtualGatewayState"],
                        "region": _region,
                    }
                )
            return result
        else:
            return []
    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{_account_id} because of {err}"
            )
            return None
        elif err.response["Error"]["Code"] == "InvalidClientTokenId":
            logger.error(
                f"the security token included in the request is invalid {err} "
                f"for account id {_account_id} and region {_region}"
            )
            return []
        elif err.response["Error"]["Code"] == "UnrecognizedClientException":
            logger.error(
                f"the security token included in the request is invalid {err} "
                f"for account id {_account_id} and region {_region}"
            )
            return []
        else:
            logger.error(f"{err} " f"for account id {_account_id} and region {_region}")
            raise err
    except Exception as ex:
        logger.error(f"{ex} " f"for account id {_account_id} and region {_region}")
        raise ex


def extract_meshes(all_args):
    _account_id, _region, mesh_client = all_args
    try:
        # iterate over only spoke accounts
        if mesh_client:
            response = mesh_client.list_meshes()

            mesh = []
            for one in response["meshes"]:
                mesh.append(
                    {
                        "account_id": _account_id,
                        "virtualGatewayId": one["meshName"],
                        "arn": one["arn"],
                        "region": _region,
                    }
                )
            return mesh
        else:
            return []
    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{_account_id} because of {err}"
            )
            return None
        elif err.response["Error"]["Code"] == "InvalidClientTokenId":
            logger.error(
                f"the security token included in the request is invalid {err} "
                f"for account id {_account_id} and region {_region}"
            )
            return []
        elif err.response["Error"]["Code"] == "UnrecognizedClientException":
            logger.error(
                f"the security token included in the request is invalid {err} "
                f"for account id {_account_id} and region {_region}"
            )
            return []
        else:
            logger.error(f"{err} " f"for account id {_account_id} and region {_region}")
            raise err
    except Exception as ex:
        logger.error(f"{ex} " f"for account id {_account_id} and region {_region}")
        raise ex


def read_anomalies(response, _account_id, _region):
    return [
        {
            "account_id": _account_id,
            "region": _region,
            "monitor_name": response["MonitorName"],
            "monitor_type": response["MonitorType"],
            "monitor_dimension": response["MonitorDimension"],
            "monitor_arn": response["MonitorArn"],
            "creation_date": response["CreationDate"],
            "last_update_date": response.get("LastUpdatedDate", "NA"),
            "last_eval_date": response.get("LastEvaluatedDate", "NA"),
            "monitor_spec": response.get("MonitorSpecification", "NA"),
        }
    ]


def read_subs(subscriptions):
    am = []
    for one in subscriptions:
        am.append(
            {
                "subscribers": [two for two in one["Subscribers"]],
                "threshold": one["Threshold"] if "Threshold" in one else "NA",
                "frequency": one["Frequency"],
                "threshold_expression": one["ThresholdExpression"],
            }
        )
    return am


def extract_anomalies_monitor(all_args):
    _account_id, _region, am_client = all_args
    retry = 2
    try:
        # iterate over only spoke accounts
        if am_client:
            response = am_client.get_anomaly_monitors()
            if len(response["AnomalyMonitors"]) > 0:
                am = read_anomalies(
                    response["AnomalyMonitors"][0], _account_id, _region
                )
                res_sub = am_client.get_anomaly_subscriptions(
                    MonitorArn=am[0]["monitor_arn"]
                )
                if len(res_sub["AnomalySubscriptions"]) > 0:
                    sub_list = read_subs(res_sub["AnomalySubscriptions"])
                    am[0]["subscribers"] = [sub for sub in sub_list[0]["subscribers"]]
                    am[0]["threshold"] = sub_list[0]["threshold"]
                    am[0]["frequency"] = sub_list[0]["frequency"]
                    am[0]["threshold_expression"] = sub_list[0]["threshold_expression"]

                return am
            else:
                return []

        else:
            return []
    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{_account_id} because of {err}"
            )
            return None
        elif err.response["Error"]["Code"] == "InvalidNextTokenException":
            logger.error(
                f"the security token included in the request is invalid {err} "
                f"for account id {_account_id} and region {_region}"
            )
            return []
        elif err.response["Error"]["Code"] == "LimitExceededException":
            logger.error(
                f"the security token included in the request is invalid {err} "
                f"for account id {_account_id} and region {_region}"
            )

            while retry > 0:
                sleeping_time = WAITING_SECONDS - retry + 1
                logger.info(f"sleeping for {2*sleeping_time} seconds")
                time.sleep(2 * sleeping_time)
                try:
                    response = am_client.get_anomaly_monitors()
                    if len(response["AnomalyMonitors"]) > 0:
                        am = read_anomalies(
                            response["AnomalyMonitors"][0], _account_id, _region
                        )
                        res_sub = am_client.get_anomaly_subscriptions(
                            MonitorArn=am[0]["monitor_arn"]
                        )
                        if len(res_sub["AnomalySubscriptions"]) > 0:
                            sub_list = read_subs(res_sub["AnomalySubscriptions"])
                            am[0]["subscribers"] = [
                                sub for sub in sub_list[0]["subscribers"]
                            ]
                            am[0]["threshold"] = sub_list[0]["threshold"]
                            am[0]["frequency"] = sub_list[0]["frequency"]
                            am[0]["threshold_expression"] = sub_list[0][
                                "threshold_expression"
                            ]

                        return am
                    else:
                        return []
                except ClientError as err:
                    if err.response["Error"]["Code"] == "LimitExceededException":
                        retry -= 1
                        continue
                    else:
                        retry = 0

            return [{"account_id": _account_id, "region": _region}]
        elif err.response["Error"]["Code"] == "UnknownMonitorException":
            logger.error(
                f"the security token included in the request is invalid {err} "
                f"for account id {_account_id} and region {_region}"
            )
            return []
        else:
            logger.error(f"{err} " f"for account id {_account_id} and region {_region}")
            raise err
    except Exception as ex:
        logger.error(f"{ex} " f"for account id {_account_id} and region {_region}")
        raise ex


def extract_login_profiles(all_args):
    _account_id, _region, am_client = all_args

    try:
        result = []
        if am_client:
            response = am_client.list_users()
            users = response["Users"]

            if len(users) > 0:
                for user in users:
                    try:
                        response = am_client.get_login_profile(
                            UserName=user["UserName"]
                        )
                        if "LoginProfile" in response:
                            result.append(
                                {
                                    "account_id": _account_id,
                                    "region": _region,
                                    "profile": response["LoginProfile"]["UserName"],
                                }
                            )
                    except ClientError as err:
                        if err.response["Error"]["Code"] == "NoSuchEntity":
                            logger.warning(
                                f"{err.response['Error']['Message']} for {844114997973} because of {err}"
                            )
                        else:
                            raise err
                logger.info(f"user extraction completed for {_account_id}")
                return result
            else:
                return result

        else:
            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "profile": "AccessDenied",
                }
            ]
    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{_account_id} because of {err}"
            )
            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "profile": "AccessDenied",
                }
            ]

        else:
            logger.error(f"{err} " f"for account id {_account_id} and region {_region}")
            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "profile": "GenericError",
                }
            ]
    except Exception as ex:
        logger.error(f"{ex} " f"for account id {_account_id} and region {_region}")
        return [
            {"account_id": _account_id, "region": _region, "profile": "GenericError"}
        ]


def extract_instances(all_args):
    _account_id, _region, ec2_client = all_args

    try:
        if ec2_client:
            paginator = ec2_client.get_paginator("describe_instances")
            response_iterator = paginator.paginate()

            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "instance_id": ec2["InstanceId"],
                    "tags": ec2["Tags"] if "Tags" in ec2 else "PROBLEM",
                }
                for response in response_iterator
                for reserve in response["Reservations"]
                for ec2 in reserve["Instances"]
            ]

        else:
            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "instance_id": "AccessDenied",
                    "tags": "AccessDenied",
                }
            ]
    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{_account_id} because of {err}"
            )
            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "instance_id": "AccessDenied",
                    "tags": "AccessDenied",
                }
            ]

        else:
            logger.error(f"{err} " f"for account id {_account_id} and region {_region}")
            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "instance_id": "GenericError",
                    "tags": "GenericError",
                }
            ]
    except Exception as ex:
        logger.error(f"{ex} " f"for account id {_account_id} and region {_region}")
        return [
            {
                "account_id": _account_id,
                "region": _region,
                "instance_id": "GenericError",
                "tags": "GenericError",
            }
        ]


def extract_volumes(all_args):
    _account_id, _region, ec2_client = all_args

    try:
        if ec2_client:
            paginator = ec2_client.get_paginator("describe_volumes")
            response_iterator = paginator.paginate()

            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "volume_id": volume["VolumeId"],
                    "tags": volume["Tags"] if "Tags" in volume else "PROBLEM",
                }
                for response in response_iterator
                for volume in response["Volumes"]
            ]

        else:
            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "volume_id": "AccessDenied",
                    "tags": "AccessDenied",
                }
            ]
    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{_account_id} because of {err}"
            )
            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "volume_id": "AccessDenied",
                    "tags": "AccessDenied",
                }
            ]

        else:
            logger.error(f"{err} " f"for account id {_account_id} and region {_region}")
            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "volume_id": "GenericError",
                    "tags": "GenericError",
                }
            ]
    except Exception as ex:
        logger.error(f"{ex} " f"for account id {_account_id} and region {_region}")
        return [
            {
                "account_id": _account_id,
                "region": _region,
                "volume_id": "GenericError",
                "tags": "GenericError",
            }
        ]


def extract_snapshots(all_args):
    _account_id, _region, ec2_client = all_args

    try:
        if ec2_client:
            paginator = ec2_client.get_paginator("describe_snapshots")
            response_iterator = paginator.paginate(OwnerIds=["self"])

            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "snapshot_id": snapshot["SnapshotId"],
                    "tags": snapshot["Tags"] if "Tags" in snapshot else "PROBLEM",
                }
                for response in response_iterator
                for snapshot in response["Snapshots"]
            ]

        else:
            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "snapshot_id": "AccessDenied",
                    "tags": "AccessDenied",
                }
            ]
    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{_account_id} because of {err}"
            )
            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "snapshot_id": "AccessDenied",
                    "tags": "AccessDenied",
                }
            ]

        else:
            logger.error(f"{err} " f"for account id {_account_id} and region {_region}")
            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "snapshot_id": "GenericError",
                    "tags": "GenericError",
                }
            ]
    except Exception as ex:
        logger.error(f"{ex} " f"for account id {_account_id} and region {_region}")
        return [
            {
                "account_id": _account_id,
                "region": _region,
                "snapshot_id": "GenericError",
                "tags": "GenericError",
            }
        ]


def extract_asgs(all_args):
    _account_id, _region, asg_client = all_args

    try:
        if asg_client:
            paginator = asg_client.get_paginator("describe_auto_scaling_groups")
            response_iterator = paginator.paginate()

            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "auto_scaling_group_name": asg["AutoScalingGroupName"],
                    "tags": asg["Tags"] if asg["Tags"] else "PROBLEM",
                }
                for response in response_iterator
                for asg in response["AutoScalingGroups"]
            ]

        else:
            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "auto_scaling_group_name": "AccessDenied",
                    "tags": "AccessDenied",
                }
            ]
    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{_account_id} because of {err}"
            )
            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "auto_scaling_group_name": "AccessDenied",
                    "tags": "AccessDenied",
                }
            ]

        else:
            logger.error(f"{err} " f"for account id {_account_id} and region {_region}")
            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "auto_scaling_group_name": "GenericError",
                    "tags": "GenericError",
                }
            ]
    except Exception as ex:
        logger.error(f"{ex} " f"for account id {_account_id} and region {_region}")
        return [
            {
                "account_id": _account_id,
                "region": _region,
                "auto_scaling_group_name": "GenericError",
                "tags": "GenericError",
            }
        ]


def extract_event_rules(all_args):
    _account_id, _region, event_client = all_args

    try:
        if event_client:
            paginator = event_client.get_paginator("list_rules")
            response_iterator = paginator.paginate()

            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "rule_name": rule["Name"],
                }
                for response in response_iterator
                for rule in response["Rules"]
            ]

        else:
            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "rule_name": "AccessDenied",
                }
            ]
    except ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            logger.warning(
                f"cannot assume the role for the role:{_account_id} because of {err}"
            )
            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "rule_name": "AccessDenied",
                }
            ]

        else:
            logger.error(f"{err} " f"for account id {_account_id} and region {_region}")
            return [
                {
                    "account_id": _account_id,
                    "region": _region,
                    "rule_name": "GenericError",
                }
            ]
    except Exception as ex:
        logger.error(f"{ex} " f"for account id {_account_id} and region {_region}")
        return [
            {
                "account_id": _account_id,
                "region": _region,
                "rule_name": "GenericError",
            }
        ]
