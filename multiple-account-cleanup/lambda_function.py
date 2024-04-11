import boto3
import os
import time
import json
import sys

def lambda_handler(event, context):
    #Get the random instance id from auto scaling groups
    asgclient = boto3.client('autoscaling')
    asg = asgclient.describe_auto_scaling_instances()
    InstanceId = asg['AutoScalingInstances'][0]['InstanceId']
    print("SSM will be connected to below instances")
    print(InstanceId)
    
    #cross account connection
    rolelist = os.environ['rolearn'].split(",")
    AWS_Running_Windows_Servers_IpAddresses = ""
    for role in rolelist:
        sts_connection = boto3.client('sts')
        acct_b = sts_connection.assume_role(
        RoleArn=role,
        RoleSessionName="cross_acct_lambda"
        )
        ACCESS_KEY = acct_b['Credentials']['AccessKeyId']
        SECRET_KEY = acct_b['Credentials']['SecretAccessKey']
        SESSION_TOKEN = acct_b['Credentials']['SessionToken']
        ec2client = boto3.resource(
            'ec2',
            aws_access_key_id=ACCESS_KEY,
            aws_secret_access_key=SECRET_KEY,
            aws_session_token=SESSION_TOKEN,
        )    
        instances = ec2client.instances.filter(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}, {'Name': 'platform', 'Values': ['windows']}])
        for instance in instances:
            AWS_Running_Windows_Servers_IpAddresses = AWS_Running_Windows_Servers_IpAddresses + instance.private_ip_address + " "
        AWS_Running_Windows_Servers_IpAddresses = AWS_Running_Windows_Servers_IpAddresses.replace(' ', '\n')
    
    # List the running windows servers private ip addresses from local
    ec2clientlocal = boto3.resource("ec2")
    instanceslocal = ec2clientlocal.instances.filter(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}, {'Name': 'platform', 'Values': ['windows']}])
    AWS_Running_Windows_Servers_IpAddresses_local = ""
    for instance2 in instanceslocal:
        AWS_Running_Windows_Servers_IpAddresses_local = AWS_Running_Windows_Servers_IpAddresses_local + instance2.private_ip_address + " "
    AWS_Running_Windows_Servers_IpAddresses_local = AWS_Running_Windows_Servers_IpAddresses_local.replace(' ', '\n')
    AWS_Running_Windows_Servers_IpAddresses_All_accounts = AWS_Running_Windows_Servers_IpAddresses + AWS_Running_Windows_Servers_IpAddresses_local
    print("Running windows instances in all accounts")
    print(AWS_Running_Windows_Servers_IpAddresses_All_accounts)
    
    # Connect SSM client to InstanceId and get the AD computers private ip addresses
    ssmclient = boto3.client("ssm")

    ssmresponse = ssmclient.send_command(
        InstanceIds=[InstanceId],
        DocumentName='AWSRunPowershellADCleanup',
        Parameters={"commands": ['Get-ADComputer -Filter * -Properties ipv4Address | Format-List ipv4*']}
    )
    command_id = ssmresponse['Command']['CommandId']
    time.sleep(10)
    output = ssmclient.get_command_invocation(CommandId=command_id, InstanceId=InstanceId)
    s1 = json.dumps(output)
    obj = json.loads(s1)
    error_check = obj['StandardErrorContent']
    if "Get-AD" in error_check:
        print("Get-ADComputer is not installed on given instance")
        return None
    ipv4 = obj['StandardOutputContent']
    ADipv4address = ipv4.replace('IPv4Address : ', '')
    print("Computers which are connected to AD before removal")
    print(ADipv4address)
    print(" ")

    # Compare the two ip addresses list and find the computers which are required to clean-up from AD
    a = ADipv4address.split()
    b = AWS_Running_Windows_Servers_IpAddresses_All_accounts.split()
    Difference = []
    for element in a:
        if element not in b:
            Difference.append(element)
    print("Difference")
    print(Difference)
    print("         ")
    delim = "|"
    Computers_needs_to_be_remove_From_AD = ''
    Difference = Difference[2:]
    if not Difference:
        print("No AD's are required to remove")
        return None
    for ele in Difference:
        Computers_needs_to_be_remove_From_AD = Computers_needs_to_be_remove_From_AD + str(ele) + delim
    Computers_needs_to_be_remove_From_AD = Computers_needs_to_be_remove_From_AD[:-1]

    #Add computers ip addresses to SSM parameter
    ssm_client = boto3.client("ssm")
    ssm_client.put_parameter(
        Name='adiplists2',
        Description='EC2 ipaddresses which are connected to AD',
        Value=Computers_needs_to_be_remove_From_AD,
        Type='String',
        Overwrite=True)

    #Remove the computers from AD
    ssm2 = boto3.client("ssm")
    remove = ssm2.send_command(
        InstanceIds=[InstanceId],
        DocumentName='AWSRunPowershellADCleanup',
        Parameters={
            "commands": ["$t = (Get-SSMParameterValue -Name adiplists2).Parameters[0].Value", "echo $t",
                         "$domainJoinUserName = (Get-SSMParameterValue -Name domainJoinUser).Parameters[0].Value",
                         "$domainJoinPassword = (Get-SSMParameterValue -Name domainJoinPassword -WithDecryption $True).Parameters[0].Value | ConvertTo-SecureString -AsPlainText -Force",
                         "$domainCredential = New-Object System.Management.Automation.PSCredential($domainJoinUserName, $domainJoinPassword)",
                         "(Get-ADComputer -Filter * -Properties ipv4Address | Where-Object {$_.IPv4Address -match $t}) | Remove-ADComputer -Credential $domainCredential -Confirm:$False"]
        }
    )
    # time.sleep(5)
    command_id2 = remove['Command']['CommandId']
    time.sleep(60)
    output2 = ssm2.get_command_invocation(CommandId=command_id2, InstanceId=InstanceId)

    #After Removal- Connect SSM client to InstanceId and get the AD computers private ip addresses
    ssmclient_check = boto3.client("ssm")

    ssmresponsefinal =  ssmclient_check.send_command(
        InstanceIds=[InstanceId],
        DocumentName='AWSRunPowershellADCleanup',
        Parameters={"commands": ['Get-ADComputer -Filter * -Properties ipv4Address | Format-List ipv4*']}
    )
    command_id3 = ssmresponsefinal['Command']['CommandId']
    time.sleep(30)
    output3 = ssmclient_check.get_command_invocation(CommandId=command_id3, InstanceId=InstanceId)
    s2 = json.dumps(output3)
    obj2 = json.loads(s2)
    error_check2 = obj2['StandardErrorContent']
    if "Get-AD" in error_check2:
        print("Get-ADComputer is not installed on given instance")
        exit()
    ipv42 = obj2['StandardOutputContent']
    ADipv4address2 = ipv42.replace('IPv4Address : ', '')
    print("Computers which are connect to AD After removal")
    print(ADipv4address2)
