---
name: sjtu-hpc
description: Log in to the SJTU HPC platform (also known as "交我算") as the user to perform job queries, submissions, cancellations, and data management. Use this skill when the user requests operations related to HPC or "交我算".
---

# sjtu-hpc

## Overview

Use this skill to log in to the SJTU HPC (交我算) platform as the user, acting on their behalf to perform personal job queries, submissions, cancellations, and data management operations.

General Principles:
- **Risk-aware operations**: Deleting user's data and interrupting running jobs are risky operations. Before performing any risky operation, always confirm with the user that they clearly understand the impact of the operation and agree to its execution.

## Quick Start

1. Analyze user requirements and clarify any ambiguous parts by asking follow-up questions. Identify the node group/partition the user is interested in and the operation type to select the correct entry node.
2. Ensure SSH keys and certificates are available in the workspace, which should be stored in `credentials` directory. If not, request a new SSH certificate for the user. Remind the user that requesting a certificate will trigger two-factor authentication.
3. Use the SSH certificate to connect to the corresponding entry node based on the cluster and operation type, execute the user's requested operations on it.

## Entry Node Selection Rules

Select the appropriate entry node based on the node group and operation type the user is interested in.

HPC cluster has 3 node groups: pi, sy (思源) , kp (鲲鹏) . Partitions belong to node groups. If the user does not explicitly specify a node group but provides a target partition, look up the corresponding node group from this table:

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

### Ensure Token Availiable

Before requesting the certificate, ensure there is a valid token. Go through the following steps:

1. Check whether `hpc_token` file exists in the `credentials` directory under workspace. If it exists, goto step 2, otherwise goto step 3.
2. Try to refresh the token with `scripts/refresh_token.py` . If success, then you have ensured a valid token and can safely skip the following steps. If the request is refused (which means the token has expired), then continue to step 3. If the request reports internal error, act according to the rules in [Error Handling section](#error-handling) .
3. Tell the user you are going to request a new token, ask for their HPC username and password.
4. Request token with `scripts/req_token.py` . It's calling format should like: 

```bash
python scripts/req_token.py "username" "password"
```

The token will be saved as `hpc_token` in the `credentials` directory under workspace. If script failed, act according to the rules in [Error Handling section](#error-handling) .

### Request SSH Certificate 

Once you have a valid token, request the SSH certificate:

1. **Ask for certificate owner**: If you have asked username when requesting token, directly use that username and skip the ask. Otherwise ask for user's HPC username.
2. **Wait for confirmation**: Tell user that certificate request will trigger two-factor authentication so they need to authorize via JWB APP (交我办) or Email. **Only proceed after the user confirms they understand and are ready to authorize.**
2. **Execute with long timeout**: Give user a prompt hint like "Start to request certificate, waiting for your two-factor authentication...". Meanwhile run `req_certificate.py <username>` with `timeout >= 600s` because the script will block waiting for user to complete two-factor authentication on another channel.
3. **Handle errors**: After script execution, check the exit code. If non-zero, act according to the rules in [Error Handling section](#error-handling) .

The SSH key and certificate will be saved to the `credentials` directory under workspace.

### Error Handling

After any script execution, check the exit code. If non-zero, parse the error message from stderr and inform the user with clear details:

- If the error message indicates "user have not set email or jAccount", **Direct the user** to read the platform documentation: https://docs.hpc.sjtu.edu.cn/accounts/security.html . Ask them to follow the instructions in the documentation to bind their second identity channel (jAccount or email).
- If the error message indicates internal error, tell user the session ID in error message, suggest them to ask help from `hpc@sjtu.edu.cn` with this ID.

**Security Note**: Only SSH keys and certificates may be stored. User account passwords must not be stored, nor included in responses.

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

If the user is interested in platform status or personal jobs, use SLURM commands to perform operations like: `sinfo, squeue, sacct, seff, sbatch, scancel, etc...`

Due to different storage pool visibility across node groups, job data computed on a partition can only be viewed on entry nodes belonging to the corresponding node group. Each entry node only allows submitting job to partitions within its own node group.

Never use cold storage data directly for job. If cold storage data is needed, transfer it to hot storage first before using it for job.

Large-scale data transfer operations should be performed on `data.hpc.sjtu.edu.cn` and `sydata.hpc.sjtu.edu.cn`. HPC has multiple cold storages, so before writing data to cold storage, check the free space of these candidates, and select the cold storage with most free space as the write target. If user asks about their data in cold storage and did not clearly specified which one, use the combined virtual filesystem `/union` .

## Resources

### scripts/

- `req_token.py`: Request a new bearer token from HPC API. This is a one-time setup that enables other operations.
- `refresh_token.py`: Refresh an existing bearer token to extend the session without re-authenticating.
- `req_certificate.py`: Request SSH key and certificate files using an existing token, which can be used to log in to the entry nodes without a password.