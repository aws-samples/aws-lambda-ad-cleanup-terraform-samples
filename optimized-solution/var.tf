variable "iam_policy_arn" {
  description = "IAM Policy to be attached to role"
  type        = list(string)
  default     = ["arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess","arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole", "arn:aws:iam::aws:policy/AutoScalingReadOnlyAccess", "arn:aws:iam::aws:policy/service-role/AWSConfigRole"]
}
variable "child_account_cross_role_arn" {
  description = "This is the role arn which will assume child account role to get the list of EC2 instances from Child accounts"
  type        = list(string)
}

variable "lambda_env_cross_role_arn" {
  description = "This is same as child_account_cross_role_arn but this value is being used by lamda function as a environment variable to pass it on loop "
  type        = string
}
