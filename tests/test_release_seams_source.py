"""Owned source/runner governance tests, NOT a substitute for library execution."""
import ast
import json
from pathlib import Path
import unittest
import tempfile
import importlib.util

REPO_ROOT=Path(__file__).resolve().parents[1]
_spec=importlib.util.spec_from_file_location("release_seams_runner",REPO_ROOT/"scripts"/"run_release_seams.py")
_runner=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_runner)
inspect_execution=_runner.inspect_execution
validate_lane=_runner.validate_lane
verify_installed_members=_runner.verify_installed_members

ROOT=REPO_ROOT/"notebooks"/"acceptance"

def cell(count=1,outputs=None):
    return {'cell_type':'code','id':f'cell-{count}','execution_count':count,'outputs':outputs or []}

class RunnerVerdictTests(unittest.TestCase):
    def test_complete_success(self):
        self.assertTrue(inspect_execution({'cells':[cell(1),cell(2)]})['passed'])
    def test_fail_then_success_is_failure(self):
        error={'output_type':'error','ename':'AssertionError','evalue':'expected400 actual0','traceback':['test']}
        verdict=inspect_execution({'cells':[cell(1,[error]),cell(2)]})
        self.assertFalse(verdict['passed'])
        self.assertEqual(verdict['failing_cells'][0]['message'],'expected400 actual0')
    def test_unexecuted_cell_fails(self):
        self.assertFalse(inspect_execution({'cells':[cell(1),cell(None)]})['passed'])
    def test_out_of_order_counts_fail(self):
        self.assertFalse(inspect_execution({'cells':[cell(2),cell(1)]})['passed'])
    def test_empty_notebook_cannot_pass(self):
        self.assertFalse(inspect_execution({'cells':[]})['passed'])

class ProvenanceGuardTests(unittest.TestCase):
    def test_tobler_requires_mapclassify(self):
        with self.assertRaises(AssertionError):
            validate_lane({'tobler'},'tobler')
    def test_shapely_forbids_mapclassify(self):
        with self.assertRaises(AssertionError):
            validate_lane({'mapclassify'},'shapely-only')
    def test_unknown_lane_fails_closed(self):
        with self.assertRaises(AssertionError):
            validate_lane({'tobler','mapclassify'},'undeclared-backend')
    def test_actual_lane_declarations(self):
        self.assertEqual(validate_lane(set(),'shapely-only'),{'declared_backend':'shapely','declared_classification_backend':'numpy'})
        self.assertEqual(validate_lane({'tobler','mapclassify'},'tobler'),{'declared_backend':'tobler','declared_classification_backend':'mapclassify'})
    def test_shapely_forbids_alternative_interpolation_backends(self):
        for dependency in ('tobler','duckdb'):
            with self.subTest(dependency=dependency),self.assertRaises(AssertionError):
                validate_lane({dependency},'shapely-only')
    def _inventory(self,extra=None,missing=False):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            package=Path(directory)/'siege_utilities'
            package.mkdir()
            if not missing:
                (package/'current.py').write_text('real fixture bytes\n')
            if extra:
                path=package/extra
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text('stale fixture bytes\n')
            verify_installed_members(package,{'siege_utilities/current.py'})
    def test_exact_installed_inventory_passes(self):
        self._inventory()
    def test_unexpected_installed_module_fails(self):
        with self.assertRaises(AssertionError):
            self._inventory(extra='stale.py')
    def test_missing_wheel_member_fails(self):
        with self.assertRaises(AssertionError):
            self._inventory(missing=True)
    def test_bytecode_cache_is_not_a_stale_module(self):
        self._inventory(extra='__pycache__/current.cpython-313.pyc')
    def test_standalone_bytecode_outside_cache_fails(self):
        with self.assertRaises(AssertionError):
            self._inventory(extra='stale.pyc')

class NotebookSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notebook=json.loads((ROOT/'release_seams.ipynb').read_text())
        cls.code=[c for c in cls.notebook['cells'] if c['cell_type']=='code']
    def test_all_cells_parse_and_are_execution_clean(self):
        self.assertGreaterEqual(len(self.code),17)
        for c in self.code:
            ast.parse(c['source'])
            self.assertIsNone(c['execution_count'])
            self.assertEqual(c['outputs'],[])
    def test_unique_valid_ids(self):
        ids=[c['id'] for c in self.notebook['cells']]
        self.assertEqual(len(ids),len(set(ids)))
        for value in ids:
            self.assertRegex(value,r'^[A-Za-z0-9_-]{1,64}$')
    def test_required_hygiene_headers(self):
        cells=self.notebook['cells']
        self.assertTrue(cells[0]['source'].startswith('# '))
        self.assertIn('## What this shows',cells[0]['source'])
        self.assertTrue(cells[-1]['source'].startswith('## Related'))
        self.assertEqual(sum(c['source'].startswith('## Related') for c in cells),1)
    def test_no_siege_function_monkeypatches(self):
        allowed={'censusgeocode.CensusGeocode','gpd','gpd.GeoDataFrame'}
        patches=[]
        for c in self.code:
            for node in ast.walk(ast.parse(c['source'])):
                if isinstance(node,ast.Call) and ast.unparse(node.func)=='patch.object':
                    patches.append(ast.unparse(node.args[0]))
        self.assertGreater(len(patches),0)
        self.assertTrue(set(patches)<=allowed,patches)
    def test_no_xfail_or_skipping_capabilities(self):
        source='\n'.join(c['source'] for c in self.code)
        for forbidden in ('pytest.xfail','pytest.skip','if HAS_','except: pass'):
            self.assertNotIn(forbidden,source)
    def test_no_home_path_in_source(self):
        for c in self.notebook['cells']:
            self.assertNotRegex(c['source'],r'/home/|/Users/')
    def test_backend_edge_oracles_are_identical_not_adaptive(self):
        by_id={c['id']:c['source'] for c in self.code}
        for identity,name in [('classification-and-map-output','expected'),('classification-numpy-upper-inclusive','upper_inclusive')]:
            assignments=[n for n in ast.walk(ast.parse(by_id[identity])) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)]
            self.assertEqual(len(assignments),1)
            self.assertIsInstance(assignments[0].value,ast.List, 'backend-specific conditional would certify a known defect')
            self.assertEqual(ast.literal_eval(assignments[0].value),[0,0,0,1,1,-1])
    def test_pricing_error_requires_exact_index_context(self):
        source=next(c['source'] for c in self.code if c['id']=='candidate-analytics-pricing-order')
        self.assertIn("'ordering at response index 0'",source)
    def test_design_pins_not_misattributed_to_original_issue(self):
        source=next(c['source'] for c in self.notebook['cells'] if c['id']=='candidate-seam-policy')
        self.assertIn('#1826 design/implementation contract pins',source)
        self.assertIn('not requirements stated by #1422',source)
    def test_declares_fail_closed_manifest_and_fresh_output(self):
        source=self.code[0]['source']
        self.assertIn("os.environ['SU_ACCEPTANCE_MANIFEST']",source)
        self.assertIn('assert not OUTPUT.exists()',source)
        self.assertIn('su.__version__',source)
        self.assertIn('su.__file__',source)

if __name__=='__main__':
    unittest.main(verbosity=2)
