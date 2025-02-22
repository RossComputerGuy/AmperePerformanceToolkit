# Copyright (c) 2024, Ampere Computing LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module containing classes related to Oracle Network."""

import json
import logging
import uuid

from absl import flags
from perfkitbenchmarker import network
from ampere.pkb import provider_info
from perfkitbenchmarker import resource
from perfkitbenchmarker import vm_util
from ampere.pkb.providers.oci import util

FLAGS = flags.FLAGS

MAX_NAME_LENGTH = 128
WAIT_INTERVAL_SECONDS = 600

VCN_CREATE_STATUSES = frozenset(
    ["AVAILABLE", "PROVISIONING", "TERMINATED", "TERMINATING", "UPDATING"]
)

SUBNET_CREATE_STATUSES = frozenset(
    ["AVAILABLE", "PROVISIONING", "TERMINATED", "TERMINATING", "UPDATING"]
)

IG_CREATE_STATUSES = frozenset(
    ["AVAILABLE", "PROVISIONING", "TERMINATED", "TERMINATING"]
)

ROUTE_TABLE_UPDATE_STATUSES = frozenset(
    ["AVAILABLE", "PROVISIONING", "TERMINATED", "TERMINATING"]
)

SECURITY_LIST_UPDATE_STATUSES = frozenset(
    ["AVAILABLE", "PROVISIONING", "TERMINATED", "TERMINATING"]
)


