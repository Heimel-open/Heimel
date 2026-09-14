#!/usr/bin/env python3
import json
import os
import statistics
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = Path('/tmp/heimel-tgrep-index')
QUERIES = [
    'REHT',
    'Veritas',
    'NO_DIRECT_EFFECT_PATH',
    'authority',
    'permit',
    'effect',
    'admission',
    'evidence',
    'runtime',
    'fail closed',
]
RUNS = 30


def run(cmd, *, check=True, capture=False):
    return subprocess.run(
        cmd,
        cwd=ROOT,
        check=check,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.PIPE if capture else subprocess.DEVNULL,
        text=True,
    )


def elapsed(cmd):
    t0 = time.perf_counter()
    p = run(cmd, check=False)
    return time.perf_counter() - t0, p.returncode


def sample(cmd):
    vals = []
    codes = []
    for _ in range(RUNS):
        dt, rc = elapsed(cmd)
        vals.append(dt * 1000.0)
        codes.append(rc)
    vals.sort()
    return {
        'median_ms': statistics.median(vals),
        'mean_ms': statistics.mean(vals),
        'p95_ms': vals[max(0, int(len(vals) * 0.95) - 1)],
        'min_ms': min(vals),
        'max_ms': max(vals),
        'return_codes': sorted(set(codes)),
    }


def count_matches(tool, query, extra=None):
    extra = extra or []
    if tool == 'rg':
        cmd = ['rg', '-F', '--no-heading', '--color', 'never', query, '.'] + extra
    else:
        cmd = ['tgrep', '-F', '--index-path', str(INDEX), '--', query, '.'] + extra
    p = run(cmd, check=False, capture=True)
    return len(p.stdout.splitlines()), p.returncode


