# Enshrouded Dedicated Server

Community Home Assistant OS add-on for **amd64/x86-64** hosts. Runs the Windows
dedicated server (Steam app 2278520) using SteamCMD, Wine and Xvfb. ARM hosts,
including Raspberry Pi, are unsupported. Wine compatibility is unofficial.

## Installation

1. Add the GitHub URL of the repository containing this folder to the HA add-on
   store, refresh the store, then install **Enshrouded Dedicated Server**.
2. Set `server_name`, a strong `server_password`, and `slots` (1–16).
3. For LAN access, set the Network mapping to **15637/UDP → 15637** and start the add-on.
   First startup downloads the server and can take several minutes.
4. Check the add-on log and `/share/enshrouded/logs` for server readiness.
5. Test locally using your HA host's LAN IP, e.g. `192.168.1.50:15637`.
   In Steam use **View → Game Servers → Favorites → +**, then select the
   favorite in Enshrouded's server browser and enter the password.

`update_on_start` defaults to true. Turning it off skips updates on subsequent
starts; a missing executable always triggers installation. Updates require
outbound internet access. Clients and server need compatible versions.

If SteamCMD reports `App '2278520' state is 0x6 after update job`, the updater
backs up the Enshrouded and redistributables app manifests under
`/data/steamcmd-manifest-backups`, then retries validation with rebuilt metadata.
Saves, game settings and installed server content are retained. The full output
is available in the add-on log and `/data/steamcmd-update.log`. Repeated failures
stop startup rather than silently launching an outdated server; check free disk
space and Steam connectivity if recovery does not succeed.

Allow ample CPU, RAM and disk capacity beyond Home Assistant's own needs.
Keen recommends 16 GB RAM and at least 30 GB free SSD storage for a dedicated
server; see [hardware guidance](https://enshrouded.zendesk.com/hc/en-us/articles/16055628734109-Recommended-Server-Specifications).

## Data and configuration

All server files persist under `/share/enshrouded`:

| Path | Contents |
| --- | --- |
| `server/` | Steam installation and `enshrouded_server.json` |
| `savegame/` | Worlds |
| `logs/` | Game logs |

Wine's prefix is stored in the add-on's persistent `/data/wine` directory.
HA options override name, slots, bind IP, query port, save/log paths and
`userGroups` on every startup. The wrapper creates one password-protected
Friend group (building, inventory and altar access; no kick/ban privileges).
Other JSON fields, such as difficulty settings, are preserved. Stop the add-on
before editing those fields. Custom role groups are overwritten.

Stop the server before copying or restoring saves. Include `/share/enshrouded`
in your backups; verify that your chosen HA backup includes the share folder.
Shutdown/save behavior through Wine must be verified on your host before
relying on unattended restarts. The image was built and the real dedicated server
reached its online running state and answered a Steam query on UDP 15637 under
Docker Desktop. HAOS installation and joining with a game client remain untested.

## Friends connecting externally

Friends need access to the **game service**, not the HA dashboard.

For CGNAT without client software for friends, install the separate optional
[Playit.gg add-on](../playit_gg/README.md) and follow its
[Enshrouded tunnel example](../playit_gg/DOCS.md#enshrouded-example-only-udp-15637).
It targets the HA host's published UDP 15637 port and can also share other games.
Enshrouded itself does not contain or require Playit.

### Public IPv4 and router port forwarding

1. Reserve a fixed LAN IP for the HA host in your router's DHCP settings.
2. Forward **UDP 15637** on your router to **HA_LAN_IP:15637**. If you changed
   the add-on's host port mapping, forward to that host port instead.
3. Allow that UDP port in any intervening firewall. With two routers, both
   need forwarding, or the upstream router needs bridge mode.
4. Give friends `PUBLIC_IPV4:15637` (or your external port) and the game password.
   They add it to Steam favorites as above. A dynamic DNS hostname can track
   a changing public IP; use the resolved IP if the Steam dialog requires it.
5. Test from a friend's connection. Testing your public address from your own
   LAN may fail if the router does not support NAT loopback.

Keep HA port 8123 and administration/file-sharing services private. The official
server configuration currently specifies query port 15637; do not add unrelated
TCP or Steam port ranges merely because older guides list them.

If the router's WAN IPv4 differs from your public IPv4, investigate upstream
NAT. A WAN address in `100.64.0.0/10` or private address ranges commonly means
CGNAT or another router. Ask the ISP for a public IPv4, or use a VPN route below.
Port forwarding alone cannot bypass ISP CGNAT.

### Private VPN (including CGNAT)

Use Tailscale on a supported always-on LAN device as a **subnet router**, advertise
the HA host's route (ideally just its `/32`), approve the route, and invite friends
to your tailnet. Friends install Tailscale, accept/use the subnet route and connect
to `HA_LAN_IP:15637`. Linux clients may need subnet route acceptance enabled.
Configure access rules to allow friends only UDP 15637 to the HA host, and remove
any broader default allow rule that would also grant them access to your LAN.

Sharing a subnet-router machine alone does **not** share its subnet routes;
friends must join the tailnet for this arrangement. Check account user limits
before choosing it. Ordinary HTTP reverse proxies and HA remote-access URLs
do not provide the UDP game connection.

## References

- [Official server configuration](https://enshrouded.zendesk.com/hc/en-us/articles/16055441447709-Dedicated-Server-Configuration)
- [Official roles and passwords](https://enshrouded.zendesk.com/hc/en-us/articles/19191581489309-Server-Roles-Configuration)
- [Official Steam favorites instructions](https://enshrouded.zendesk.com/hc/en-us/articles/16454683440541-Favorite-Server-via-IP)
- [Tailscale subnet routers](https://tailscale.com/docs/features/subnet-routers)
- [Tailscale sharing limitations](https://tailscale.com/docs/features/sharing)
