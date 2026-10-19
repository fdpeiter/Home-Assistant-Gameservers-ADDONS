# Share any game server through Playit.gg

This standalone add-on is optional. It works with Enshrouded, other game add-ons
in this repository, and game servers elsewhere on your LAN. One agent can serve
multiple tunnels. Friends need only the public game address and any game password.
No public home IP, router forwarding, or VPN client on friends' PCs is required.
Check Playit's current plans for TCP/UDP availability and tunnel limits.

## Install in Home Assistant

1. Open **Settings → Add-ons → Add-on Store → ⋮ → Repositories** and add
   `https://github.com/fdpeiter/Home-Assistant-Gameservers-ADDONS`.
2. Refresh/check for updates, then install **Playit.gg Game Server Tunnels**.
   This add-on currently supports amd64 hosts.
3. Sign in at [Playit.gg](https://playit.gg/) and use its
   [Docker agent setup](https://playit.gg/account/setup/wizard/new-account/docker/docker-name)
   to create an agent and obtain its secret key. You do not need to run the
   supplied Docker command: this add-on already includes the agent.
4. In the add-on's **Configuration**, set:

   ```yaml
   secret_key: "PASTE-YOUR-PLAYIT-AGENT-SECRET-KEY"
   ```

5. Save and start the Playit add-on. Check its logs and confirm the agent is
   online in Playit's dashboard. Optionally enable **Start on boot** and
   **Watchdog** in HA. Keep the key private; do not share it with players.

## Configure a tunnel for a game

1. Install and start your chosen game server. In that game add-on's **Network**
   settings, publish the required game ports on the HA host.
2. Test the game on the LAN using `HA_LAN_IP:HOST_PORT`.
3. In Playit's dashboard, add a tunnel assigned to this shared agent. Choose the
   protocol the game actually needs (UDP, TCP, or both), and the needed port count.
4. Set the **local address** to the HA host's LAN IP and **local port** to the
   game's published host port. For games on another machine, use that machine's
   LAN IP and listening port. Allow the connection through any local firewall.
5. Give players the **public address and external port assigned by Playit**.
   The external port may differ from the internal game port.

**Do not use `127.0.0.1` for another add-on.** Playit runs in its own container;
loopback points to the Playit container, not the game or HA host. Reserve a fixed
LAN IP for HA so your tunnel destinations remain valid.

Games requiring multiple ports need the corresponding tunnel(s); some protocols
advertise addresses inside game packets or require matching external ports, so
generic TCP/UDP tunneling alone is not a guarantee of compatibility with every
game. Test joining from a friend's connection. Proxy protocol should remain off
unless the game explicitly supports it.

## Enshrouded example: only UDP 15637

1. In **Enshrouded Dedicated Server**, set a strong game password and keep the
   **15637/UDP → 15637** host mapping enabled. Start the game add-on.
2. In Playit's dashboard create just this tunnel:

   | Setting | Value |
   | --- | --- |
   | Agent | This standalone Playit agent |
   | Type/protocol | Custom UDP / UDP only |
   | Port count | `1` |
   | Local IP | Your HA host's LAN IP, e.g. `192.168.1.50` |
   | Local port | `15637` |
   | Proxy protocol | Disabled |

3. Friends add `PLAYIT_PUBLIC_IP:PUBLIC_PORT` under
   **Steam → View → Game Servers → Favorites → +**, then join the favorite in
   Enshrouded using the game password. Use Playit's assigned external port,
   not necessarily 15637. If Steam requires a numeric address, use the public
   IPv4 displayed by Playit or resolve the assigned hostname.

With only that tunnel configured, only the selected UDP game endpoint is public.
The host mapping also makes it reachable on your LAN. Keep HA's dashboard port
8123 and administration services out of your tunnels. The shared agent follows
dashboard settings; it does not enforce a local allowlist against account changes.

## Add other games or disable sharing

Add another tunnel to the same agent using the next game's LAN IP, published
port(s) and required protocol. No changes to the game add-on's image or code
are needed. Each tunnel can be disabled/deleted separately in Playit's dashboard.

Stop the Playit add-on to turn off all tunnels belonging to this agent; your
game servers remain running. Disable **Start on boot** to keep sharing off after
a reboot. Stopping one game does not stop the shared agent or its other tunnels.

The key remains in HA options and `/data/playit-secret`. To remove credentials,
stop/uninstall the add-on and revoke the agent key in Playit. Treat backups
containing the add-on's configuration as private.

## Migrating from the earlier combined version

If you installed the earlier Enshrouded 1.1.0 that bundled Playit, stop it first.
The rewritten Enshrouded add-on has no Playit settings. HA
may not offer an automatic downgrade: back up `/share/enshrouded`, reinstall
Enshrouded from this repository if needed, and configure only its game options.
Keep the UDP 15637 host mapping enabled. Saves stay in `/share/enshrouded`.

Move the agent secret to this separate Playit add-on and change the existing
tunnel destination from `127.0.0.1` to your HA host's LAN IP. Run only one copy
of an agent with the same key. You can retain the existing tunnel's public address.

Sources: [Official agent and key setup](https://github.com/playit-cloud/playit-agent),
[Playit service](https://playit.gg/),
[Enshrouded Steam favorites](https://enshrouded.zendesk.com/hc/en-us/articles/16454683440541-Favorite-Server-via-IP).
