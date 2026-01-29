# ☁️ Af.Boto3.Aws
Python scripts using **boto3** (AWS SDK) to automate tasks and analyze resources in the cloud.

---

### 📋 Script descriptions
#### 🖥️ EC2 (`ec2/`)
| Script | Description |
|--------|-------------|
| **read-ec2-filter-by-tag-all-region.py** | Iterates over all regions and lists EC2 instances that **do not have** the `Project` tag. Outputs InstanceIds per region. |
| **read-ec2-filter-by-account.py** | Iterates over all regions and audits resources without the `Project` tag: EC2 instances, EBS volumes, security groups, Elastic IPs, ECR repositories, and AWS Config rules. Prints untagged resources to the console. |
| **read-ec2-unused-security-groups.py** | Lists **all** security groups in all regions and indicates whether each is in use (attached to a network interface) or not. Exports a CSV with columns: Region, GroupId, GroupName, VpcId, Description, IsDefault, **InUse** (Yes/No). |

#### 📊 CloudWatch (`cloudwatch/`)
| Script | Description |
|--------|-------------|
| **read-cloudwatch.py** | Lists all CloudWatch alarms in region `sa-east-1`. Outputs a JSON with name, state, metric, threshold, actions, etc. and saves `cloudwatch_alarms.json`. |
| **read-cloudwatch-log-groups-with-tags.py** | Iterates over all regions, lists all CloudWatch Logs **log groups** with their **tags** and metadata (retention, size, etc.). Exports a CSV with tags as dynamic columns. |

#### 🔑 IAM (`iam/`)
| Script | Description |
|--------|-------------|
| **read-iam-users.py** | Lists all IAM users with UserName, UserId, Arn, CreateDate, groups, and attached policies. Outputs JSON to the console. |
| **read-iam-users-with-access-keys.py** | Lists IAM users that have **one or more access keys**. For each key it exports: UserName, AccessKeyId, Status, CreateDate, AgeInDays, UserId, UserArn. Generates a CSV and prints a summary (active/inactive) and the oldest key. |
| **read-export-iam.py** | Exports all IAM users with their groups, policies (direct and from groups), and tags (Project, ProjectStatus, ProjectService, ProjectDescription). Generates `users_iam_tags_permisos.csv`. |

#### 🪣 S3 (root)
| Script | Description |
|--------|-------------|
| **read-s3-tags-by-project-report.py** | Lists S3 buckets that **do not have** the `Project` tag. Gets each bucket’s region and exports `buckets_without_project_tag.csv` with BucketName and Region. |

#### 🛡️ Security groups (root)
| Script | Description |
|--------|-------------|
| **read-security-groups.py** | In region `sa-east-1`, lists security groups with **open** rules (ingress or egress with `0.0.0.0/0` or `::/0`). Exports `security_groups_open.csv` with SG ID, name, direction, and CIDR. |

---

### 🗺️ Planned additions
- Automated backup of EC2 instances or EBS volumes, filtered by tags or regions.
- AWS cost reports filtered by resource tags.
- Status and performance checks for other services such as RDS or Lambda.
- Access and permission auditing for IAM configurations.

#### ©️ License
By Agustina Fassina
