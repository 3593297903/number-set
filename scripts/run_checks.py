"""Run source/release checks from a clean checkout with fresh ignored QA data."""
import argparse
import hashlib
import json
import os
import sys
import time
import uuid
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('source', 'release'))
    parser.add_argument('--dist-dir', type=Path)
    args, extra = parser.parse_known_args()
    project = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(project), str(project / 'src')]
    os.chdir(project)
    dist = (args.dist_dir or project / 'dist/NumberTool').resolve()
    hashes = {}
    if args.mode == 'release':
        for name in ('NumberTool.exe', 'NumberVerify.exe'):
            path = dist / name
            if not path.is_file():
                parser.error(f'Build the folder distribution first; missing {path}')
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()

    import pytest
    from tests.integration import test_output_paths
    from tests.release import support

    qa = project / 'qa/checks' / (args.mode + '-' + uuid.uuid4().hex)
    qa.mkdir(parents=True)
    test_output_paths.QA = qa
    support.ROOT = qa / 'existing-release'
    support.ROOT.mkdir()
    if hashes:
        (qa / 'candidate-exes.json').write_text(
            json.dumps({'sha256': hashes}, indent=2) + '\n', encoding='utf-8')

    class IsolatedQA:
        def pytest_configure(self, config):
            from tests import conftest

            @pytest.fixture
            def isolated_tmp_path():
                path = qa / 'tmp' / uuid.uuid4().hex
                path.mkdir(parents=True)
                return path

            conftest.tmp_path = isolated_tmp_path

    targets = (['tests/test_project.py', 'tests/unit', 'tests/integration']
               if args.mode == 'source' else ['tests/release', '--dist-dir', str(dist)])
    options = ['-q', *targets, '-p', 'no:cacheprovider',
               '--junitxml', str(qa / 'tests.xml'), *extra]
    print(f'Fresh QA directory: {qa}', flush=True)
    started = time.time()
    code = int(pytest.main(options, plugins=[IsolatedQA()]))
    (qa / 'run.json').write_text(json.dumps({
        'mode': args.mode, 'exitcode': code, 'pytest_args': options,
        'started_unix': started, 'finished_unix': time.time(),
        'executable_sha256': hashes,
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