class OciVcn(resource.BaseResource):
    """An object representing an Oci VCN."""

    def __init__(self, name, region, profile):
        super(OciVcn, self).__init__()
        self.status = None
        self.region = region
        self.profile = profile
        self.id = None
        self.name = name
        self.cidr_blocks = ["172.16.0.0/16"]
        self.cidr_block = None
        self.vcn_id = None
        self.subnet_id = None
        self.ig_id = None
        self.rt_id = None
        self.security_list_id = None
        self.tags = util.MakeFormattedDefaultTags()

    @vm_util.Retry(poll_interval=60, log_errors=False)
    def WaitForVcnStatus(self, status_list):
        """Waits until the disk's status is in status_list."""
        logging.info("Waiting until the instance status is: %s" % status_list)
        status_cmd = util.OCI_PREFIX + [
            "network",
            "vcn",
            "get",
            f"--vcn-id {self.vcn_id}",
            f"--profile {self.profile}",
        ]
        status_cmd = util.GetEncodedCmd(status_cmd)
        out, _ = vm_util.IssueRetryableCommand(status_cmd)
        state = json.loads(out)
        check_state = state["data"]["lifecycle-state"]
        self.status = check_state
        assert check_state in status_list

    def GetVcnIDFromName(self):
        """Gets VCN OCIid from Name"""
        get_cmd = util.OCI_PREFIX + [
            "network",
            "vcn",
            "list",
            f"--display-name {self.name}",
        ]
        get_cmd = util.GetEncodedCmd(get_cmd)
        logging.info(get_cmd)
        stdout, _, _ = vm_util.IssueCommand(get_cmd, raise_on_failure=False)
        response = json.loads(stdout)
        self.vcn_id = response["data"][0]["id"]
        logging.info(self.vcn_id)

    def _Create(self):
        """Creates the VPC."""
        logging.info("Creating custom CIDR Block")
        create_cmd = util.OCI_PREFIX + [
            "network",
            "vcn",
            "create",
            f"--display-name pkb-{FLAGS.run_uri}",
            f"--dns-label vcn{FLAGS.run_uri}",
            f"--freeform-tags {self.tags}",
            '--from-json \'{"cidr-blocks":["172.16.0.0/16"]}\'',
            f"--profile {self.profile}",
        ]
        create_cmd = util.GetEncodedCmd(create_cmd)
        logging.info(create_cmd)
        stdout, _, _ = vm_util.IssueCommand(create_cmd, raise_on_failure=False)
        response = json.loads(stdout)
        self.vcn_id = response["data"]["id"]
        self.cidr_block = response["data"]["cidr-block"]

    def _Delete(self):
        delete_cmd = util.OCI_PREFIX + [
            "network",
            "vcn",
            "delete",
            f"--vcn-id {self.vcn_id}",
            f"--profile {self.profile}",
            "--force",
        ]
        delete_cmd = util.GetEncodedCmd(delete_cmd)
        stdout, _, _ = vm_util.IssueCommand(delete_cmd, raise_on_failure=False)

    def GetSubnetIdFromVCNId(self):
        """Gets Subnet OCIid from Name"""
        get_cmd = util.OCI_PREFIX + [
            "network",
            "subnet",
            "list",
            f"--vcn-id {self.vcn_id}",
            f"--profile {self.profile}",
        ]
        get_cmd = util.GetEncodedCmd(get_cmd)
        logging.info(get_cmd)
        stdout, _, _ = vm_util.IssueCommand(get_cmd, raise_on_failure=False)
        response = json.loads(stdout)
        self.subnet_id = response["data"][0]["id"]

    @vm_util.Retry(poll_interval=60, log_errors=False)
    def WaitForSubnetStatus(self, status_list):
        """Waits until the disk's status is in status_list."""
        logging.info("Waiting until the instance status is: %s" % status_list)
        status_cmd = util.OCI_PREFIX + [
            "network",
            "subnet",
            "get",
            f"--subnet-id {self.subnet_id}",
            f"--profile {self.profile}",
        ]
        status_cmd = util.GetEncodedCmd(status_cmd)
        out, _ = vm_util.IssueRetryableCommand(status_cmd)
        state = json.loads(out)
        check_state = state["data"]["lifecycle-state"]
        self.status = check_state
        assert check_state in status_list

    def CreateSubnet(self):
        """Creates the VPC."""
        logging.info("Creating custom subnet Block")
        create_cmd = util.OCI_PREFIX + [
            "network",
            "subnet",
            "create",
            f"--display-name pkb-{FLAGS.run_uri}",
            f"--dns-label sub{FLAGS.run_uri}",
            f"--cidr-block {self.cidr_block}",
            f"--vcn-id {self.vcn_id}",
            f"--profile {self.profile}",
        ]
        create_cmd = util.GetEncodedCmd(create_cmd)
        stdout, _, _ = vm_util.IssueCommand(create_cmd, raise_on_failure=False)
        response = json.loads(stdout)
        self.subnet_id = response["data"]["id"]

    def DeleteSubnet(self):
        """Creates the VPC."""
        logging.info("Creating custom subnet Block")
        create_cmd = util.OCI_PREFIX + [
            "network",
            "subnet",
            "delete",
            f"--subnet-id {self.subnet_id}",
            f"--profile {self.profile}",
            "--force",
        ]
        create_cmd = util.GetEncodedCmd(create_cmd)
        stdout, _, _ = vm_util.IssueCommand(create_cmd, raise_on_failure=False)

    def WaitForInternetGatewayStatus(self, status_list):
        """Waits until the disk's status is in status_list."""
        logging.info("Waiting until the instance status is: %s", status_list)
        status_cmd = util.OCI_PREFIX + [
            "network",
            "internet-gateway",
            "get",
            f"--ig-id {self.ig_id}",
            f"--profile {self.profile}",
        ]
        status_cmd = util.GetEncodedCmd(status_cmd)
        out, _ = vm_util.IssueRetryableCommand(status_cmd)
        state = json.loads(out)
        check_state = state["data"]["lifecycle-state"]
        self.status = check_state
        assert check_state in status_list

    def CreateInternetGateway(self):
        """Creates the Internet Gateway."""
        logging.info("Creating custom Internet Gateway")
        create_cmd = util.OCI_PREFIX + [
            "network",
            "internet-gateway",
            "create",
            f"--display-name pkb-{FLAGS.run_uri}",
            f"--vcn-id {self.vcn_id}",
            f"--profile {self.profile}",
            "--is-enabled  True",
        ]
        create_cmd = util.GetEncodedCmd(create_cmd)
        stdout, _, _ = vm_util.IssueCommand(create_cmd, raise_on_failure=False)
        response = json.loads(stdout)
        self.ig_id = response["data"]["id"]

    def DeleteInternetGateway(self):
        """Creates the VPC."""
        logging.info("Creating custom subnet Block")
        create_cmd = util.OCI_PREFIX + [
            "network",
            "internet-gateway",
            "delete",
            f"--ig-id {self.ig_id}",
            f"--profile {self.profile}",
            "--force",
        ]
        create_cmd = util.GetEncodedCmd(create_cmd)
        stdout, _, _ = vm_util.IssueCommand(create_cmd, raise_on_failure=False)

    def WaitForRouteTableStatus(self, status_list):
        """Waits until the disk's status is in status_list."""
        logging.info("Waiting until the instance status is: %s", status_list)
        status_cmd = util.OCI_PREFIX + [
            "network",
            "route-table",
            "get",
            f"--rt-id {self.rt_id}",
            f"--profile {self.profile}",
        ]
        status_cmd = util.GetEncodedCmd(status_cmd)
        out, _ = vm_util.IssueRetryableCommand(status_cmd)
        state = json.loads(out)
        check_state = state["data"]["lifecycle-state"]
        self.status = check_state
        assert check_state in status_list

    def WaitForSecurityListStatus(self, status_list):
        """Waits until the disk's status is in status_list."""
        logging.info("Waiting until the instance status is: %s", status_list)
        status_cmd = util.OCI_PREFIX + [
            "network",
            "security-list",
            "get",
            f"--security-list-id {self.security_list_id}",
            f"--profile {self.profile}",
        ]
        status_cmd = util.GetEncodedCmd(status_cmd)
        out, _ = vm_util.IssueRetryableCommand(status_cmd)
        state = json.loads(out)
        check_state = state["data"]["lifecycle-state"]
        self.status = check_state
        assert check_state in status_list

    def UpdateRouteTable(self):
        """Updates the Route Table."""
        logging.info("Update Routing Table with Internet Gateway")
        create_cmd = util.OCI_PREFIX + [
            "network",
            "route-table",
            "update",
            f"--rt-id {self.rt_id}",
            "--force",
            '--route-rules \'[{"cidrBlock":"0.0.0.0/0","networkEntityId":"%s"}]\''
            % self.ig_id,
            f"--profile {self.profile}",
        ]
        create_cmd = util.GetEncodedCmd(create_cmd)
        stdout, _, _ = vm_util.IssueCommand(create_cmd, raise_on_failure=False)

    def ClearRouteTable(self):
        """Updates the Route Table."""
        logging.info("Update Routing Table with Internet Gateway")
        create_cmd = util.OCI_PREFIX + [
            "network",
            "route-table",
            "update",
            f"--rt-id {self.rt_id}",
            "--force",
            "--route-rules '[]'",
            f"--profile {self.profile}",
        ]
        create_cmd = util.GetEncodedCmd(create_cmd)
        stdout, _, _ = vm_util.IssueCommand(create_cmd, raise_on_failure=False)

    def AddSecurityListIngressRule(
        self,
        protocol="6",
        start_port=22,
        end_port=None,
        source_range=None,
        protocol_type=None,
        protocol_code=None,
    ):
        if not end_port:
            end_port = start_port
        end_port = end_port or start_port
        source_range = source_range or "0.0.0.0/0"

        current_security_rules = self.GetSecurityListFromId()
        # tcp =6 #udp=17

        """Updates security list to allow traffic on a specific port"""
        logging.info(f"Add ingress rule for ports {start_port} : {end_port}")
        # start_port=22, end_port=None, source_range=None, protocol_type=None, protocol_code=None
        source = '"source":"%s" ,' % source_range

        protocol_str = '"protocol": "%s" ,' % protocol
        if protocol == "1":
            if protocol_type is None and protocol_code is None:
                icmp_options = '"icmp-options": null,'
            else:
                icmp_options = '"icmp-options": { "code": %s, "type": %s},' % (
                    str(protocol_code),
                    str(protocol_type),
                )
            start_port = None
        else:
            icmp_options = '"icmp-options": null,'

        if start_port:
            tcpOptions = (
                '"tcp-options":{"destinationPortRange": {"max": %s, "min": %s }},'
                % (str(end_port), str(start_port))
            )
        else:
            tcpOptions = '"tcp-options": null,'

        udp_options = '"udp-options": null'

        rule_json_string = '{%s %s %s "is-stateless": false, %s %s }' % (
            source,
            icmp_options,
            protocol_str,
            tcpOptions,
            udp_options,
        )

        current_security_rules.append(json.loads(rule_json_string))

        current_security_rules_str = json.dumps(current_security_rules)
        current_security_rules_str = "'%s'" % current_security_rules_str
        cmd = util.OCI_PREFIX + [
            "network",
            "security-list",
            "update",
            f"--security-list-id {self.security_list_id}",
            "--force",
            f"--ingress-security-rules {current_security_rules_str}",
            f"--profile {self.profile}",
        ]

        cmd = util.GetEncodedCmd(cmd)
        stdout, _, _ = vm_util.IssueCommand(cmd, raise_on_failure=False)

    def GetSecurityListFromId(self):
        cmd = util.OCI_PREFIX + [
            "network",
            "security-list",
            "get",
            f"--security-list-id {self.security_list_id}",
            f"--profile {self.profile}",
        ]
        get_cmd = util.GetEncodedCmd(cmd)
        logging.info(get_cmd)
        stdout, _, _ = vm_util.IssueCommand(get_cmd, raise_on_failure=False)
        response = json.loads(stdout)
        ingress_rules = response["data"]["ingress-security-rules"]
        logging.info(ingress_rules)
        return ingress_rules

    def GetDefaultRouteTableId(self):
        """Get Default Route Table OCI Id."""
        status_cmd = util.OCI_PREFIX + [
            "network",
            "vcn",
            "get",
            f"--vcn-id {self.vcn_id}",
            f"--profile {self.profile}",
        ]
        status_cmd = util.GetEncodedCmd(status_cmd)
        out, _, _ = vm_util.IssueCommand(status_cmd)
        state = json.loads(out)
        self.rt_id = state["data"]["default-route-table-id"]

    def GetDefaultSecurityListId(self):
        """Get Default Route Table OCI Id."""
        status_cmd = util.OCI_PREFIX + [
            "network",
            "vcn",
            "get",
            f"--vcn-id {self.vcn_id}",
            f"--profile {self.profile}",
        ]
        status_cmd = util.GetEncodedCmd(status_cmd)
        out, _, _ = vm_util.IssueCommand(status_cmd)
        state = json.loads(out)
        self.security_list_id = state["data"]["default-security-list-id"]


