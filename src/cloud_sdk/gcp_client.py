import inspect
from typing import List
import concurrent.futures

from google.api_core.exceptions import NotFound
from google.cloud import compute_v1
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import utils.logger as logs
import paramiko

import secrets
import string

from configs.config import load_config

log = logs.CustomLogger(__name__)


def generate_id(n):
    alphabet = string.ascii_lowercase + string.digits
    unique_id = ''.join(secrets.choice(alphabet) for _ in range(n))
    return unique_id


class GCPClient:
    def __init__(self, config):
        self.project_config = config["project"]
        self.instance_config = config["vm_instances"]
        self.network_config = config["vpc_network"]
        self.project_name = self.project_config["name"]
        self.project_id = self.project_config["id"]
        self.region = self.project_config["region"]
        self.zone = self.project_config["zone"]

        self.credentials = service_account.Credentials.from_service_account_file(
            self.instance_config["service_account_credentials"],
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        self.client = build(self.instance_config["service"], "v1", credentials=self.credentials)

    def __repr__(self):
        return f"{__class__.__name__}({self.project_name}, {self.zone})"

    def get_instances(self):
        """Get all VM instances"""
        return self.client.instances().list(
            project=self.project_id,
            zone=self.zone,
        ).execute()

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

    def execute_script_in_instance(self, instance, script) -> None:
        """Execute single script in single instance"""
        ip_address = instance["networkInterfaces"][0]["accessConfigs"][0]["natIP"]

        ssh_key, ssh_username = self.get_ssh_credentials(instance)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip_address, username=ssh_username, pkey=ssh_key)

        ssh.exec_command(script)
        ssh.close()

    def create_vm_instance(self) -> None:
        """Create a VM instance"""
        instance_template = self.load_instance_template()
        request = self.client.instances().insert(
            project=self.project_id,
            zone=self.zone,
            body=instance_template,
        )
        self.execute_request(request)

    def create_n_instances(self, n) -> None:
        for _ in range(n):
            self.create_vm_instance()

    def delete_all_vm_instances(self):
        """Delete all VM instances"""
        instances = self.get_instances()

        for instance in instances["items"]:
            instance_name = instance["name"]
            request = self.client.instances().delete(
                project=self.project_id,
                zone=self.zone,
                instance=instance_name
            )
            self.execute_request(request)

    def load_instance_template(self) -> dict:
        """Load instance template, add unique name, update metadata startup script"""
        instance_template = load_config(self.instance_config["instance_template"])

        # Add unique id to name
        instance_template["name"] += f"-{generate_id(10)}"

        # Add startup script
        startup_script_path = instance_template["metadata"]["items"][0]["value"]
        with open(startup_script_path, "r") as f:
            start_up_script = f.read()
            instance_template["metadata"]["items"] = [{"key": "startup-script", "value": start_up_script}]

        return instance_template

    def execute_request(self, request):
        func_name = inspect.stack()[1][3]
        try:
            response = request.execute()
            self.client.globalOperations().wait(project=self.project_id, operation=response["name"])
            log.info(f"{func_name} executed successfully - {response}")
            return response
        except HttpError as error:
            error_msg = f"{func_name} request failed - {error}"
            log.warning(error_msg)
            raise HttpError(error_msg)

    def create_network(self) -> None:
        network_name = self.network_config["network"]["name"]

        try:
            network_client = compute_v1.NetworksClient(credentials=self.credentials)
            network_client.get(project=self.project_id, network=network_name)
            log.info(f"Network {network_name} already exists. Skipping creation step.")
            return
        except NotFound:
            log.info(f"Network {network_name} not found. Building new network.")

        network_body = {
            'name': network_name,
            'autoCreateSubnetworks': False
        }
        request = self.client.networks().insert(project=self.project_id, body=network_body)
        self.execute_request(request)

    def create_subnetwork(self):
        subnet_name = self.network_config["subnet"]["name"]
        network_name = self.network_config["network"]["name"]
        ip_cidr_range = self.network_config["subnet"]["ip_cidr_range"]

        try:
            subnet_client = compute_v1.SubnetworksClient(credentials=self.credentials)
            subnet_client.get(project=self.project_id, region=self.region, subnetwork=subnet_name)
            log.info(f"Subnetwork {subnet_name} already exists. Skipping creation step.")
            return
        except NotFound:
            log.info(f"Subnetwork {subnet_name} not found. Building new subnet.")

        subnetwork_body = {
            "name": subnet_name,
            "ipCidrRange": ip_cidr_range,
            "region": f"projects/{self.project_id}/regions/{subnet_name}",
            "network": f"projects/{self.project_id}/global/networks/{network_name}"
        }
        request = self.client.subnetworks().insert(
            project=self.project_id,
            region=self.region,
            body=subnetwork_body
        )
        self.execute_request(request)

    def create_allow_all_firewall_rule(self):
        """Not working or required"""
        network_name = self.network_config["network"]["name"]
        firewall_rule_body = {
            "network": f"projects/{self.project_id}/global/networks/{network_name}"
        }
        firewall_rule_body.update(self.network_config["firewall"])

        firewall_rule = self.client.firewalls().insert(
            project=self.project_id,
            body=firewall_rule_body,
        )
        self.execute_request(firewall_rule)
