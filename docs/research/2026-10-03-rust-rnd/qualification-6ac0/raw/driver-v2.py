#!/usr/bin/env python3
"""Bounded orchestration for the Rust CIX/uncix stream qualification.

This is intentionally an orchestrator only: compression and restoration are
always performed by the supplied Rust executables.  It holds no source-sized
buffer and starts every native child in its own process group.
"""
import argparse, hashlib, json, os, pathlib, platform, resource, select, signal, subprocess, sys, time

SOURCE = 32 * 1024 * 1024
PAUSE_AT = 1024 * 1024 + 256
BUF = 64 * 1024
FILE_CAP = 48 * 1024 * 1024
WALL = 120.0
SIZES = (1, 7, 31, 257, 4093, 16384, 65536)

def die(message): raise RuntimeError(message)
def sha_path(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(BUF), b''): h.update(b)
    return h.hexdigest()
def kill_group(p):
    fallback = False
    if p.poll() is None:
        try: os.killpg(p.pid, signal.SIGINT)
        except ProcessLookupError: return False
        try: p.wait(timeout=1)
        except subprocess.TimeoutExpired:
            fallback = True
            try: os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            p.wait()
    return bool(fallback)
def bounded_write(pipe, chunks, deadline):
    os.set_blocking(pipe.fileno(), False)
    for block in chunks:
        view = memoryview(block)
        while view:
            if time.monotonic() >= deadline: die('stdin write wall timeout')
            _, writable, _ = select.select([], [pipe], [], .05)
            if writable:
                n = os.write(pipe.fileno(), view); view = view[n:]
def flags(mode):
    common = ['--fast', '--stream', '--flush-interval', '50ms', '--block-size', '65536B', '--memory', '16MiB']
    return (['--format', 'cixg1', '--threads', '2', '--parallelism', 'blocks'] + common if mode == 'g1'
            else ['--format', 'cixm6', '--threads', '1'] + common)
def output_limit(): resource.setrlimit(resource.RLIMIT_FSIZE, (SOURCE, SOURCE))
def generator():
    state = 0x6a09e667f3bcc909
    sent = turn = 0
    while sent < SOURCE:
        n = min(SIZES[turn % len(SIZES)], SOURCE - sent, PAUSE_AT - sent if sent < PAUSE_AT else SOURCE - sent)
        block = bytearray(n)
        for i in range(n):
            state ^= (state << 13) & ((1 << 64) - 1); state ^= state >> 7; state ^= (state << 17) & ((1 << 64) - 1)
            state &= (1 << 64) - 1; block[i] = (state >> 24) & 0xff
        sent += n; turn += 1
        yield sent, bytes(block)

