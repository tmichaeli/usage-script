#!/usr/bin/env python3

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
from tabulate import tabulate
import ssl
import atexit

# Configuration
VCENTER_SERVER = "XXX"
USERNAME = "administrator@vsphere.local"
PASSWORD = "XXX"
PORT = 443  # Default vCenter port

# Bypass SSL verification (not recommended for production)
context = ssl._create_unverified_context()

# Connect to vCenter
si = SmartConnect( host=VCENTER_SERVER, user=USERNAME, pwd=PASSWORD, port=PORT, sslContext=context)

# Ensure session is properly disconnected on exit
atexit.register(Disconnect, si)

print("Successfully connected to vCenter!")

# Get the content object
content = si.RetrieveContent()
datastore_cluster_map = {}
rows = []

# Loop through all clusters
for datacenter in content.rootFolder.childEntity:
    if hasattr(datacenter, 'hostFolder'):
        clusters = datacenter.hostFolder.childEntity
        for cluster in clusters:
            if isinstance(cluster, vim.ClusterComputeResource):
                print(f"Datacenter: {datacenter.name}")
                for host in cluster.host:
                    hostname = host.name
                    cores = host.hardware.cpuInfo.numCpuCores
                    sockets = host.hardware.cpuInfo.numCpuPackages
                    vcf_cores = 0
                    if cores <= 16:
                        vcf_cores += 16
                    else:
                        vcf_cores += cores

                    rows.append([
                        cluster.name,
                        host.name,
                        host.hardware.cpuInfo.numCpuPackages,
                        host.hardware.cpuInfo.numCpuCores,
                        vcf_cores
                    ])
                    for ds in host.datastore:
                        datastore_cluster_map[ds._moId] = cluster.name
# Print as table
headers = ["Cluster", "Host", "CPU Sockets", "CPU Cores", "VCF Cores"]
print(tabulate(rows, headers=headers, tablefmt="grid"))


rows = []
# Get all datastores (shared only)
container = content.viewManager.CreateContainerView(content.rootFolder, [vim.Datastore], True)
datastores = container.view

for ds in datastores:
    summary = ds.summary

    # Skip local datastores
    if not summary.multipleHostAccess:
        continue

    cluster_name = datastore_cluster_map.get(ds._moId, "Unknown")

    name = summary.name
    capacity_gb = summary.capacity / (1024**4)
    free_space_gb = summary.freeSpace / (1024**4)
    used_space_gb = capacity_gb - free_space_gb
    percent_free = (free_space_gb / capacity_gb) * 100 if capacity_gb else 0
    rows.append([
         cluster_name,
         name,
         summary.type,
         capacity_gb,
         used_space_gb
    ])
# Print as table
headers = ["Cluster", "Datastore", "Type", "Capacity TB", "Used TB"]
print(tabulate(rows, headers=headers, tablefmt="grid"))
