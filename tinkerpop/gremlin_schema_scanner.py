#!/usr/bin/env python3

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from schema_scanner import SchemaScanner
from cypher_client import new_client

class GremlinSchemaScanner(SchemaScanner):
    def gremlin_init(self):
        self.client = new_client(self.ip, self.port)

    def scan(self):
        self.gremlin_init()
        self.node_count = self.execute_query("g.V().count()")[0]
        self.edge_count = self.execute_query("g.E().count()")[0]
        self.node_labels = sorted(self.execute_query("g.V().label().dedup()"))
        self.edge_labels = sorted(self.execute_query("g.E().label().dedup()"))
        self.print_schema_info()
        self.scan_properties()
        self.scan_connectivity()
        self.client.close()
        return self.node_labels, self.edge_labels, self.node_properties, self.connectivity_matrix

    def scan_properties(self):
        self.node_properties = {}
        for each_node_label in self.node_labels:
            self.node_properties[each_node_label] = self.execute_query(
                "g.V().hasLabel(l).properties().key().dedup()", {"l": each_node_label})

    def scan_connectivity(self):
        self.connectivity_matrix = []
        for each_node_label in self.node_labels:
            matrix_row = []
            for each_test_node_label in self.node_labels:
                if each_node_label==each_test_node_label:
                    matrix_row.append(0)
                else:
                    query_result = self.execute_query(
                        "g.V().hasLabel(a).out().hasLabel(b).limit(1).count()",
                        {"a": each_node_label, "b": each_test_node_label})[0]
                    matrix_row.append(0 if query_result==0 else 1)
            self.connectivity_matrix.append(matrix_row)
        self.print_connectivity()

    def execute_query(self, query, bindings=None):
        return self.client.submit(query, bindings).all().result()

if __name__ == "__main__":
    scanner = GremlinSchemaScanner("127.0.0.1", 8182, "", "")
    node_labels, edge_labels, node_properties, connectivity_matrix = scanner.scan()
    print("Node properties: {}".format(node_properties))
