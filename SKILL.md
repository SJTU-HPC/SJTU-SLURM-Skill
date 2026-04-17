---
name: sjtu-hpc
description: Log in to the SJTU HPC platform (also known as "交我算") as the user to perform job queries, submissions, cancellations, and data management. Use this skill when the user requests operations related to HPC or "交我算".
metadata:
  {
    "openclaw":
      {
        "emoji": "🦞",
        "homepage": https://github.com/SJTU-HPC/SJTU-SLURM-Skill,
      }
  }
---

# sjtu-hpc

## Overview

Use this skill to log in to the SJTU HPC (交我算) platform as the user, acting on their behalf to perform personal job queries, submissions, cancellations, and data management operations.

General Principles:

- **Risk-aware operations**: Deleting user's data and interrupting running jobs are risky operations. Before performing any risky operation, always confirm with the user that they clearly understand the impact of the operation and agree to its execution.
- private credentials: All user's credential files (like SSH key, certificate, API token, etc...) should be stored in the `credentials` directory under workspace (e.g., `~/.openclaw/workspace/default/credentials`). **Do Not store user's password** , if you received any attachment from user containing their password, delete it once you get a valid token.

## Quick Start

1. Ensure HPC API token file is available in the workspace, which should be stored in `credentials` directory. If not, request a new token.
2. For each user request, analyze whether you need to log in to an HPC entry node to perform the operation remotely. You can ask more questions to clarify any ambiguous parts of the request.
   - If user wants to know its storage quota usage or update its account (like password, binding Email/jAccount, preferred contact method), then you can meet the requirement directly by calling HPC API with the token.
   - if user is talking about job or its data, then you have to select an entry node to do remote operation. In this case, take the following steps.
3. Ensure SSH keys and certificates are available in the workspace, which should be stored in `credentials` directory. If not, request a new SSH certificate for the user. Remind the user that requesting a certificate will trigger two-factor authentication.
4. For each user request need remote operation, identify the node group/partition the user is interested in and the operation type to select the correct entry node.
5. Use the SSH certificate to connect to the corresponding entry node based on the cluster and operation type, execute the user's requested operations on it.

## Ensure Token Available

Before calling any HPC API, ensure there is a valid token in the credentials directory. Go through the following steps:

