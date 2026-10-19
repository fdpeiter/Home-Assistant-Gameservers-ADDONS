# Playit.gg Game Server Tunnels

An optional, standalone **amd64** Home Assistant add-on for exposing game servers
through CGNAT. Install once and manage one or more TCP/UDP tunnels in Playit's
dashboard, pointing to the published ports of any game server on your LAN.
Friends connect to the public tunnel addresses without installing software.

Game add-ons do not depend on this add-on and contain no Playit agent or secret.
Install/start it only when wanted; stop it to disable all of its tunnels. Each
game continues running independently. **[Home Assistant setup guide](DOCS.md)**.

Uses the [official Playit agent](https://github.com/playit-cloud/playit-agent)
v1.0.10 with a pinned SHA-256 checksum. Requires a Playit account, outbound
connectivity, and a plan supporting the protocols/number of tunnels you choose.
The agent has no published host ports, no host networking, and no HA API access.
Its secret is kept under `/data` and is not passed in command-line arguments.

Tunnels follow your Playit dashboard configuration; there is no local destination
allowlist. Publish only the game endpoints you intend to share. Protect your
Playit account and game servers with appropriate passwords and permissions.
The image build, daemon startup, secret-file permissions, invalid-key handling
and clean container shutdown were verified under Docker Desktop. Authenticated
public tunneling and HAOS installation still require verification on your host.