def live_stream(mode, cix, uncix, archive, work):
    """Feed CIX and a separate Rust decoder concurrently through bounded pipes."""
    enc_err = open(work / 'encoder.stderr', 'wb'); dec_err = open(work / 'partial-decoder.stderr', 'wb')
    enc = subprocess.Popen([cix, *flags(mode), '-c', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                           stderr=enc_err, start_new_session=True)
    dec = subprocess.Popen([uncix, '-c', '--memory', '16MiB', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                           stderr=dec_err, start_new_session=True)
    for f in (enc.stdin, enc.stdout, dec.stdin, dec.stdout): os.set_blocking(f.fileno(), False)
    source = hashlib.sha256(); partial = hashlib.sha256(); generated = generator(); inbuf = bytearray(); to_dec = bytearray()
    sent = archived = decoded = 0; pause_done = False; cix_eof = dec_eof = False; queue_peak = inbuf_peak = 0; readiness_wait = 0.0; started = time.monotonic()
    try:
        with open(archive, 'wb') as af:
            while True:
                if time.monotonic() - started > WALL: die('live stream wall timeout')
                if not inbuf and sent < SOURCE:
                    sent, block = next(generated); inbuf.extend(block); inbuf_peak = max(inbuf_peak, len(inbuf)); source.update(block)
                readers = [dec.stdout]
                if len(to_dec) <= BUF - 4096 and not cix_eof: readers.append(enc.stdout)
                wait_started = time.monotonic(); r, w, _ = select.select(readers, [x for x, q in ((enc.stdin, inbuf), (dec.stdin, to_dec)) if q], [], .05); readiness_wait += time.monotonic() - wait_started
                for f in r:
                    b = os.read(f.fileno(), 4096)
                    if f is enc.stdout:
                        if not b: cix_eof = True
                        else:
                            archived += len(b)
                            if archived > FILE_CAP: die('archive exceeds 48MiB cap')
                            af.write(b); to_dec.extend(b); queue_peak = max(queue_peak, len(to_dec))
                    elif not b: dec_eof = True
                    else: decoded += len(b); partial.update(b); time.sleep(.002)  # deliberately slow consumer
                for f in w:
                    q = inbuf if f is enc.stdin else to_dec
                    n = os.write(f.fileno(), q)
                    del q[:n]
                queue_peak = max(queue_peak, len(to_dec)); inbuf_peak = max(inbuf_peak, len(inbuf))
                if sent == PAUSE_AT and not inbuf and not pause_done:
                    before_archive, before_decoded = archived, decoded
                    deadline = time.monotonic() + .250
                    while time.monotonic() < deadline:
                        readers = [dec.stdout]
                        if len(to_dec) <= BUF - 4096 and not cix_eof: readers.append(enc.stdout)
                        r, w, _ = select.select(readers, [dec.stdin] if to_dec else [], [], .01)
                        for f in r:
                            b = os.read(f.fileno(), 4096)
                            if f is enc.stdout and b:
                                archived += len(b)
                                if archived > FILE_CAP: die('archive exceeds 48MiB cap')
                                af.write(b); to_dec.extend(b); queue_peak = max(queue_peak, len(to_dec))
                            elif f is dec.stdout and not b: dec_eof = True
                            elif f is dec.stdout: decoded += len(b); partial.update(b); time.sleep(.002)
                        for f in w:
                            n = os.write(f.fileno(), to_dec); del to_dec[:n]
                        queue_peak = max(queue_peak, len(to_dec))
                    if enc.stdin is None or decoded < PAUSE_AT:
                        die('idle-open checkpoint lacked post-boundary archive or decoded partial output')
                    pause_done = True
                if sent == SOURCE and not inbuf and enc.stdin is not None:
                    enc.stdin.close(); enc.stdin = None
                if cix_eof and not to_dec and dec.stdin is not None:
                    dec.stdin.close(); dec.stdin = None
                if cix_eof and dec_eof: break
        encoder_status = enc.wait(timeout=max(0.1, WALL - (time.monotonic()-started)))
        decoder_status = dec.wait(timeout=max(0.1, WALL - (time.monotonic()-started)))
        if encoder_status != 0: die('encoder exit nonzero')
        if decoder_status != 0: die('partial Rust decoder exit nonzero')
        if decoded != SOURCE or partial.hexdigest() != source.hexdigest(): die('live Rust decoder did not exactly reconstruct source')
        return {'source_sha256': source.hexdigest(), 'archive_bytes': archived, 'partial_decoded_bytes': decoded,
                'partial_sha256': partial.hexdigest(), 'idle_after_bytes': PAUSE_AT, 'idle_ms':250,
                'max_to_dec_bytes': queue_peak, 'max_inbuf_bytes': inbuf_peak,
                'select_readiness_wait_seconds': readiness_wait, 'consumer_delay_ms_per_read':2,
                'encoder_exit_status':encoder_status, 'live_decoder_exit_status':decoder_status}
    finally:
        kill_group(enc); kill_group(dec); enc_err.close(); dec_err.close()

def decode_fresh(binary, archive, destination):
    err = open(str(destination) + '.stderr', 'wb')
    with open(destination, 'wb') as out:
        p = subprocess.Popen([binary, '-c', '--memory', '16MiB', str(archive)], stdout=out, stderr=err, start_new_session=True, preexec_fn=output_limit)
        try: status = p.wait(timeout=WALL)
        except subprocess.TimeoutExpired: kill_group(p); die('fresh decoder wall timeout')
    err.close()
    if status != 0: die('fresh decoder exit nonzero')
    if destination.stat().st_size > SOURCE: die('restoration exceeds source bound')
    return sha_path(destination)

def reject(uncix, archive, target):
    err = open(str(target)+'.stderr', 'wb')
    p = subprocess.Popen([uncix, '-c', '--memory', '16MiB', str(archive)], stdout=subprocess.PIPE, stderr=err, start_new_session=True)
    os.set_blocking(p.stdout.fileno(), False); emitted = 0; deadline = time.monotonic()+WALL
    while p.poll() is None:
        if time.monotonic() >= deadline: kill_group(p); die('malformed decoder wall timeout')
        r, _, _ = select.select([p.stdout], [], [], .05)
        if p.stdout in r:
            b = os.read(p.stdout.fileno(), 4096); emitted += len(b)
            if emitted > SOURCE: kill_group(p); die('malformed decoder exceeded streamed output cap')
    while True:
        try: b = os.read(p.stdout.fileno(), 4096)
        except BlockingIOError: break
        if not b: break
        emitted += len(b)
        if emitted > SOURCE: die('malformed decoder exceeded streamed output cap')
    status = p.returncode; err.close()
    if status == 0: die('malformed archive unexpectedly decoded')
    return {'archive_bytes':archive.stat().st_size, 'archive_sha256':sha_path(archive), 'decoder_exit_status':status,
            'decoder_emitted_bytes':emitted, 'stderr_path':str(target)+'.stderr'}

def malformed(uncix, archive, work):
    size = archive.stat().st_size
    if size < 2 or size > FILE_CAP: die('archive unsuitable for malformed controls')
    trunc = work/'truncated.cix'
    with open(archive, 'rb') as src, open(trunc, 'wb') as dst:
        remaining = size - 1
        while remaining:
            b = src.read(min(BUF, remaining))
            if not b: die('short archive while truncating')
            dst.write(b); remaining -= len(b)
    truncated = reject(uncix, trunc, work/'truncated.out'); trunc.unlink()
    corrupt = work/'corrupt.cix'; flip = size // 2; position = 0
    with open(archive, 'rb') as src, open(corrupt, 'wb') as dst:
        while True:
            b = bytearray(src.read(BUF))
            if not b: break
            if position <= flip < position + len(b): b[flip-position] ^= 0x80
            dst.write(b); position += len(b)
    corrupted = reject(uncix, corrupt, work/'corrupt.out'); corrupt.unlink()
    return {'truncated':truncated, 'corrupt':corrupted}

def interrupt(mode, cix, work):
    err = open(work/'interrupt.stderr', 'wb')
    p = subprocess.Popen([cix, *flags(mode), '-c', '-'], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                         stderr=err, start_new_session=True)
    def chunks():
        remaining = PAUSE_AT
        while remaining:
            n = min(BUF, remaining); remaining -= n; yield b'Z' * n
    bounded_write(p.stdin, chunks(), time.monotonic()+WALL); time.sleep(.250)
    if p.poll() is not None: die('interrupted encoder exited before SIGINT')
    fallback = kill_group(p); err.close()
    if p.poll() is None: die('interrupted encoder was not reaped')
    if p.returncode == 0: die('interrupted encoder exited zero')
    return {'signal':'SIGINT','exit_status':p.returncode,'sigkill_fallback':fallback}

def empty_control(mode, cix, uncix, work):
    archive, restored = work/'empty.cix', work/'empty.restored'
    with open(archive, 'wb') as out, open(work/'empty-encoder.stderr', 'wb') as err:
        p = subprocess.Popen([cix, *flags(mode), '-c', '-'], stdin=subprocess.DEVNULL, stdout=out,
                             stderr=err, start_new_session=True)
        try: status = p.wait(timeout=WALL)
        except subprocess.TimeoutExpired: kill_group(p); die('empty encoder wall timeout')
    if status != 0 or archive.stat().st_size > FILE_CAP: die('empty encoder failed or exceeded archive cap')
    restored_sha = decode_fresh(uncix, archive, restored)
    if restored_sha != hashlib.sha256(b'').hexdigest(): die('empty restoration mismatch')
    record = {'encoder_exit_status':status, 'archive_bytes':archive.stat().st_size, 'archive_sha256':sha_path(archive),
              'decoder_exit_status':0, 'restored_bytes':restored.stat().st_size, 'restored_sha256':restored_sha}
    archive.unlink(); restored.unlink(); pathlib.Path(str(restored)+'.stderr').unlink(missing_ok=True)
    return record

def m6_held_open_reap(uncix, archive, source_sha256, work):
    """Regression control for the former finish_stream blocking read: feed a
    complete archive, deliberately retain EOF, then terminate/reap the group."""
    err = open(work/'m6-held-open.stderr', 'wb')
    p = subprocess.Popen([uncix, '-c', '--memory', '16MiB', '-'], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=err, start_new_session=True)
    os.set_blocking(p.stdin.fileno(), False); os.set_blocking(p.stdout.fileno(), False)
    decoded = 0; digest = hashlib.sha256(); pending = bytearray()
    deadline = time.monotonic()+WALL
    with open(archive, 'rb') as src:
        while True:
            if not pending:
                b = src.read(BUF)
                if not b: break
                pending.extend(b)
            if time.monotonic() >= deadline: die('held-open M6 feed wall timeout')
            r, w, _ = select.select([p.stdout], [p.stdin] if pending else [], [], .05)
            if p.stdout in r:
                b = os.read(p.stdout.fileno(), 4096)
                if b: decoded += len(b); digest.update(b)
            if p.stdin in w:
                n = os.write(p.stdin.fileno(), pending); del pending[:n]
        # stdin remains intentionally open while the complete plaintext is drained.
        while decoded < SOURCE:
            if time.monotonic() >= deadline: die('held-open M6 drain wall timeout')
            r, _, _ = select.select([p.stdout], [], [], .01)
            if p.stdout in r:
                b = os.read(p.stdout.fileno(), 4096)
                if b: decoded += len(b); digest.update(b)
        time.sleep(.250)
    if p.poll() is not None: die('held-open M6 decoder exited before SIGINT')
    fallback = kill_group(p); err.close()
    if p.poll() is None: die('held-open M6 decoder was not reaped')
    if p.returncode == 0: die('held-open M6 decoder exited zero')
    if decoded != SOURCE or digest.hexdigest() != source_sha256: die('held-open M6 decoder did not emit exact plaintext before EOF')
    return {'signal':'SIGINT','exit_status':p.returncode,'sigkill_fallback':fallback,'decoded_bytes_before_eof':decoded,'decoded_sha256_before_eof':digest.hexdigest()}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('g1','m6')); ap.add_argument('cix'); ap.add_argument('uncix'); ap.add_argument('old_bd2'); ap.add_argument('work', type=pathlib.Path); ap.add_argument('--expected-source-sha', required=True); ns = ap.parse_args()
    started_utc = time.time(); ns.work.mkdir(parents=True, exist_ok=True)
    if sha_path(ns.old_bd2) != 'f9ec393c689c6602a3912ca74a8d83575979dcdf2cb0646ac2760f41cf80db84':
        die('frozen BD2 decoder absent or SHA-256 mismatch')
    archive = ns.work/'stream.cix'; row = 1 if ns.mode == 'g1' else 2
    live = live_stream(ns.mode, ns.cix, ns.uncix, archive, ns.work)
    if live['source_sha256'] != ns.expected_source_sha: die('generated source SHA-256 differs from frozen prehash')
    restored = ns.work/'restored.current'; current = decode_fresh(ns.uncix, archive, restored); restored.unlink()
    old = ns.work/'restored.old'; legacy = decode_fresh(ns.old_bd2, archive, old); old.unlink(); pathlib.Path(str(old)+'.stderr').unlink(missing_ok=True)
    if current != live['source_sha256'] or legacy != live['source_sha256']: die('fresh restoration SHA mismatch')
    restored.unlink(missing_ok=True); pathlib.Path(str(restored)+'.stderr').unlink(missing_ok=True)
    malformed_controls = malformed(ns.uncix, archive, ns.work); empty = empty_control(ns.mode, ns.cix, ns.uncix, ns.work); interrupted = interrupt(ns.mode, ns.cix, ns.work)
    held_open = m6_held_open_reap(ns.uncix, archive, live['source_sha256'], ns.work) if ns.mode == 'm6' else None
    record = {'row_number': row, 'profile_name': ('fast-g1-stream' if ns.mode == 'g1' else 'fast-m6-stream'),
              'mode': ns.mode, 'started_unix_seconds': started_utc, 'ended_unix_seconds': time.time(),
              'hardware': {'machine':platform.machine(), 'processor':platform.processor(), 'os_cpu_count':os.cpu_count()}, 'encoder_argv': [ns.cix, *flags(ns.mode), '-c', '-'],
              'fresh_decoder_argv': [ns.uncix, '-c', '--memory', '16MiB', str(archive)], 'live': live,
              'archive_bytes': archive.stat().st_size, 'archive_sha256': sha_path(archive), 'encoder_sha256': sha_path(ns.cix), 'current_decoder_sha256': sha_path(ns.uncix), 'expected_source_sha256': ns.expected_source_sha,
              'old_bd2_decoder_sha256': sha_path(ns.old_bd2), 'fresh_current_sha256': current,
              'fresh_old_bd2_sha256': legacy, 'empty': empty, 'malformed': malformed_controls, 'interruption': interrupted,
              'm6_complete_archive_held_open': held_open}
    (ns.work/'result.json').write_text(json.dumps(record, sort_keys=True, indent=2)+'\n'); print(json.dumps(record, sort_keys=True))
if __name__ == '__main__':
    try: main()
    except Exception as e: print('stream-qv2: '+str(e), file=sys.stderr); sys.exit(2)
