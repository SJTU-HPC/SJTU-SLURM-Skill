---
name: SJTU-HPC
description: Log in to the SJTU HPC platform (also known as "交我算") as the user to perform job queries, submissions, cancellations, and data management. Use this skill when the user requests operations related to HPC or "交我算".
---

# SJTU HPC

## Overview

Use this skill to log in to the SJTU HPC (交我算) platform as the user, acting on their behalf to perform personal job queries, submissions, cancellations, and data management operations.

## Quick Start

1. Analyze user requirements and clarify any ambiguous parts by asking follow-up questions. Identify the node group/partition the user is interested in and the operation type to select the correct entry node.
2. Ensure SSH keys and certificates are available in the workspace, which should be stored in `credentials` directory. If not, obtain the user's account credentials to request a new SSH certificate. Remind the user that requesting a certificate will trigger two-factor authentication.
3. Use the SSH certificate to log in to the corresponding entry node based on the cluster and operation type. If two-factor authentication is required, remind the user to complete it through the appropriate channel.
4. Execute the user's requested operations on the entry node.

## Entry Node Selection Rules

Select the appropriate entry node based on the node group and operation type the user is interested in.

Partitions belong to node groups. If the user does not explicitly specify a node group but provides a target partition, look up the corresponding node group from this table:

| partition    | node group |
| ------------ | ---------- |
| cpu          | pi         |
| debug        | pi         |
| dgx2         | pi         |
| huge         | pi         |
| 192c6t       | pi         |
| debugarm     | kp         |
| arm128c256g  | kp         |
| scnet_arm    | kp         |
| small        | sy         |
| 64c512g      | sy         |
| el9          | sy         |
| debug64c512g | sy         |
| win32        | sy         |
| a100         | sy         |
| a800         | sy         |
| debuga100    | sy         |

Then select the entry node according to this table:

| business | node group | entry node              |
| -------- | ---------- | ----------------------- |
| job      | pi         | pilogin.hpc.sjtu.edu.cn |
| job      | sy         | sylogin.hpc.sjtu.edu.cn |
| job      | kp         | kplogin.hpc.sjtu.edu.cn |
| data     | pi, kp     | data.hpc.sjtu.edu.cn    |
| data     | sy         | sydata.hpc.sjtu.edu.cn  |

## SSH Keys and Certificates

SSH login to entry nodes requires the user's passwordless certificate. Check if SSH keys and certificates exist in the `credentials` directory under workspace. If not, follow these steps:

1. **Notify user first**: Tell the user that requesting a certificate need their HPC account username and password, and will trigger two-factor authentication so they need to authorize via JWB APP (交我办) or Email.
2. **Wait for confirmation**: Only proceed after the user confirms they understand and are ready to authorize. If user has not provide their username or password, continue to ask for the missing parts.
3. **Execute with long timeout**: Run `req_certificate.py` with `timeout >= 600s` because the script will block waiting for user to complete two-factor authentication on another channel. This can take several minutes.

```bash
scripts/req_certificate.py "user_name" "user_password" "output_path"
```

`output_path` should be set to the workspace `credentials` directory.

Only SSH keys and certificates may be stored. User account passwords must not be stored, nor included in responses.

> **Important**: The two-factor authentication is asynchronous — while this script is running, the user must check their JWB APP or Email and approve the request. Do not proceed with the script until the user has explicitly confirmed they are aware and ready to authorize.

## Executing User-Requested Operations on Entry Nodes

Use the SSH key and certificate from the workspace credentials directory to log in to the entry node and remotely execute the user's requested operations:

```bash
ssh -i "/path_to_workspace/credentials/private_key" -o "CertificateFile=/path_to_workspace/credentials/certificate" user@entry_node "command"
```

Note that user data is distributed across multiple shared storage pools, and visible storage varies depending on the node group. The storage where the user's home directory resides also differs:

| node group | mount point | storage information                                 |
| ---------- | ----------- | --------------------------------------------------- |
| pi, kp     | /lustre     | Hot storage, Lustre, user home directory is here   |
| sy         | /dssg       | Hot storage, GPFS, user home directory is here     |
| pi, sy, kp | /archive    | Cold storage A, NFS, for archived data, writable only on data and sydata nodes, read-only on other nodes |
| pi, sy, kp | /vault      | Cold storage B, NFS, for archived data, writable only on data and sydata nodes, read-only on other nodes |
| pi, sy, kp | /union      | mergerfs virtual filesystem, combines /archive and /vault, same read/write restrictions as the two cold storages |

User personal directory paths are consistent across storage pools. Replace the top-level path of the user's home directory with the target storage to get the corresponding personal directory path. For example: `/lustre/home/acct-hpc/hpcrobot` -> `/archive/home/acct-hpc/hpcrobot`

If the user is interested in platform status or personal jobs, use SLURM commands to perform operations, including but not limited to: `sinfo, squeue, sacct, seff, sbatch, scancel, etc...`

Due to different storage pool visibility across node groups, job data computed on a partition can only be viewed on entry nodes belonging to the corresponding node group. Each entry node only allows submitting job to partitions within its own node group.

Never use cold storage data directly for job. If cold storage data is needed, transfer it to hot storage first before using it for job.

Large-scale data transfer operations should be performed on `data.hpc.sjtu.edu.cn` and `sydata.hpc.sjtu.edu.cn`.

## Resources

### scripts/

`req_certificate.py`: Request new SSH key and certificate files, which can be used to log in to the entry nodes without a password.
