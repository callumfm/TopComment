from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import utils.logger as logs
import paramiko
import pandas as pd

log = logs.CustomLogger(__name__)


class MIGClient:
    def __init__(
            self,
            sa_credentials,
            service,
            project_name,
            zone,
            ssh_username,
            ssh_key,
            instance_name,
            instance_template,
            num_instances,
    ):
        self.project = project_name
        self.zone = zone
        self.mig_name = None
        self.ssh_username = ssh_username
        self.ssh_key = ssh_key
        self.instance_name = instance_name
        self.instance_template = instance_template
        self.num_instances = num_instances

        self.instance_group_body = {
            "name": self.instance_name,
            "instanceTemplate": self.instance_template,
            "targetSize": self.num_instances,
        }
        self.credentials = service_account.Credentials.from_service_account_file(
            sa_credentials, scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        self.client = build(service, "v1", credentials=self.credentials)

    def __repr__(self):
        return f"{__class__.__name__}({self.project}, {self.zone})"

    def __enter__(self):
        self.create_mig()

    def __exit__(self, mig_name, exc_type, exc_val, exc_tb):
        self.close_mig()

    def get_instances(self):
        """Get all instances in MIG"""
        mig_resource = self.client.instanceGroupManagers().get(
            project=self.project,
            zone=self.zone,
            instanceGroupManager=self.mig_name,
        ).execute()

        instances = []
        for instance in mig_resource["instanceGroup"]:
            instance_name = instance["instance"].rsplit("/", 1)[1]
            request = self.client.instances().get(
                project=self.project,
                zone=self.zone,
                instance=instance_name
            )
            response = request.execute()
            instances.append(response)

        return instances

    def execute_script_in_instance(self, instance, script):
        instance_name = instance["name"]
        ip_address = instance["networkInterfaces"][0]["accessConfigs"][0]["natIP"]

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip_address, username=self.ssh_username, pkey=self.ssh_key)

        cmd = f"python -m {script}"
        stdin, stdout, stderr = ssh.exec_command(cmd)

        stdout_lines = stdout.readlines()
        stderr_lines = stderr.readlines()
        log.info(stderr_lines)
        ssh.close()

        df = pd.DataFrame({"instance": [instance_name] * len(stdout_lines), "output": stdout_lines})
        return df

    def execute_script_on_all_instances(self, script) -> pd.DataFrame:
        instances = self.get_instances()
        dfs = [self.execute_script_in_instance(instance, script) for instance in instances]
        table = pd.concat(dfs, ignore_index=True)
        return table

    def create_mig(self):
        """Use the Google Cloud Python SDK to create a Managed Instance Group (MIG) with n instances"""
        try:
            request = self.client.instanceGroupManagers().insert(
                project=self.project, zone=self.zone, body=self.instance_group_body
            )
            response = request.execute()
            log.info(f"Instance created: {response['name']}")
        except HttpError as error:
            log.warning(f"Instance creation failed: {error}")

    def close_mig(self):
        """Use the Google Cloud Python SDK to close Managed Instance Group (MIG) with n instances"""
        try:
            instances = self.get_instances()
            request = self.client.instanceGroupManagers().deleteInstances(
                project=self.project,
                zone=self.zone,
                instanceGroupManager=self.mig_name,
                body={"instances": instances},
            )
            response = request.execute()
            log.info(f"Instance closed: {response['name']}")
        except HttpError as error:
            log.warning(f"Instance closure failed: {error}")
