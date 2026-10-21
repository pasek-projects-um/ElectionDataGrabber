"""Compress this run's evidence once; only control state belongs in the cache."""
import argparse
import json
import tarfile
from pathlib import Path


def package(state_dir, output):
    output.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in state_dir.rglob('*') if p.is_file() and p.name != 'worker.lock')
    archive = output / 'watch-evidence.tar.gz'
    with tarfile.open(archive, 'w:gz') as tar:
        for path in files:
            tar.add(path, arcname=str(path.relative_to(state_dir)), recursive=False)
    manifest = {'files': len(files), 'uncompressed_bytes': sum(p.stat().st_size for p in files),
                'archive_bytes': archive.stat().st_size,
                'scope': 'Candidate discovery evidence; no verified election-results coverage'}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest), flush=True)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', type=Path, default=Path('watch-data'))
    parser.add_argument('--output', type=Path, default=Path('watch-artifact'))
    args = parser.parse_args()
    package(args.state_dir, args.output)


if __name__ == '__main__':
    main()
