import boto3
import os
import time
import json
import sys


def lambda_handler(event, context):
    # Get the random instance id from auto scaling groups
    ec2client = boto3.resource("ec2")
    instances = ec2client.instances.filter(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}, {'Name': 'platform', 'Values': ['windows']}])
    for instance in instances:
        print(instance.id)
        Instanceid = instance.id
        ssmclient = boto3.client("ssm")
        ssmresponse = ssmclient.send_command(
            InstanceIds=[Instanceid],
            DocumentName='AWSRunPowershellADCleanup',
            Parameters={"commands": ['Get-ADComputer -Filter * -Properties ipv4Address | Format-List ipv4*']}
        )
        command_id = ssmresponse['Command']['CommandId']
        time.sleep(10)
        output = ssmclient.get_command_invocation(CommandId=command_id, InstanceId=Instanceid)
        s1 = json.dumps(output)
        obj = json.loads(s1)
        error_check = obj['StandardErrorContent']
        if "Get-AD" in error_check:
            print("Get-ADComputer is not installed on given instance")
            continue  # This is to continue for next loop
        else:
            InstanceId = Instanceid
            break  # This break the loop and exit with instance id
    print(InstanceId)

    # asgclient = boto3.client('autoscaling')
    # asg = asgclient.describe_auto_scaling_instances()
    # InstanceId = asg['AutoScalingInstances'][0]['InstanceId']
    # print("SSM will be connected to below instances")
    # print(InstanceId)

    # Get the parent account id
    account_id = boto3.client("sts").get_caller_identity()["Account"]

    # Compare the account id with the input events and decide where it should find the ip addresses
    if account_id != event['account']:
        sts_connection = boto3.client('sts')
        acct_b = sts_connection.assume_role(
            RoleArn="arn:aws:iam::" + event['account'] + ":role/ec2crossaccountrole",
            RoleSessionName="cross_acct_lambda"
        )
        ACCESS_KEY = acct_b['Credentials']['AccessKeyId']
        SECRET_KEY = acct_b['Credentials']['SecretAccessKey']
        SESSION_TOKEN = acct_b['Credentials']['SessionToken']
        client = boto3.client(
            'config',
            aws_access_key_id=ACCESS_KEY,
            aws_secret_access_key=SECRET_KEY,
            aws_session_token=SESSION_TOKEN,
        )
        # client = boto3.client('config')
        # print (event['detail']['instance-id'])
        response = client.get_resource_config_history(
            resourceType='AWS::EC2::Instance', resourceId=event['detail']['instance-id'],
            chronologicalOrder='Reverse',
            limit=2
        )
        configuration_json = response["configurationItems"][1]["configuration"]
        config_dict = json.loads(configuration_json)
        AWS_Terminated_computer_ip_address = config_dict["privateIpAddress"]
        print(AWS_Terminated_computer_ip_address)
    else:
        client = boto3.client('config')
        response = client.get_resource_config_history(
            resourceType='AWS::EC2::Instance', resourceId=event['detail']['instance-id'],
            chronologicalOrder='Reverse',  # By default, the results are listed in reverse chronological order.
            limit=2
        )
        configuration_json = response["configurationItems"][1]["configuration"]
        config_dict = json.loads(configuration_json)
        AWS_Terminated_computer_ip_address = config_dict["privateIpAddress"]
        print(AWS_Terminated_computer_ip_address)

    # Add terminated computer ip address to SSM parameter
    ssm_client = boto3.client("ssm")
    ssm_client.put_parameter(
        Name='adterminatedip',
        Description='EC2 ipaddresses which are connected to AD',
        Value=AWS_Terminated_computer_ip_address,
        Type='String',
        Overwrite=True)

    # Check this computer is present in AD and remove if it is present
    ssm2 = boto3.client("ssm")
    check = ssm2.send_command(
        InstanceIds=[InstanceId],
        DocumentName='AWSRunPowershellADCleanup',
        Parameters={
            "commands": ["$ip = (Get-SSMParameterValue -Name adterminatedip).Parameters[0].Value",
                         "$result = (Get-ADComputer -Filter * -Properties ipv4Address | Where-Object {$_.IPv4Address -eq $ip})",
                         "echo $result"]
        }
    )
    command_id2 = check['Command']['CommandId']
    time.sleep(60)
    output2 = ssm2.get_command_invocation(CommandId=command_id2, InstanceId=InstanceId)
    print(output2)
    s2 = json.dumps(output2)
    obj2 = json.loads(s2)
    error_check2 = obj2['StandardErrorContent']
    if "Get-AD" in error_check2:
        print("Get-ADComputer is not installed on given instance")
        return None
    if AWS_Terminated_computer_ip_address in obj2['StandardOutputContent']:
        print("computer needs to be removed now")
        remove = ssm2.send_command(
            InstanceIds=[InstanceId],
            DocumentName='AWSRunPowershellADCleanup',
            Parameters={
                "commands": ["$ip = (Get-SSMParameterValue -Name adterminatedip).Parameters[0].Value",
                             "$domainJoinUserName = (Get-SSMParameterValue -Name domainJoinUser).Parameters[0].Value",
                             "$domainJoinPassword = (Get-SSMParameterValue -Name domainJoinPassword -WithDecryption $True).Parameters[0].Value | ConvertTo-SecureString -AsPlainText -Force",
                             "$domainCredential = New-Object System.Management.Automation.PSCredential($domainJoinUserName, $domainJoinPassword)",
                             "(Get-ADComputer -Filter * -Properties ipv4Address | Where-Object {$_.IPv4Address -eq $ip}) | Remove-ADComputer -Credential $domainCredential -Confirm:$False"]
            }
        )
        command_id3 = remove['Command']['CommandId']
        time.sleep(60)
        output3 = ssm2.get_command_invocation(CommandId=command_id3, InstanceId=InstanceId)
        # print(output3)
    else:
        print("This computer is not present in AD. No action required")
        return None

    # Final Check this computer is present in AD After removal
    check2 = ssm2.send_command(
        InstanceIds=[InstanceId],
        DocumentName='AWSRunPowershellADCleanup',
        Parameters={
            "commands": ["$ip = (Get-SSMParameterValue -Name adterminatedip).Parameters[0].Value",
                         "$c = (Get-ADComputer -Filter * -Properties ipv4Address | Where-Object {$_.IPv4Address -eq $ip})",
                         "echo $c"]
        }
    )
    command_id4 = check2['Command']['CommandId']
    time.sleep(60)
    output4 = ssm2.get_command_invocation(CommandId=command_id4, InstanceId=InstanceId)
    print(output4)
    s4 = json.dumps(output4)
    obj4 = json.loads(s4)
    error_check4 = obj4['StandardErrorContent']
    if "Get-AD" in error_check4:
        print("Get-ADComputer is not installed on given instance")
        exit()
    if adterminatedip in obj4['StandardOutputContent']:
        print(AWS_Terminated_computer_ip_address + "computer failed to remove for below reason")
        print(obj4['StandardOutputContent'])
    else:
        print(AWS_Terminated_computer_ip_address + "is removed successfully")