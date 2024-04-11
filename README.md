# AD Cleanup automation using Lambda

[Active Directory ](https://www.n-able.com/blog/difference-between-ldap-ad)is a Microsoft scripting tool that manages domain information and user interactions with network services. It’s widely used among managed services providers (MSPs) to [manage employee credentials and access permissions](https://www.n-able.com/blog/free-permissions-analyzer-tool-active-directory).Since Active directory attackers can use inactive accounts to try and hack into an organization. It is important to find these inactive accounts and disable them on a routine maintenance schedule. This APG can quickly find inactive accounts and remove them. So that it will always keep AD secure and updated.

## Folder structure

- Single-account-cleanup

    If the Amazon EC2 instances which are connected to Directory services is present only in single account , single-account-cleanup folder code helps to cleanup the inactive AD via lambda function. Prerequesties and execution flow explained in another read me which is present in the respective folder.

- multiple-account-cleanup

    If the Amazon EC2 instances which are connected to Directory services is present across accounts , multiple-account-cleanup folder code helps to cleanup the inactive AD via lambda function. Prerequesties and execution flow explained in another read me which is present in the respective folder.

- Modularised solution

    If the Amazon EC2 instances which are connected to Directory services is present across accounts , optimized-solution folder code helps to cleanup the inactive AD via lambda function in a two different ways.One is based on termination event ,remove the respective EC2 instance from AD. Other one is bulk cleanup based on cron schedule in Amazon Event Bridge. Prerequesties and execution flow explained in another read me which is present in the respective folder.

## Deployment

- Go to the respective folder and execute the below commands.

```
terraform init
terraform plan
terraform apply

```
## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
