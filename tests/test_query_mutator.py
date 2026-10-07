import json
from pathlib import Path
import subprocess
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE_QUERY = (
    'MATCH ()-[]-(zpxqxffp:Director) '
    'WHERE zpxqxffp IS NOT NULL AND True '
    'RETURN DISTINCT count(zpxqxffp) ORDER BY -1+1 SKIP 0'
)


class EquivalentQueryGenerationTests(unittest.TestCase):
    def generate_queries(self, target):
        # Isolate the generator so an infinite loop fails without hanging tests.
        script = f'''
import json
import random
from query_mutator import CypherQueryMutator

random.seed(1)
mutator = CypherQueryMutator(['Director'], ['DIRECTED'], {{}}, [[0]])
mutator.graphdb = 'neo4j'
mutator.language = 'cypher'
mutator.graph_pattern_mutation = 1
mutator.random_symbol_len = 8
mutator.mutated_query_num = {target}
queries, rules = mutator.generate_equivalent_queries({BASE_QUERY!r})
print(json.dumps([queries, rules]))
'''
        try:
            result = subprocess.run(
                [sys.executable, '-c', script],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=3,
                check=True,
            )
        except subprocess.TimeoutExpired:
            self.fail(f'Equivalent query generation did not finish for target {target}')
        queries, rules = json.loads(result.stdout)
        self.assertEqual(len(queries), len(rules))
        self.assertTrue(all(isinstance(query, str) and query for query in queries))
        return queries

    def test_returns_when_initial_mutations_exceed_target(self):
        self.assertGreaterEqual(len(self.generate_queries(10)), 12)

    def test_returns_when_initial_mutations_equal_target(self):
        self.assertEqual(len(self.generate_queries(12)), 12)

    def test_adds_recursive_mutations_until_target(self):
        self.assertEqual(len(self.generate_queries(20)), 20)


if __name__ == '__main__':
    unittest.main()
