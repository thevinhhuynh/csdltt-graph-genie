#!/usr/bin/env python3
# Gremlin client able to send Cypher queries to the cypher-for-gremlin OpProcessor ("cypher")

from gremlin_python.driver.client import Client
from gremlin_python.driver.request import RequestMessage
from gremlin_python.driver.serializer import GraphSONSerializersV3d0, Standard

class CypherGraphSONSerializer(GraphSONSerializersV3d0):
    # gremlinpython resolves processors by attribute name; "cypher" takes the same args as a standard eval
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cypher = Standard(self.standard._writer)

def new_client(ip, port, pool_size=None):
    url = "ws://{}:{}/gremlin".format(ip, port)
    return Client(url, "g", pool_size=pool_size, message_serializer=CypherGraphSONSerializer())

def cypher_message(query):
    return RequestMessage(processor="cypher", op="eval", args={"gremlin": query})

# CypherOpProcessor does not enforce evaluationTimeout, so a heavy query can run forever.
# Translate with EXPLAIN (no execution), then run the Gremlin through the standard processor,
# which stops it after evaluationTimeout (gremlin-server-cypher.yaml).
def translate(client, query):
    rows = client.submit(cypher_message("EXPLAIN " + query)).all().result()
    return rows[0]["translation"]
