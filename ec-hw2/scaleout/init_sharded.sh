#!/usr/bin/env bash
# init_sharded.sh: set up the sharded MongoDB demo cluster. It is safe to run twice.
#
# Purpose
#   1. Start the replica set of each mongod with rs.initiate (one member each):
#      cfgrs (the config server, configsvr: true), shard1rs and shard2rs.
#   2. Wait until each replica set has a primary.
#   3. Add the 2 shards to the router (mongos) with sh.addShard.
#   A step that is already done is skipped, with a message.
# Inputs
#   The running containers of ec-hw2/scaleout/docker-compose.sharded.yml.
# Outputs
#   The cluster settings, stored in the truthlag-sharded_* volumes.
#   It prints the list of shards at the end.
# Run (from the repo root)
#   docker compose -f ec-hw2/scaleout/docker-compose.sharded.yml up -d
#   bash ec-hw2/scaleout/init_sharded.sh
# You should see (the first time)
#   cfgrs: rs.initiate sent / cfgrs: PRIMARY / shard1rs: ... / shard2rs: ...
#   shard1rs: added / shard2rs: added
#   shards: shard1rs=shard1rs/shard1:27018, shard2rs=shard2rs/shard2:27018
# The second time, every step says "already".
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$HERE/docker-compose.sharded.yml"
TRIES=60            # 60 tries x 2 seconds = 2 minutes for each wait

# msh <host:port> <javascript>: run mongosh and print the result.
# mongosh always runs inside the cfg container and connects over the Docker network.
# Why: mongosh needs about 150 MB. A loaded shard uses about 450 MB of its 600 MB, and
# mongos has only 256 MB, so mongosh inside those containers can push them over the
# memory limit, and Docker then kills the database server. cfg uses about 130 MB.
msh() {
  docker compose -f "$COMPOSE_FILE" exec -T cfg \
    mongosh "mongodb://$1/?directConnection=true" --quiet --eval "$2"
}

# wait_for_ping <host:port>: wait until the server answers
wait_for_ping() {
  local hp=$1 i
  for ((i = 1; i <= TRIES; i++)); do
    if [[ "$(msh "$hp" 'db.adminCommand({ping: 1}).ok' 2>/dev/null || true)" == "1" ]]; then
      return 0
    fi
    sleep 2
  done
  echo "STOP: $hp does not answer after $((TRIES * 2)) seconds." >&2
  echo "      Is the cluster running? docker compose -f $COMPOSE_FILE ps -a" >&2
  exit 1
}

# init_replset <service> <port> <replica set name> <extra rs.initiate fields>
init_replset() {
  local svc=$1 port=$2 rs=$3 extra=$4 state i
  wait_for_ping "$svc:$port"
  # rs.status() fails with the code name NotYetInitialized before rs.initiate.
  state=$(msh "$svc:$port" 'try { rs.status().ok } catch (e) { e.codeName }')
  if [[ "$state" == "NotYetInitialized" ]]; then
    msh "$svc:$port" \
      "rs.initiate({_id: '$rs'${extra}, members: [{_id: 0, host: '$svc:$port'}]}).ok" >/dev/null
    echo "$rs: rs.initiate sent"
  elif [[ "$state" == "1" ]]; then
    echo "$rs: already initiated"
  else
    echo "WARNING: $rs: rs.status() says '$state'. Waiting for a primary anyway." >&2
  fi
  for ((i = 1; i <= TRIES; i++)); do
    if [[ "$(msh "$svc:$port" 'db.hello().isWritablePrimary' 2>/dev/null || true)" == "true" ]]; then
      echo "$rs: PRIMARY"
      return 0
    fi
    sleep 2
  done
  echo "STOP: $rs has no primary after $((TRIES * 2)) seconds." >&2
  exit 1
}

# add_shard <replica set name> <host:port>
add_shard() {
  local rs=$1 host=$2 have
  have=$(msh mongos:27017 "db.adminCommand({listShards: 1}).shards.map(s => s._id).includes('$rs')")
  if [[ "$have" == "true" ]]; then
    echo "$rs: already a shard"
    return 0
  fi
  msh mongos:27017 "sh.addShard('$rs/$host').ok" >/dev/null
  echo "$rs: added"
}

# The 3 database servers must be running. (We do not start them here, because Neo4j
# must be stopped first: see the memory rule in SHARDING.md.)
running=$(docker compose -f "$COMPOSE_FILE" ps --status running --services)
for svc in cfg shard1 shard2; do
  if ! grep -qx "$svc" <<<"$running"; then
    echo "STOP: the container '$svc' is not running. Start the cluster first:" >&2
    echo "      docker stop truthlag-neo4j-1" >&2
    echo "      docker compose -f $COMPOSE_FILE up -d" >&2
    exit 1
  fi
done

init_replset cfg 27019 cfgrs ", configsvr: true"
init_replset shard1 27018 shard1rs ""
init_replset shard2 27018 shard2rs ""

# mongos needs a working config server. If it stopped while it waited, start it again.
if ! docker compose -f "$COMPOSE_FILE" ps --status running --services | grep -qx mongos; then
  echo "mongos is not running: starting it"
  docker compose -f "$COMPOSE_FILE" up -d mongos
fi
wait_for_ping mongos:27017

add_shard shard1rs shard1:27018
add_shard shard2rs shard2:27018

echo "shards: $(msh mongos:27017 \
  "db.adminCommand({listShards: 1}).shards.map(s => s._id + '=' + s.host).join(', ')")"
