variable "iam_policy_arn" {
  description = "IAM Policy to be attached to role"
  type        = list(string)
  default     = ["arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess", "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole", "arn:aws:iam::aws:policy/AutoScalingReadOnlyAccess", "arn:aws:iam::aws:policy/service-role/AWS_ConfigRole"]
}
variable "child_account_cross_role_arn" {
  description = "This is the role arn which will assume child account role to get the list of EC2 instances from Child accounts"
  type        = list(string)
}