def main():
    print('BASE_SHA', run(['git', 'rev-parse', 'HEAD'], capture=True).stdout.strip())
    print('RG_VERSION', run(['rg', '--version'], capture=True).stdout.splitlines()[0])
    print('TGREP_VERSION', run(['tgrep', '--version'], capture=True).stdout.splitlines()[0])
    files = int(run(['bash', '-lc', 'rg --files | wc -l'], capture=True).stdout.strip())
    size_kb = int(run(['du', '-sk', '.'], capture=True).stdout.split()[0])
    print('REPO_FILES', files)
    print('REPO_KB', size_kb)

    if INDEX.exists():
        run(['rm', '-rf', str(INDEX)])
    t0 = time.perf_counter()
    p = run(['tgrep', 'index', '.', '--index-path', str(INDEX)], check=False, capture=True)
    index_s = time.perf_counter() - t0
    print('INDEX_RC', p.returncode)
    print('INDEX_SECONDS', round(index_s, 4))
    print('INDEX_STDERR', p.stderr.strip().replace('\n', ' | '))
    idx_kb = int(run(['du', '-sk', str(INDEX)], capture=True).stdout.split()[0])
    print('INDEX_KB', idx_kb)

    results = []
    for q in QUERIES:
        rg_count, rg_rc = count_matches('rg', q)
        tg_count, tg_rc = count_matches('tgrep', q)
        rg_stats = sample(['rg', '-F', '--no-heading', '--color', 'never', q, '.'])
        tg_stats = sample(['tgrep', '-F', '--index-path', str(INDEX), '--', q, '.'])
        results.append({
            'query': q,
            'rg_count': rg_count,
            'tgrep_count': tg_count,
            'rg_rc': rg_rc,
            'tgrep_rc': tg_rc,
            'rg': rg_stats,
            'tgrep_disk': tg_stats,
            'disk_speedup_median': (rg_stats['median_ms'] / tg_stats['median_ms']) if tg_stats['median_ms'] else None,
        })
    print('DISK_RESULTS_JSON', json.dumps(results, sort_keys=True))

    server = subprocess.Popen(
        ['tgrep', 'serve', '.', '--index-path', str(INDEX)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        ready = False
        for _ in range(100):
            st = run(['tgrep', 'status', '.', '--index-path', str(INDEX)], check=False, capture=True)
            if st.returncode == 0:
                ready = True
                break
            time.sleep(0.1)
        print('SERVER_READY', ready)

        server_results = []
        for q in QUERIES:
            rg_stats = sample(['rg', '-F', '--no-heading', '--color', 'never', q, '.'])
            tg_stats = sample(['tgrep', '-F', '--index-path', str(INDEX), '--', q, '.'])
            server_results.append({
                'query': q,
                'rg': rg_stats,
                'tgrep_server': tg_stats,
                'server_speedup_median': (rg_stats['median_ms'] / tg_stats['median_ms']) if tg_stats['median_ms'] else None,
            })
        print('SERVER_RESULTS_JSON', json.dumps(server_results, sort_keys=True))

        sentinel = ROOT / 'tools' / '.tgrep_bench_sentinel.tmp'
        sentinel.write_text('HEIMEL_TGREP_SENTINEL_927461\n', encoding='utf-8')
        detect_t0 = time.perf_counter()
        found = False
        attempts = 0
        while time.perf_counter() - detect_t0 < 5.0:
            attempts += 1
            p = run(['tgrep', '-F', '--index-path', str(INDEX), '--', 'HEIMEL_TGREP_SENTINEL_927461', '.'], check=False, capture=True)
            if p.returncode == 0 and 'HEIMEL_TGREP_SENTINEL_927461' in p.stdout:
                found = True
                break
            time.sleep(0.02)
        print('WATCH_EDIT_FOUND', found)
        print('WATCH_EDIT_DETECT_MS', round((time.perf_counter() - detect_t0) * 1000.0, 3))
        print('WATCH_EDIT_ATTEMPTS', attempts)
        sentinel.unlink(missing_ok=True)

        run(['git', 'switch', '-c', 'bench-switch-probe'])
        branch_file = ROOT / 'tools' / '.tgrep_branch_sentinel.tmp'
        branch_file.write_text('HEIMEL_BRANCH_SENTINEL_841205\n', encoding='utf-8')
        branch_t0 = time.perf_counter()
        branch_found = False
        attempts = 0
        while time.perf_counter() - branch_t0 < 5.0:
            attempts += 1
            p = run(['tgrep', '-F', '--index-path', str(INDEX), '--', 'HEIMEL_BRANCH_SENTINEL_841205', '.'], check=False, capture=True)
            if p.returncode == 0 and 'HEIMEL_BRANCH_SENTINEL_841205' in p.stdout:
                branch_found = True
                break
            time.sleep(0.02)
        print('WATCH_BRANCH_FOUND', branch_found)
        print('WATCH_BRANCH_DETECT_MS', round((time.perf_counter() - branch_t0) * 1000.0, 3))
        print('WATCH_BRANCH_ATTEMPTS', attempts)
        branch_file.unlink(missing_ok=True)
        run(['git', 'switch', '-'])
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()

    # Measure explicit reindex cost after an edit with no server.
    probe = ROOT / 'tools' / '.tgrep_reindex_probe.tmp'
    probe.write_text('HEIMEL_REINDEX_SENTINEL_365190\n', encoding='utf-8')
    t0 = time.perf_counter()
    p = run(['tgrep', 'index', '.', '--index-path', str(INDEX)], check=False, capture=True)
    reindex_s = time.perf_counter() - t0
    print('REINDEX_RC', p.returncode)
    print('REINDEX_SECONDS', round(reindex_s, 4))
    print('REINDEX_STDERR', p.stderr.strip().replace('\n', ' | '))
    found = run(['tgrep', '-F', '--index-path', str(INDEX), '--', 'HEIMEL_REINDEX_SENTINEL_365190', '.'], check=False, capture=True)
    print('REINDEX_EDIT_FOUND', found.returncode == 0 and 'HEIMEL_REINDEX_SENTINEL_365190' in found.stdout)
    probe.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
