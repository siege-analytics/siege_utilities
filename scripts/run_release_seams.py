"""Clean-kernel acceptance runner for an already built/installed candidate wheel.

No clone, installation, branch mutation, provider calls or environment provisioning.
Run this file WITH the isolated environment's Python. A Git input must be real,
clean and match --expected-sha. Own API archives are independently tree-verified.
Mechanical component diagnostics have a null candidate SHA, a verified real base,
and an explicit expected content tree. Every wheel member must match actual source
and installed bytes. Source-clean notebook and executed evidence remain separate.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

if sys.flags.optimize:
    raise RuntimeError('Acceptance runner refuses Python optimization: assertions must be active')

KEY_DEPENDENCIES = ('pandas','numpy','scipy','geopandas','shapely','pyproj','pyarrow','censusgeocode','matplotlib','nbclient','nbformat','ipykernel')

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inspect_execution(notebook: dict) -> dict:
    """Fail the run on ANY failed/unexecuted/out-of-order cell, even if later cells pass."""
    cells = [(i,c) for i,c in enumerate(notebook['cells']) if c['cell_type']=='code']
    counts = [c.get('execution_count') for _,c in cells]
    failures = []
    for position,cell in cells:
        for output in cell.get('outputs',[]):
            if output.get('output_type')=='error':
                failures.append({'position':position,'id':cell.get('id'),'error':output.get('ename'),'message':output.get('evalue'),'traceback':output.get('traceback',[])})
    in_order = bool(cells) and counts == list(range(1,len(cells)+1))
    return {'passed':in_order and not failures,'code_cells':len(cells),'execution_counts':counts,'all_cells_executed_in_order':in_order,'failing_cells':failures}

def git(repo: Path, *args: str) -> str:
    result = subprocess.run(['git','-C',str(repo),*args],check=True,capture_output=True,text=True,timeout=30)
    return result.stdout.strip()

def source_tree_id(folder: Path) -> str:
    def object_id(kind: bytes, data: bytes) -> bytes:
        return hashlib.sha1(kind+b' '+str(len(data)).encode()+b'\x00'+data).digest()
    def recurse(directory: Path) -> bytes:
        records=[]
        children=sorted(directory.iterdir(),key=lambda p:(p.name+('/' if p.is_dir() else '')).encode())
        for path in children:
            assert not path.is_symlink(), 'source input must not contain symlinks'
            if path.is_dir():
                mode=b'40000'; digest=recurse(path)
            else:
                mode=b'100755' if path.stat().st_mode & 0o111 else b'100644'
                digest=object_id(b'blob',path.read_bytes())
            records.append(mode+b' '+path.name.encode()+b'\x00'+digest)
        return object_id(b'tree',b''.join(records))
    return recurse(folder).hex()

def validate_lane(names: set[str], lane: str) -> dict:
    """Check declared installed dependency lane before any kernel starts."""
    assert lane in ('shapely-only','tobler'), 'Unknown acceptance lane'
    if lane=='shapely-only':
        assert not ({'tobler','duckdb','mapclassify'} & names), 'Shapely/NumPy lane forbids tobler, duckdb and mapclassify'
    else:
        assert {'tobler','mapclassify'} <= names, 'Tobler/mapclassify lane requires both installed dependencies'
    return {'declared_backend':'shapely' if lane=='shapely-only' else 'tobler','declared_classification_backend':'numpy' if lane=='shapely-only' else 'mapclassify'}

def verify_installed_members(package_root: Path, expected: set[str]) -> None:
    """Check installed non-cache package inventory against wheel members."""
    actual={'siege_utilities/'+str(p.relative_to(package_root)) for p in package_root.rglob('*') if p.is_file() and '__pycache__' not in p.relative_to(package_root).parts}
    assert expected == actual, {'missing_installed':sorted(expected-actual),'unexpected_installed':sorted(actual-expected)}

def verified_composition(repo: Path, expected_base_sha: str, receipt_path: Path, expected_tree: str) -> dict:
    receipt=json.loads(receipt_path.read_text())
    assert receipt['diagnostic_only'] is True and receipt['candidate_sha'] is None
    assert receipt['base_sha']==expected_base_sha
    assert Path(receipt['source']).resolve()==repo
    assert not (repo/'.git').exists()
    tree=source_tree_id(repo)
    assert tree==expected_tree==receipt['candidate_tree']
    assert receipt['diagnostic_id']=='local-diagnostic-'+tree
    base_manifest=Path(receipt['base_source_manifest'])
    base_commit=Path(receipt['base_commit_receipt'])
    assert sha256(base_manifest)==receipt['base_source_manifest_sha256']
    assert sha256(base_commit)==receipt['base_commit_receipt_sha256']
    base=json.loads(base_manifest.read_text())
    api=json.loads(base_commit.read_text())
    assert api['sha']==base['candidate_sha']==expected_base_sha
    assert source_tree_id(Path(base['source']))==api['tree']['sha']==receipt['base_tree']
    actual={str(p.relative_to(repo)):{'sha256':sha256(p),'mode':'100755' if p.stat().st_mode & 0o111 else '100644'} for p in repo.rglob('*') if p.is_file()}
    assert actual==receipt['all_source_files'],'composition source changed since mechanical assembly'
    inputs=receipt_path.parent/'inputs'
    assert sha256(inputs/'source-manifest.json')==receipt['1826_owner_manifest_sha256']
    assert sha256(inputs/'candidate-vs-develop35d.patch')==receipt['1826_full_patch_sha256']
    assert sha256(inputs/'1801-components.patch')==receipt['1801_component_patch_sha256']
    owner=json.loads((inputs/'source-manifest.json').read_text())
    for item in owner['paths_changed_vs_develop']:
        if item['path']!='CHANGELOG.md':
            assert sha256(repo/item['path'])==item['draft_sha256']
    return {'candidate_sha':None,'candidate_tree':tree,'candidate_branch':None,'candidate_source_kind':receipt['source_kind'],'diagnostic_only':True,'diagnostic_id':receipt['diagnostic_id'],'base_sha':expected_base_sha,'base_tree':receipt['base_tree'],'composition_manifest':str(receipt_path),'composition_manifest_sha256':sha256(receipt_path)}

def candidate_provenance(repo: Path, expected_sha: str, wheel: Path, source_manifest: Path | None = None, composition_manifest: Path | None = None, expected_composition_tree: str | None = None) -> dict:
    extra={}
    assert not (source_manifest is not None and composition_manifest is not None)
    # A component composition has no Git candidate SHA. Its REAL base and content tree are separate.
    if composition_manifest is not None:
        assert expected_composition_tree is not None
        extra=verified_composition(repo,expected_sha,composition_manifest.resolve(),expected_composition_tree)
        candidate=None
        candidate_tree=extra['candidate_tree']
        branch=None
        source_kind=extra['candidate_source_kind']
    # Exact API archive is a supported source input, never a fabricated Git checkout.
    elif source_manifest is not None:
        receipt=json.loads(source_manifest.read_text())
        assert receipt['candidate_sha']==expected_sha
        assert Path(receipt['source']).resolve()==repo.resolve()
        assert receipt['tree_verified'] is True
        assert not (repo/'.git').exists()
        candidate=receipt['candidate_sha']
        candidate_tree=source_tree_id(repo)
        api_commit=json.loads((source_manifest.parent/'source-commit.json').read_text())
        assert api_commit['sha']==expected_sha
        assert candidate_tree==api_commit['tree']['sha'], 'archive source differs from actual GitHub commit tree'
        assert candidate_tree==receipt['candidate_tree'], 'archive source changed since acquisition'
        branch=None
        source_kind=receipt['source_kind']
    else:
        assert git(repo,'rev-parse','--show-toplevel') == str(repo.resolve())
        candidate = git(repo,'rev-parse','HEAD')
        assert candidate == expected_sha, (candidate,expected_sha)
        assert not git(repo,'status','--porcelain'), 'candidate repository must be clean'
        candidate_tree=git(repo,'rev-parse','HEAD^{tree}')
        branch=git(repo,'branch','--show-current')
        source_kind='verified clean Git checkout' 
    assert sys.prefix != sys.base_prefix, 'run with a declared isolated virtualenv Python'
    import siege_utilities as su
    origin = Path(su.__file__).resolve()
    assert origin.is_relative_to(Path(sys.prefix).resolve()), 'installed library must come from isolated env, not checkout shadowing'
    library_version = metadata.version('siege-utilities')
    assert su.__version__ == library_version
    # Verify ALL shipped package members, including non-Python data.
    # Distribution metadata/RECORD alone is not evidence of imported code identity.
    package_root = origin.parent
    wheel_members={}
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if name.startswith('siege_utilities/') and not name.endswith('/'):
                installed = package_root.parent / name
                assert installed.read_bytes() == archive.read(name), f'installed/wheel mismatch: {name}'
                wheel_members[name]=hashlib.sha256(archive.read(name)).hexdigest()
    verify_installed_members(package_root,set(wheel_members))
    project = __import__('tomllib').loads((repo/'pyproject.toml').read_text())
    assert project['project']['version'] == library_version
    # Compare declared source to every shipped package member, including data.
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if name.startswith('siege_utilities/') and not name.endswith('/'):
                assert (repo/name).read_bytes() == archive.read(name), f'candidate/wheel mismatch: {name}'
    dependencies={p:metadata.version(p) for p in KEY_DEPENDENCIES}
    for optional in ('tobler','mapclassify'):
        try:
            dependencies[optional]=metadata.version(optional)
        except metadata.PackageNotFoundError:
            pass
    return {'candidate_sha':candidate,'candidate_tree':candidate_tree,'candidate_branch':branch,'candidate_source_kind':source_kind,'candidate_source':str(repo),'library_version':library_version,'library_origin':str(origin),'wheel_sha256':sha256(wheel),'wheel_name':wheel.name,'wheel_members_sha256':wheel_members,'env_prefix':sys.prefix,'python_executable':sys.executable,'python_version':sys.version,'key_dependencies':dependencies,'runner_file':str(Path(__file__).resolve()),'runner_sha256':sha256(Path(__file__)),'python_optimization':sys.flags.optimize,'source_trust_boundary':'Actual GitHub API acquisition receipts are retained locally and re-verified against source bytes; not refetched per run',**extra}

def run(args: argparse.Namespace) -> int:
    import nbclient
    import nbformat
    from jupyter_client import KernelManager
    from jupyter_client.kernelspec import KernelSpecManager

    repo = args.repo.resolve()
    notebook_path = args.notebook.resolve()
    wheel = args.wheel.resolve()
    provenance = candidate_provenance(repo,args.expected_sha,wheel,args.source_provenance,args.composition_provenance,args.expected_composition_tree)
    names={dist.metadata['Name'].lower() for dist in metadata.distributions() if dist.metadata['Name']}
    provenance.update(validate_lane(names,args.lane))
    args.runs.mkdir(parents=True,exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix='release-seams-',dir=args.runs.resolve()))
    source_hash = sha256(notebook_path)
    source = nbformat.read(notebook_path,as_version=4)
    assert all(c.get('execution_count') is None and not c.get('outputs') for c in source.cells if c.cell_type=='code'), 'source notebook must be execution-clean'
    started = datetime.now(timezone.utc).isoformat()
    provenance.update({'run_id':run_dir.name,'started_at':started,'source_notebook_sha256':source_hash,'source_notebook':str(notebook_path),'fixture_kind':'synthetic deterministic rectangles and CSV transport','external_services_certified':False,'acceptance_lane':args.lane})
    manifest_path = run_dir/'manifest.json'
    manifest_path.write_text(json.dumps(provenance,indent=2)+'\n')
    freeze = sorted(f"{dist.metadata['Name']}=={dist.version}" for dist in metadata.distributions() if dist.metadata['Name'])
    (run_dir/'dependencies.txt').write_text('\n'.join(freeze)+'\n')
    kernel_home = run_dir/'home'
    kernel_home.mkdir()
    cwd = run_dir/'work'
    cwd.mkdir()
    for folder in ('tmp','cache','config','jupyter-runtime'):
        (run_dir/folder).mkdir()
    kernel_env = {
        'HOME':str(kernel_home),'TMPDIR':str(run_dir/'tmp'),'XDG_CACHE_HOME':str(run_dir/'cache'),'XDG_CONFIG_HOME':str(run_dir/'config'),
        'JUPYTER_RUNTIME_DIR':str(run_dir/'jupyter-runtime'),'MPLCONFIGDIR':str(run_dir/'config'/'matplotlib'),
        'SIEGE_UTILITIES_CACHE_DIR':str(run_dir/'cache'/'siege_utilities'),'SIEGE_OUTPUT':str(run_dir/'output'),
        'SU_ACCEPTANCE_OUTPUT':str(run_dir/'output'),'SU_ACCEPTANCE_MANIFEST':str(manifest_path),
        'SU_ACCEPTANCE_CANDIDATE_SHA':provenance.get('candidate_sha') or '',
        'SU_ACCEPTANCE_DIAGNOSTIC_ID':provenance.get('diagnostic_id',''),'SU_ACCEPTANCE_BASE_SHA':provenance.get('base_sha',''),'PYTHONNOUSERSITE':'1','PYTHONPATH':'','MPLBACKEND':'Agg',
    }
    kernels = run_dir/'kernels'
    kernel_dir = kernels/'release-seams'
    kernel_dir.mkdir(parents=True)
    kernel_spec = {'argv':[sys.executable,'-I','-m','ipykernel_launcher','-f','{connection_file}'],'display_name':'Release seams isolated wheel','language':'python','env':kernel_env}
    (kernel_dir/'kernel.json').write_text(json.dumps(kernel_spec,indent=2)+'\n')
    manager = KernelSpecManager(kernel_dirs=[str(kernels)])
    km = KernelManager(kernel_name='release-seams',kernel_spec_manager=manager)
    client = nbclient.NotebookClient(source,km=km,timeout=args.timeout,allow_errors=True,resources={'metadata':{'path':str(cwd)}})
    startup_error = None
    try:
        clean_env={'PATH':str(Path(sys.prefix)/'bin')+os.pathsep+os.defpath,'LANG':'C.UTF-8','PYTHONNOUSERSITE':'1'}
        with (run_dir/'kernel.stdout.log').open('w') as kernel_stdout, (run_dir/'kernel.stderr.log').open('w') as kernel_stderr:
            client.execute(cwd=str(cwd),env=clean_env,stdout=kernel_stdout,stderr=kernel_stderr)
    except Exception as error:
        # Preserve interrupted/failed runs rather than discarding the partially executed notebook.
        startup_error = {'type':type(error).__name__,'message':str(error)}
    finally:
        if km.has_kernel:
            km.shutdown_kernel(now=True)
        executed = run_dir/'release_seams.executed.ipynb'
        nbformat.write(source,executed)
    verdict = inspect_execution(source)
    verdict['runner_error'] = startup_error
    verdict['passed'] = verdict['passed'] and startup_error is None
    verdict['source_unchanged'] = sha256(notebook_path) == source_hash
    verdict['passed'] = verdict['passed'] and verdict['source_unchanged']
    transcript = []
    stderr = []
    for position,cell in enumerate(source.cells):
        if cell.cell_type!='code':
            continue
        transcript.append(f"\nCELL {position} {cell.get('id')} count={cell.get('execution_count')}\n")
        for out in cell.get('outputs',[]):
            if out.output_type=='stream':
                (stderr if out.name=='stderr' else transcript).append(out.text)
            elif out.output_type=='error':
                stderr.append('\n'.join(out.get('traceback',[]))+'\n')
            elif out.output_type in ('display_data','execute_result'):
                transcript.append(out.get('data',{}).get('text/plain',''))
    (run_dir/'stdout.log').write_text(''.join(transcript))
    (run_dir/'stderr.log').write_text(''.join(stderr))
    provenance.update({'finished_at':datetime.now(timezone.utc).isoformat(),'executed_notebook_sha256':sha256(executed),'source_notebook_sha256_after':sha256(notebook_path),'verdict':verdict})
    provenance['output_hashes']={str(p.relative_to(run_dir)):sha256(p) for p in sorted((run_dir/'output').rglob('*')) if p.is_file()}
    manifest_path.write_text(json.dumps(provenance,indent=2)+'\n')
    (run_dir/'verdict.json').write_text(json.dumps(verdict,indent=2)+'\n')
    print(json.dumps({'run':str(run_dir),'candidate':provenance['candidate_sha'],'tree':provenance['candidate_tree'],'passed':verdict['passed'],'code_cells':verdict['code_cells'],'execution_counts':verdict['execution_counts'],'failing_cells':[{'position':f['position'],'id':f['id'],'error':f['error'],'message':f['message']} for f in verdict['failing_cells']],'runner_error':startup_error},indent=2))
    return 0 if verdict['passed'] else 1

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',required=True,type=Path)
    parser.add_argument('--expected-sha',required=True)
    parser.add_argument('--source-provenance',type=Path,help='Verified own API archive receipt; no Git metadata required or claimed')
    parser.add_argument('--composition-provenance',type=Path,help='Own mechanically assembled NON-Git diagnostic source receipt; expected-sha is its actual base commit')
    parser.add_argument('--expected-composition-tree',help='Explicit expected content-tree identity for component diagnostics, not a Git commit')
    parser.add_argument('--wheel',required=True,type=Path)
    parser.add_argument('--notebook',required=True,type=Path)
    parser.add_argument('--runs',required=True,type=Path)
    parser.add_argument('--lane',choices=('shapely-only','tobler'),required=True)
    parser.add_argument('--timeout',type=int,default=180)
    return run(parser.parse_args())

if __name__=='__main__':
    raise SystemExit(main())
