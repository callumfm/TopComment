import inspect
import secrets
import string
from time import sleep
from typing import List

from google.api_core.exceptions import NotFound
from google.cloud import compute_v1
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import utils.logger as logs
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
        self.startup_timeout = self.project_config["startup_timeout"]

        self.credentials = service_account.Credentials.from_service_account_file(
            self.instance_config["service_account_credentials"],
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        self.client = build(self.instance_config["service"], "v1", credentials=self.credentials)

    def __repr__(self):
        return f"{__class__.__name__}({self.project_name}, {self.zone})"

    def run(self, num_instances: int, scripts: List[str]) -> None:
        for i in range(num_instances):
            self.create_vm_instance(script=scripts[i])

    def await_startup_script_execution(self, instance):
        """Ensures all libraries are installed before using VM"""
        request = self.client.instances().getSerialPortOutput(
            project=self.project_id,
            zone=self.zone,
            instance=instance["id"],
        )
        response = self.execute_request(request)
        console_output = response.get("contents", "")
        t = 0
        while "Setup complete" not in console_output and instance["status"] != "RUNNING":
            sleep(2)
            if t > self.startup_timeout:
                error_msg = f"Startup script exceeded timeout limit ({self.startup_timeout}s) for instance {instance}"
                log.warning(error_msg)
                raise TimeoutError(error_msg)

        log.info(f"Startup script correctly for instance {instance}")

    def create_vm_instance(self, script="") -> None:
        """Create a VM instance"""
        instance_template = self.load_instance_template(script=script)
        request = self.client.instances().insert(
            project=self.project_id,
            zone=self.zone,
            body=instance_template,
        )
        self.execute_request(request, operation=True)

    def get_instances(self):
        """Get all VM instances"""
        return self.client.instances().list(
            project=self.project_id,
            zone=self.zone,
        ).execute()["items"]

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
            self.execute_request(request, operation=True)

    def load_instance_template(self, script: str) -> dict:
        """Load instance template, add unique name, update metadata startup script"""
        instance_template = load_config(self.instance_config["instance_template"])

        # Add unique id to name
        instance_template["name"] += f"-{generate_id(10)}"

        # Add startup script
        startup_script_path = instance_template["metadata"]["items"][0]["value"]
        with open(startup_script_path, "r") as f:
            startup_script = f.read()
            startup_script += f"\n{script}"
            instance_template["metadata"]["items"] = [{"key": "startup-script", "value": startup_script}]

        return instance_template

    def execute_request(self, request, operation=False):
        func_name = inspect.stack()[1][3]
        try:
            response = request.execute()
            if operation:
                self.client.globalOperations().wait(project=self.project_id, operation=response["name"])
            log.info(f"{func_name} executed successfully")
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

    # def create_allow_all_firewall_rule(self):
    #     """Not working or required"""
    #     network_name = self.network_config["network"]["name"]
    #     firewall_rule_body = {
    #         "network": f"projects/{self.project_id}/global/networks/{network_name}"
    #     }
    #     firewall_rule_body.update(self.network_config["firewall"])
    #
    #     firewall_rule = self.client.firewalls().insert(
    #         project=self.project_id,
    #         body=firewall_rule_body,
    #     )
    #     self.execute_request(firewall_rule)
