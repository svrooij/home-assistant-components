# Proxmox VE (beta)

This is a beta version of the Proxmox integration for Home Assistant. It's provided as through [hacs](https://hacs.xyz/) at the moment, violating the [HACS manifest guidelines](https://hacs.xyz/docs/publish/start) (because it should not be used to provided beta versions of integrations).

> **Please note:** This integration is not officially supported by Proxmox. It's a community effort and not affiliated with Proxmox Server Solutions GmbH.

## Features

This integration provides the following features:

- **Container/VM status:** The status of all containers and VMs.
- **CPU Usage** The CPU usage of all containers and VMs.
- **Memory Usage** The memory usage of all containers and VMs.
- **Actions** Start, stop, shutdown, reboot, and suspend containers and VMs.

## Installation

1. Add the repository to HACS as a custom repository:
   - **URL:** `svrooij/home-assistant-components`
   - **Category:** Integration
2. Install the integration through HACS `Proxmox VE (beta)` and restart Home Assistant.

## Usage

1. Add the integration through the UI.
1. Enter the required details:
   - **Host:** The IP address or hostname of your Proxmox server.
   - **Port:** The port of your Proxmox server (default: `8006`).
   - **Username:** The username to login with.
   - **Realm:** The realm to login with (default: `pam`).
   - **Token:** The token to login with [see token](#api-token).
   - **Token ID:** The token ID to login with [see token](#api-token).
   - **Verify SSL:** Whether to verify the SSL certificate of the Proxmox server.

### API Token

1. Open Proxmox web interface.
1. Go to `Datacenter` > `Permissions`.
1. Click on `API Tokens` and click on `Add`.
1. Select the user you want to create the token for.
1. Enter a token id for the token (needed to setup this integration).
1. Enable `Privileges separation`.
1. Click on `Add`.
1. Copy the token and use it in the integration setup.