class OciNetwork(network.BaseNetwork):
    """Object representing a AliCloud Network."""

    CLOUD = provider_info.OCI

    def __init__(self, spec):
        super(OciNetwork, self).__init__(spec)
        self.name = FLAGS.oci_network_name or (
            "perfkit-%s-%s" % (FLAGS.run_uri, str(uuid.uuid4())[-12:])
        )
        self.profile = spec.zone
        self.region = spec.zone
        self.use_vcn = FLAGS.oci_use_vcn
        self.network_id = None
        self.vcn_id = None

        if self.use_vcn:
            self.vcn = OciVcn(self.name, self.region, self.profile)
            self.security_group = None


    @vm_util.Retry()
    def Create(self):
        """Creates the network."""
        if self.use_vcn:
            self.vcn.Create()
            self.vcn.WaitForVcnStatus(["AVAILABLE"])
            self.vcn.GetDefaultRouteTableId()
            self.vcn.GetDefaultSecurityListId()
            self.vcn.CreateSubnet()
            self.vcn.WaitForSubnetStatus(["AVAILABLE"])
            self.network_id = self.vcn.subnet_id
            self.vcn.CreateInternetGateway()
            self.vcn.WaitForInternetGatewayStatus(["AVAILABLE"])
            self.vcn.UpdateRouteTable()
            self.vcn.WaitForRouteTableStatus(["AVAILABLE"])
            # Add opening in VCN for SSH
            self.vcn.AddSecurityListIngressRule(protocol="6", start_port=22)
            self.vcn.WaitForSecurityListStatus(["AVAILABLE"])
            self.vcn.AddSecurityListIngressRule(protocol="1")
            self.vcn.WaitForSecurityListStatus(["AVAILABLE"])

        else:
            self.vcn.GetVcnIDFromName()
            self.vcn.GetSubnetIdFromVCNId()
            self.network_id = self.vcn.subnet_id

    def Delete(self):
        """Deletes the network."""
        if self.use_vcn:
            self.vcn.ClearRouteTable()
            self.vcn.DeleteInternetGateway()
            self.vcn.DeleteSubnet()
            self.vcn.Delete()


