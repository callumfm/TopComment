import inspect
from typing import List
import concurrent.futures

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import utils.logger as logs
import paramiko
import pandas as pd

from configs.config import load_config

log = logs.CustomLogger(__name__)


class GCPClient:
    def __init__(self, config):
        self.project_config = config["project"]
        self.mig_config = config["managed_instance_group"]
        self.network_config = config["vpc_network"]
        self.project_name = self.project_config["name"]
        self.project_id = self.project_config["id"]
        self.region = self.project_config["region"]
        self.zone = self.project_config["zone"]

        self.credentials = service_account.Credentials.from_service_account_file(
            self.mig_config["service_account_credentials"],
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        self.client = build(self.mig_config["service"], "v1", credentials=self.credentials)

    def __repr__(self):
        return f"{__class__.__name__}({self.mig_config['project_name']}, {self.mig_config['zone']})"

    def __enter__(self):
        self.upload_instance_template(self.mig_config["instance_template"])
        self.create_mig()

    def __exit__(self, mig_name, exc_type, exc_val, exc_tb):
        self.close_mig()

    def get_instances(self):
        """Get all instances in MIG"""
        mig_resource = self.client.instanceGroupManagers().get(
            project=self.project_name,
            zone=self.zone,
            instanceGroupManager=self.mig_config["name"],
        ).execute()

        instances = []
        for instance in mig_resource["instanceGroup"]:
            instance_name = instance["instance"].rsplit("/", 1)[1]
            request = self.client.instances().get(
                project=self.project_name,
                zone=self.zone,
                instance=instance_name
            )
            response = request.execute()
            instances.append(response)

        return instances

    @staticmethod
    def get_ssh_credentials(instance):
        """Retrieve ssh key and username for instance"""
        metadata = instance["metadata"]["items"]
        ssh_key = None
        ssh_username = None
        for item in metadata:
            if item["key"] == "ssh-keys":
                ssh_key = item["value"].split(":")[1].strip()
                ssh_username = item["value"].split(":")[0].split()

        return ssh_key, ssh_username

    def execute_script_in_instance(self, instance, script):
        """Execute single script in single instance"""
        instance_name = instance["name"]
        ip_address = instance["networkInterfaces"][0]["accessConfigs"][0]["natIP"]

        ssh_key, ssh_username = self.get_ssh_credentials(instance)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip_address, username=ssh_username, pkey=ssh_key)

        cmd = f"python -m {script}"
        stdin, stdout, stderr = ssh.exec_command(cmd)

        stdout_lines = stdout.readlines()
        stderr_lines = stderr.readlines()
        log.info(stderr_lines)
        ssh.close()

        df = pd.DataFrame({"instance": [instance_name] * len(stdout_lines), "output": stdout_lines})
        return df

    def execute_in_parallel(self, scripts: List[str]) -> pd.DataFrame:
        """Execute multiple scripts across multiple instances in parallel"""
        instances = self.get_instances()
        inp = list(zip(instances, scripts))

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(instances)) as executor:
            dfs = executor.map(self.execute_script_in_instance, inp)

        table = pd.concat(dfs, ignore_index=True)
        return table

    def create_mig(self):
        """Use the Google Cloud Python SDK to create a Managed Instance Group (MIG) with n instances"""
        instance_group_body = {
            "name": self.mig_config["name"],
            "size": self.mig_config["num_instances"],
            "instanceTemplate": self.mig_config["instance_template"],
        }
        request = self.client.instanceGroupManagers().insert(
            project=self.project_id,
            zone=self.zone,
            body=instance_group_body
        )
        self.execute_request(request)

    def close_mig(self):
        """Use the Google Cloud Python SDK to close Managed Instance Group (MIG) with n instances"""
        instances = self.get_instances()
        request = self.client.instanceGroupManagers().deleteInstances(
            project=self.project_id,
            zone=self.zone,
            instanceGroupManager=self.mig_config["name"],
            body={"instances": instances},
        )
        self.execute_request(request)

    def create_network(self) -> None:
        name = self.network_config["network"]["name"]
        network_exists = self.check_network_exists(network_name=name)

        if network_exists:
            log.info(f"Network {name} already exists. Skipping creation step.")
            return

        network_body = {
            'name': name,
            'autoCreateSubnetworks': False
        }
        request = self.client.networks().insert(project=self.project_id, body=network_body)
        self.execute_request(request)

    def create_subnetwork(self, network_response):
        name = self.network_config["subnet"]["name"]
        ip_cidr_range = self.network_config["subnet"]["ip_cidr_range"]
        subnet_exists = self.check_network_exists(network_name=name)

        if subnet_exists:
            log.info(f"Network {name} already exists. Skipping creation step.")
            return

        subnetwork_body = {
            "name": name,
            "ipCidrRange": ip_cidr_range,
            "region": f"https://www.googleapis.com/compute/v1/projects/{self.project_id}/regions/{name}",
            "network": network_response["selfLink"]
        }
        request = self.client.subnetworks().insert(
            project=self.project_id,
            region=self.region,
            body=subnetwork_body
        )
        self.execute_request(request)

    def check_network_exists(self, network_name):
        client = self.client.NetworksClient()
        subnet_path = client.network_path(self.project_id, network_name)
        subnet_exists = client.get_network(network_path=subnet_path)
        return subnet_exists

    def upload_instance_template(self, template_path) -> None:
        instance_template = load_config(template_path)
        request = self.client.instanceTemplates().insert(
            project=self.project_id,
            body=instance_template,
        )
        self.execute_request(request)
        self.mig_config["instance_template"] = f"projects/{self.project_name}/global/instanceTemplates/tc-template"

    @staticmethod
    def execute_request(request):
        func_name = inspect.stack()[1][3]
        try:
            response = request.execute()
            log.info(f"{func_name} executed successfully - {response}")
        except HttpError as error:
            log.warning(f"{func_name} request failed - {error}")
