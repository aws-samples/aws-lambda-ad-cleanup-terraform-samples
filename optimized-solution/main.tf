data "aws_partition" "current" {}

data "aws_region" "current" {}

data "aws_caller_identity" "current" {}

resource "random_id" "server" {
  byte_length = 8
}

data "archive_file" "lambda_my_function" {
  type             = "zip"
  source_file      = "lambda_function.py"
  output_file_mode = "0666"
  output_path      = "${path.module}/files/adcleanup.zip"
}

data "archive_file" "lambda_my_function_optmized" {
  type             = "zip"
  source_file      = "optimized_function.py"
  output_file_mode = "0666"
  output_path      = "${path.module}/files/adcleanup_optmized.zip"
}

resource "aws_ssm_document" "foo" {
  name          = "AWSRunPowershellADCleanupTerraform"
  document_type = "Command"

  content = <<DOC
{
  "schemaVersion": "1.2",
  "description": "Run a PowerShell script or specify the paths to scripts to run.",
  "parameters": {
    "commands": {
      "type": "StringList",
      "description": "(Required) Specify the commands to run or the paths to existing scripts on the instance.",
      "minItems": 1,
      "displayType": "textarea"
    },
    "workingDirectory": {
      "type": "String",
      "default": "",
      "description": "(Optional) The path to the working directory on your instance.",
      "maxChars": 4096
    },
    "executionTimeout": {
      "type": "String",
      "default": "3600",
      "description": "(Optional) The time in seconds for a command to be completed before it is considered to have failed. Default is 3600 (1 hour). Maximum is 172800 (48 hours).",
      "allowedPattern": "([1-9][0-9]{0,4})|(1[0-6][0-9]{4})|(17[0-1][0-9]{3})|(172[0-7][0-9]{2})|(172800)"
    }
  },
  "runtimeConfig": {
    "aws:runPowerShellScript": {
      "properties": [
        {
          "id": "0.aws:runPowerShellScript",
          "runCommand": "{{ commands }}",
          "workingDirectory": "{{ workingDirectory }}",
          "timeoutSeconds": "{{ executionTimeout }}"
        }
      ]
    }
  }
}
DOC
}

resource "aws_iam_role" "ADcleanuprole" {
  name = "ADcleanuprole" # ADcleanuprole is the static IAM Role name, Make sure this is not exist in your account if you are running terraform apply 

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy" "ssmpolicy" {
  name   = "S3Access1"
  role   = aws_iam_role.ADcleanuprole.id
  policy = <<EOT
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                    "ssm:PutParameter",
                    "ssm:Get*",
                    "ssm:Describe*",
                    "ssm:List*",
                    "ssm:create*",
                    "ssm:update*",
                    "ssm:send*"
            ],
            "Resource": [
                    "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:*",
                    "arn:aws:ec2:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:instance/*",
                    "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"
            ],
            "Effect": "Allow"
        }
    ]
}
EOT
}

resource "aws_iam_role_policy" "crossaccountpolicy1" {
  name   = "crossaccountpolicy1"
  role   = aws_iam_role.ADcleanuprole.id
  policy = <<EOT
{
    "Version": "2012-10-17",
    "Statement": [
  {
        "Effect": "Allow",
        "Action": "sts:AssumeRole",
        "Resource": ${jsonencode(var.child_account_cross_role_arn)}
}
]
}
EOT
}


resource "aws_iam_role_policy_attachment" "role-policy-attachment" {
  role       = aws_iam_role.ADcleanuprole.name
  count      = length(var.iam_policy_arn)
  policy_arn = var.iam_policy_arn[count.index]
}


