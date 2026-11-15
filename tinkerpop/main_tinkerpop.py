#!/usr/bin/env python3
# GraphGenie for TinkerPop: Cypher queries are sent to Gremlin Server
# and translated to Gremlin by the cypher-for-gremlin plugin.
# Reuses the original Testing/generator/mutator code from the project root without modifying it.
# Run from this folder so that ./graphgenie.ini and ./logs are used.

import os
import sys
import time
import configparser

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from main import Testing
from query_generator import RandomCypherGenerator
from query_mutator import CypherQueryMutator
from gremlin_schema_scanner import GremlinSchemaScanner
from cypher_client import new_client, translate

# null marker used by cypher-for-gremlin translations (normalized only by the cypher processor)
CYPHER_NULL = "  cypher.null"

class TinkerPopTesting(Testing):
    def __init__(self):
        self.init_testing_configs()
        self.start_time = time.time()
        if os.path.exists(self.logpath):
            self.init_log()
        self.log("***** Testing TinkerPop (cypher-for-gremlin) *****\n")
        self.log("\tmulti_threading={}\n".format(self.multi_threading))
        self.log("\tvariant={}\n".format(self.variant))
        self.client = new_client(self.ip, self.port, pool_size=8)

    # log/return result+time; time covers only the Gremlin execution, measured on the client side
    def execute_ret_result_time(self, query, log_str):
        query_result = None
        query_time = -1
        try:
            gremlin = translate(self.client, query)
            start_time = time.time()
            rows = self.client.submit(gremlin).all().result()
            query_time = (time.time()-start_time)*1000
            if len(rows)>0:
                query_result = list(rows[0].values())[0]
                if query_result==CYPHER_NULL:
                    query_result = None
        except Exception as e:
            self.except_log('\nQuery:{}\nInfo:{}\n'.format(query, str(e)))
            return None, -1
        self.executed_allquery += 1
        self.log("No.{} {} Query=\"{}\"\n\tQuery Result={}\n\tQuery Time={}\n".format(self.executed_allquery, log_str, query, query_result, query_time))
        self.executed_query_num += 1
        return query_result, query_time

if __name__ == "__main__":
    print("=====GraphGenie (TinkerPop)=====")
    os.makedirs("logs", exist_ok=True)
    config = configparser.ConfigParser()
    config.read('graphgenie.ini')
    ip = config['default']['ip']
    port = int(config['default']['port'])
    username = config['default']['username']
    password = config['default']['password']

    test = TinkerPopTesting()
    schema_scanner = GremlinSchemaScanner(ip, port, username, password)
    node_labels, edge_labels, node_properties, connectivity_matrix = schema_scanner.scan()

    random_cypher_generator = RandomCypherGenerator(node_labels, edge_labels, node_properties, connectivity_matrix)
    cypher_query_mutator = CypherQueryMutator(node_labels, edge_labels, node_properties, connectivity_matrix)
    test.testing(random_cypher_generator, cypher_query_mutator)