class OCIFirewall(network.BaseFirewall):

    CLOUD = provider_info.OCI

    def __init__(self):
        super(OCIFirewall, self).__init__()

    def AllowPort(self, vm, start_port, end_port=None, source_range=None):
        """
        Open a port range on a specific vm. This seems to normally be called by the vm object.

        :param vm:
        :param start_port:
        :param end_port:
        :return:
        """

        if not vm.network.vcn:
            # TODO: What happens when we do not have a vcn? Is that possible?
            logging.error(
                "Opening ports with OCI cloud only supported when using a VCN for now!"
            )

        else:
            vm.network.vcn.AddSecurityListIngressRule(
                protocol="6",
                start_port=start_port,
                end_port=end_port,
                source_range=source_range,
            )
            vm.network.vcn.WaitForRouteTableStatus(["AVAILABLE"])

    def AllowIcmp(self, vm, protocol_type=None, protocol_code=None, source_range=None):
        """Opens the ICMP protocol on the firewall.

        Args:
        vm: The BaseVirtualMachine object to open the ICMP protocol for.
        """
        if not vm.network.vcn:
            logging.error(
                "Allow ICMP with OCI cloud only supported when using a VCN for now!"
            )
        else:
            vm.network.vcn.AddSecurityListIngressRule(
                protocol="1",
                protocol_type=protocol_type,
                protocol_code=protocol_code,
                source_range=source_range,
            )
            vm.network.vcn.WaitForRouteTableStatus(["AVAILABLE"])
            # protocol="6", start_port=22, end_port=None, source_range=None, protocol_type=None, protocol_code=None