resource "aws_lambda_function" "ADcleanupfunction" {
  function_name = "ADcleanup-Lambda" # ADcleanup-Lambda is the function name, Make sure this is not exist in your account if you are running terraform apply 
  #checkov:skip=CKV_AWS_117: "Ensure that AWS Lambda function is configured inside a VPC"
  #checkov:skip=CKV_AWS_116: "Ensure that AWS Lambda function is configured for a Dead Letter Queue(DLQ)"
  #checkov:skip=CKV_AWS_173: "Check encryption settings for Lambda environmental variable"
  description                    = "This lambda function verifies the main project's dependencies, requirements and implement auxiliary functions"
  role                           = aws_iam_role.ADcleanuprole.arn
  handler                        = "lambda_function.lambda_handler"
  filename                       = data.archive_file.lambda_my_function.output_path
  runtime                        = "python3.8"
  timeout                        = 300
  memory_size                    = 128
  reserved_concurrent_executions = 1
  environment {
    variables = {
      rolearn = var.lambda_env_cross_role_arn
    }
  }
  tracing_config {
    mode = "Active"
  }
}

resource "aws_lambda_function" "optimized-ad-cleanup-function" {
  function_name = "optimized-ad-cleanup-Lambda" # ADcleanup-Lambda is the function name, Make sure this is not exist in your account if you are running terraform apply
  #checkov:skip=CKV_AWS_117: "Ensure that AWS Lambda function is configured inside a VPC"
  #checkov:skip=CKV_AWS_116: "Ensure that AWS Lambda function is configured for a Dead Letter Queue(DLQ)"
  #checkov:skip=CKV_AWS_173: "Check encryption settings for Lambda environmental variable"
  description                    = "This lambda function verifies the main project's dependencies, requirements and implement auxiliary functions"
  role                           = aws_iam_role.ADcleanuprole.arn
  handler                        = "optimized_function.lambda_handler"
  filename                       = data.archive_file.lambda_my_function_optmized.output_path
  runtime                        = "python3.8"
  timeout                        = 300
  memory_size                    = 128
  reserved_concurrent_executions = 1
  environment {
    variables = {
      rolearn = var.lambda_env_cross_role_arn
    }
  }
  tracing_config {
    mode = "Active"
  }
}

resource "aws_cloudwatch_event_rule" "every_day_once" {
  name                = "every-day-once"
  description         = "Fires every day once"
  schedule_expression = "rate(5 minutes)"
}

resource "aws_cloudwatch_event_target" "check_foo_every_day_once" {
  rule      = aws_cloudwatch_event_rule.every_day_once.name
  target_id = "ADcleanup-Lambda"
  arn       = aws_lambda_function.ADcleanupfunction.arn
}

resource "aws_cloudwatch_event_rule" "master_account_events" {
  name        = "capture-aws-sign-in"
  description = "Capture each AWS Console Sign In"

  event_pattern = <<PATTERN
{
  "source": [
    "aws.ec2"
  ],
  "detail-type": [
    "EC2 Instance State-change Notification"
  ],
  "detail": {
    "state": [
      "terminated"
    ]
  }
}
PATTERN
}

resource "aws_cloudwatch_event_rule" "child_account_events" {
  name        = "capture-aws-sign-in-child"
  description = "Capture each AWS Console Sign In"

  event_pattern = <<PATTERN
{
  "account": [
    "*"
  ],
  "source": [
    "aws.ec2"
  ],
  "detail-type": [
    "EC2 Instance State-change Notification"
  ],
  "detail": {
    "state": [
      "terminated"
    ]
  }
}
PATTERN
}
resource "aws_cloudwatch_event_target" "child_account_events_target" {
  rule      = aws_cloudwatch_event_rule.child_account_events.name
  target_id = "optimized-ad-cleanup-Lambda"
  arn       = aws_lambda_function.ADcleanupfunction.arn
}

resource "aws_cloudwatch_event_target" "master_account_events_target" {
  rule      = aws_cloudwatch_event_rule.master_account_events.name
  target_id = "optimized-ad-cleanup-Lambda"
  arn       = aws_lambda_function.ADcleanupfunction.arn
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_ADcleanup" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ADcleanupfunction.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.every_day_once.arn
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_ADcleanup_terminationevent_master" {
  statement_id  = "AllowExecutionFromCloudWatch_master"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.optimized-ad-cleanup-function.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.master_account_events.arn
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_ADcleanup_terminationevent_child" {
  statement_id  = "AllowExecutionFromCloudWatch2_child"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.optimized-ad-cleanup-function.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.child_account_events.arn
}

