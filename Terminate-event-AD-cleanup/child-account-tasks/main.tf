data "aws_partition" "current" {}

data "aws_region" "current" {}

data "aws_caller_identity" "current" {}

resource "aws_iam_role" "ec2crossaccountrole" {
  name = "ec2crossaccountrole"

  assume_role_policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "ec2.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        },
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": ${Parent account Lambda function role}
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "role-policy-attachment" {
  role       = aws_iam_role.ec2crossaccountrole.name
  policy_arn = ["arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess","arn:aws:iam::aws:policy/service-role/AWS_ConfigRole"]
}

resource "aws_cloudwatch_event_rule" "child_account_events" {
  name        = "child-account-termination-event"
  description = "Collect child account termination events"

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

resource "aws_cloudwatch_event_target" "child_account_events_target" {
  rule      = aws_cloudwatch_event_rule.child_account_events.name
  target_id = "send-termination-account"
  arn       = ${Parent account default Event Bus}
}

