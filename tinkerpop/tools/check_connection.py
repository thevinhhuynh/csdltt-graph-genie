#!/usr/bin/env python3
# Check that Gremlin Server answers both Gremlin and Cypher (via cypher-for-gremlin) queries
# usage: python tools/check_connection.py [ip] [port]

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from cypher_client import new_client, cypher_message

ip = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
port = int(sys.argv[2]) if len(sys.argv) > 2 else 8182
client = new_client(ip, port)
try:
    print("[Gremlin] vertex labels:", client.submit("g.V().label().groupCount()").all().result())
    print("[Gremlin] edge labels:", client.submit("g.E().label().groupCount()").all().result())
    query = "MATCH (n:Movie) RETURN count(n)"
    print("[Cypher] {}:".format(query), client.submit(cypher_message(query)).all().result())
finally:
    client.close()
