#!/usr/bin/env bash
# Start the old (buggy) GDBMS versions used in the GraphGenie paper, plus the latest versions for regression checks.
# Run from the project root: bash paper_bugs/setup_servers.sh
# Needs Docker. TinkerPop (port 8182) and the current Neo4j (port 7687) are started separately (see tinkerpop/README.md).
set -e
cd "$(dirname "$0")/.."
DL=paper_bugs/downloads
mkdir -p "$DL"

# Neo4j 5.1.0 / 5.4.0 with recommendations-50 (bugs #12988, #12991, #12996 and the 5.4.0 artifact)
for spec in "5.1.0:17687" "5.4.0:27687"; do
  v=${spec%%:*}; port=${spec##*:}; name=neo4j-$(echo "$v" | tr . -)
  docker rm -f "$name" >/dev/null 2>&1 || true
  docker volume rm -f "$name-data" >/dev/null 2>&1 || true
  docker run --rm -i -v "$name-data:/data" "neo4j:$v-community" \
    neo4j-admin database load --from-stdin --overwrite-destination=true neo4j < data/recommendations-50.dump
  docker run -d --name "$name" -p "$port:7687" -v "$name-data:/data" -e NEO4J_AUTH=neo4j/12344321 "neo4j:$v-community"
done

# Neo4j 4.4.12 with the POLE dataset (bug #12968)
[ -f "$DL/pole-43.dump" ] || curl -fsSL -o "$DL/pole-43.dump" https://github.com/neo4j-graph-examples/pole/raw/main/data/pole-43.dump
docker rm -f neo4j-4-4-12 >/dev/null 2>&1 || true
docker volume rm -f neo4j-4-4-12-data >/dev/null 2>&1 || true
docker run --rm -v neo4j-4-4-12-data:/data -v "$PWD/$DL:/dumps:ro" neo4j:4.4.12-community \
  neo4j-admin load --from=/dumps/pole-43.dump --database=neo4j --force
docker run -d --name neo4j-4-4-12 -p 37687:7687 -v neo4j-4-4-12-data:/data -e NEO4J_AUTH=neo4j/12344321 neo4j:4.4.12-community

# Neo4j 5.4.0 with Cybersecurity (bugs #13041, #13034) and the latest Neo4j with POLE / Cybersecurity (regression checks)
[ -f "$DL/pole-50.dump" ] || curl -fsSL -o "$DL/pole-50.dump" https://github.com/neo4j-graph-examples/pole/raw/main/data/pole-50.dump
[ -f "$DL/cyber-security-ad-50.dump" ] || curl -fsSL -o "$DL/cyber-security-ad-50.dump" https://github.com/neo4j-graph-examples/cybersecurity/raw/main/data/cyber-security-ad-50.dump
for spec in "neo4j-5-4-0-cyber:28687:5.4.0-community:cyber-security-ad-50.dump" \
            "neo4j-latest-pole:48687:community:pole-50.dump" \
            "neo4j-latest-cyber:49687:community:cyber-security-ad-50.dump"; do
  IFS=: read -r name port tag dump <<< "$spec"
  docker rm -f "$name" >/dev/null 2>&1 || true
  docker volume rm -f "$name-data" >/dev/null 2>&1 || true
  docker run --rm -i -v "$name-data:/data" "neo4j:$tag" \
    neo4j-admin database load --from-stdin --overwrite-destination=true neo4j < "$DL/$dump"
  docker run -d --name "$name" -p "$port:7687" -v "$name-data:/data" -e NEO4J_AUTH=neo4j/12344321 "neo4j:$tag"
done

# RedisGraph 2.10.15 (bugs #2744, #2858, #2859, #2865, #3071) and FalkorDB latest (its successor)
docker rm -f redisgraph-2-10-15 falkordb-latest >/dev/null 2>&1 || true
docker run -d --name redisgraph-2-10-15 --platform linux/amd64 -p 16379:6379 redislabs/redisgraph:2.10.15
docker run -d --name falkordb-latest -p 26379:6379 falkordb/falkordb:latest

# clean Neo4j latest, used as reference (oracle) for the RedisGraph dataset
docker rm -f neo4j-oracle >/dev/null 2>&1 || true
docker run -d --name neo4j-oracle -p 47687:7687 -e NEO4J_AUTH=neo4j/12344321 neo4j:community

# AgensGraph v2.13.0 (bug #609) and v2.14.1 (latest), graph t with 100 edges
for spec in "v2.13.0:15432" "v2.14.1:25432"; do
  v=${spec%%:*}; port=${spec##*:}; name=agensgraph-$(echo "$v" | tr . -)
  docker rm -f "$name" >/dev/null 2>&1 || true
  docker run -d --name "$name" -p "$port:5432" -e POSTGRES_PASSWORD=agensgraph "bitnine/agensgraph:$v"
done
sleep 20
SQL="CREATE GRAPH t; SET graph_path = t; $(for k in $(seq 1 100); do printf "CREATE (:n {id:%d})-[:e]->(:n {id:%d}); " "$k" $((k+1000)); done)"
for name in agensgraph-v2-13-0 agensgraph-v2-14-1; do echo "$SQL" | docker exec -i "$name" psql -q -U postgres >/dev/null; done

echo "waiting for Neo4j containers..."
for port in 17687 27687 28687 37687 47687 48687 49687; do until nc -z 127.0.0.1 "$port"; do sleep 2; done; done
sleep 10
echo "all servers ready"
