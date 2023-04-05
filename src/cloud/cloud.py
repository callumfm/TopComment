from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from utils.logger import get_configured_logger

log = get_configured_logger(__name__)


class GoogleCloudClient:

    def __init__(self, sa_credentials, service, project_name, zone):
        self.project = project_name
        self.zone = zone
        self.mig_name = None
        self.credentials = service_account.Credentials.from_service_account_file(
            sa_credentials,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        self.client = build(service, "v1", credentials=self.credentials)

    def __repr__(self):
        return f"{__class__.__name__}({self.project}, {self.zone})"

    def __enter__(self, **kwargs):
        self.create_mig(**kwargs)

    def __exit__(self, mig_name, exc_type, exc_val, exc_tb):
        self.close_mig()

    def create_mig(self, instance_name, instance_template, num_instances):
        """Use the Google Cloud Python SDK to create a Managed Instance Group (MIG) with n instances"""
        instance_group_body = {
            "name": instance_name,
            "instanceTemplate": instance_template,
            "targetSize": num_instances
        }
        try:
            request = self.client.instanceGroupManagers().insert(
                project=self.project,
                zone=self.zone,
                body=instance_group_body
            )
            response = request.execute()
            log.info(f"Instance created: {response['name']}")
        except HttpError as error:
            log.warning(f"Instance creation failed: {error}")

    def close_mig(self):
        """Use the Google Cloud Python SDK to close Managed Instance Group (MIG) with n instances"""
        try:
            mig_resource = self.client.instanceGroupManagers().get(
                project=self.project,
                zone=self.zone,
                instanceGroupManager=self.mig_name
            ).execute()

            instance_names = [i['instance'].rsplit('/', 1)[1] for i in mig_resource['instanceGroup']]
            instances = [{'instance': f'/compute/v1/projects/{self.project}/zones/{self.zone}/instances/{name}'} for name in instance_names]

            request = self.client.instanceGroupManagers().deleteInstances(
                project=self.project,
                zone=self.zone,
                instanceGroupManager=self.mig_name,
                body={"instances": instances}
            )
            response = request.execute()
            log.info(f"Instance closed: {response['name']}")
        except HttpError as error:
            log.warning(f"Instance closure failed: {error}")