1. Check whether `hpc_token` file exists in the `credentials` directory under workspace. If it exists, goto step 2, otherwise goto step 3.
2. Try to refresh the token with `scripts/refresh_token.py --workspace "path_to_workspace"`. If success, then you have ensured a valid token and can safely skip the following steps. If the request is refused (which means the token has expired), then continue to step 3. If the request reports internal error, act according to the rules in [Error Handling section](#error-handling) .
3. Tell the user you are going to request a new token, ask for their HPC username and password. To avoid password leak, advise user to upload a text file instead of providing passwords directly in the chat window.
4. Request token with `python scripts/req_token.py "username" "password" --workspace "path_to_workspace"` . The token will be saved as `hpc_token` in the `credentials` directory under workspace. If script failed, act according to the rules in [Error Handling section](#error-handling) .
5. **Remove password file**: If you got user's password from any files, delete them now to avoid password leak. Never include the plain password in talk messages.

## HPC API

Here are some HPC API path you can call when users want to know their storage quota usage or update their account:

- `GET /quota`: query the storage quota data of user or its related group account.
- `GET /user`: query user's account information.
- `PATCH /user`: update some field of user's account, including password, binding Email/jAccount, preferred contact method.

Only these tasks can be done through HPC API. **Do NOT try to use API for any other user requirements.**

Before you call any API, you must consult the API's online documentation (https://api.hpc.sjtu.edu.cn/doc/index.html#/) to understand the calling conventions of the target API. Use the token in `credentials` directory if authorization is required. Ask for user's HPC name or group account if they are needed and has not been provided during the talk.
There may be more paths in the documentation than what we listed here. Don't care, you should not need to call other paths.

## Entry Node Selection Rules

Select the appropriate entry node based on the node group and operation type the user is interested in.

HPC cluster has 3 node groups: pi, sy (思源) , kp (鲲鹏) . Partitions belong to node groups. If user does not explicitly specify a node group but only provides a target partition or a target storage, look up the corresponding node group from this table:

| node group | partition                                                      | storage    |
| ---------- | -------------------------------------------------------------- | ---------- |
| pi         | cpu, debug, dgx2, huge, 192c6t                                 | lustre     |
| kp         | debugarm, arm128c256g, scnet_arm                               |            |
| sy         | small, 64c512g, el9, debug64c512g, win32, a100, a800, debug100 | dssg(gpfs) |

Then select the entry node according to this table:

| business | node group | entry node               |
| -------- | ---------- | ------------------------ |
| job      | pi         | pilogin.hpc.sjtu.edu.cn  |
| job      | sy         | sylogin.hpc.sjtu.edu.cn  |
| job      | kp         | armlogin.hpc.sjtu.edu.cn |
| data     | pi, kp     | data.hpc.sjtu.edu.cn     |
| data     | sy         | sydata.hpc.sjtu.edu.cn   |

## SSH Keys and Certificates

SSH login to entry nodes requires the user's passwordless certificate. The agent should store all credentials (tokens, SSH keys, certificates) in the workspace's `credentials` directory. If no certificate available, follow the steps to request a new SSH certificate:

1. Ask for certificate owner: If you have asked username when requesting token, directly use that username and skip the ask. Otherwise ask for user's HPC username.
2. Make sure user is prepared: Tell the user that requesting the certificate will trigger two-factor authentication via JWB APP (交我办) or Email. Ask user whether it have been prepared to do the authentication.
3. Call synchronous script with long timeout: Give the user a prompt like "Requesting certificate now, please check your JWB App (交我办) or Email...", **Do NOT wait for the user's confirmation before proceeding**. Immediately call the script `req_certificate.py <username> --workspace "path_to_workspace"` with `timeout >= 600s` because the script will block waiting for the user to complete two-factor authentication on another channel.
4. **Handle errors**: After script execution, check the exit code. If non-zero, act according to the rules in [Error Handling section](#error-handling) .

The SSH key and certificate will be saved to the `credentials` directory under workspace.

## Error Handling

If any script execution or API call failed, parse the error message from stderr and inform the user with clear details:

- If the error message indicates "user have not set email or jAccount", **Direct the user** to read the platform documentation: https://docs.hpc.sjtu.edu.cn/accounts/security.html . Ask them to follow the instructions in the documentation to bind their second identity channel (jAccount or email).
- If the error message indicates internal error, tell user the session ID in error message, suggest them to ask help from `hpc@sjtu.edu.cn` with this ID.

## Executing User-Requested Operations on Entry Nodes

Use the SSH key and certificate from the workspace credentials directory to log in to the entry node and remotely execute the user's requested operations:

```bash
ssh -i "/path_to_workspace/credentials/private_key" -o "CertificateFile=/path_to_workspace/credentials/certificate" user@entry_node "command"
```

Note that user data is distributed across multiple shared storage pools, and visible storage varies depending on the node group. The storage where the user's home directory resides also differs:

| node group | mount point | storage information                                                                                              |
| ---------- | ----------- | ---------------------------------------------------------------------------------------------------------------- |
| pi, kp     | /lustre     | Hot storage, Lustre, user home directory is here                                                                 |
| sy         | /dssg       | Hot storage, GPFS, user home directory is here                                                                   |
| pi, sy, kp | /archive    | Cold storage A, NFS, for archived data, writable only on data and sydata nodes, read-only on other nodes         |
| pi, sy, kp | /vault      | Cold storage B, NFS, for archived data, writable only on data and sydata nodes, read-only on other nodes         |
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
