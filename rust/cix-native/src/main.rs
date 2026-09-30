use flate2::{write::DeflateEncoder, Compression, Decompress, FlushDecompress, Status};
use sha2::{Digest, Sha256};
use std::sync::atomic::{AtomicBool, Ordering};
use std::{
    env,
    fs::{self, File, OpenOptions},
    io::{self, Read, Write},
    path::Path,
    process,
    time::{SystemTime, UNIX_EPOCH},
};

mod rank;

const MAGIC: &[u8; 5] = b"CIXG1";
const HEADER: usize = 13;
const END: u8 = 255;
const MAX_BLOCK: u32 = 65536;
static INTERRUPTED: AtomicBool = AtomicBool::new(false);
fn check_interrupted() -> Result<(), String> {
    if INTERRUPTED.load(Ordering::Relaxed) {
        Err("interrupted".into())
    } else {
        Ok(())
    }
}
fn read_poll<R: Read>(
    src: &mut R,
    buffer: &mut [u8],
    fd: i32,
    timeout: Option<std::time::Duration>,
) -> Result<Option<usize>, String> {
    loop {
        check_interrupted()?;
        #[cfg(unix)]
        {
            let slice = std::time::Duration::from_millis(250);
            let wait = timeout.map(|t| t.min(slice)).unwrap_or(slice);
            if !wait_input(fd, wait).map_err(|e| {
                if INTERRUPTED.load(Ordering::Relaxed) {
                    "interrupted".to_string()
                } else {
                    ioerr(e)
                }
            })? {
                return Ok(None);
            }
        }
        match src.read(buffer) {
            Ok(n) => return Ok(Some(n)),
            Err(e) if e.kind() == io::ErrorKind::Interrupted => continue,
            Err(e) => {
                return Err(if INTERRUPTED.load(Ordering::Relaxed) {
                    "interrupted".into()
                } else {
                    ioerr(e)
                })
            }
        }
    }
}
fn read_exact_poll<R: Read>(src: &mut R, mut buffer: &mut [u8], fd: i32) -> Result<(), String> {
    while !buffer.is_empty() {
        match read_poll(src, buffer, fd, None)? {
            Some(0) => return Err("truncated archive".into()),
            Some(n) => {
                let (_, rest) = buffer.split_at_mut(n);
                buffer = rest;
            }
            None => continue,
        }
    }
    Ok(())
}
#[derive(Default)]
struct Opt {
    decode: bool,
    stdout: bool,
    keep: bool,
    force: bool,
    test: bool,
    list: bool,
    level: u8,
    threads: usize,
    memory: usize,
    input: String,
    output: Option<String>,
    route: Option<String>,
    block: Option<u32>,
    stream: bool,
    history: usize,
    independent_blocks: bool,
    flush_interval: Option<std::time::Duration>,
}
fn usage() {
    println!("CIX (pronounced six) native stream compressor (CIXG1; not ZIP/gzip)\nUsage: cix [--stream] [--block-size SIZE] [--memory SIZE] [--threads N] [--history SIZE] [--independent-blocks] [--flush-interval DURATION] [-1..-9] [-c] [-k] [-f] [--route auto|raw|runs|composition|deflate] [-o FILE] FILE...\n       uncix [--stream] [-d|-c|-t|-l] [-k] [-f] [-o FILE] FILE...\n       cixcat FILE...\nUse '-' for standard input/output. Supported routes: raw, runs, exact-rank composition, raw DEFLATE. CIXG1 frames are limited to 65536 bytes.");
}
fn parse() -> Result<Opt, String> {
    let mut o = Opt {
        level: 6,
        threads: 1,
        memory: 512 * 1024 * 1024,
        ..Opt::default()
    };
    let args: Vec<String> = env::args().collect();
    let prog = Path::new(args.first().map(String::as_str).unwrap_or("cix"))
        .file_name()
        .unwrap_or_default()
        .to_string_lossy();
    o.decode = prog == "uncix" || prog == "unsix" || prog == "cixcat";
    o.stdout = prog == "cixcat";
    let mut files = vec![];
    let mut i = 1;
    while i < args.len() {
        let a = &args[i];
        if a == "--help" || a == "-h" {
            usage();
            process::exit(0)
        } else if a == "--version" {
            println!("cix-native {} (CIXG1)", env!("CARGO_PKG_VERSION"));
            process::exit(0)
        } else if a == "-d" {
            o.decode = true
        } else if a == "-c" {
            o.stdout = true
        } else if a == "-k" {
            o.keep = true
        } else if a == "-f" {
            o.force = true
        } else if a == "-t" {
            o.test = true;
            o.decode = true
        } else if a == "-l" {
            o.list = true;
            o.decode = true
        } else if a == "-1"
            || a == "-2"
            || a == "-3"
            || a == "-4"
            || a == "-5"
            || a == "-6"
            || a == "-7"
            || a == "-8"
            || a == "-9"
        {
            o.level = a[1..].parse().unwrap()
        } else if a == "--stream" {
            o.stream = true
        } else if a == "--independent-blocks" {
            o.independent_blocks = true
        } else if a == "--threads"
            || a == "--memory"
            || a == "-o"
            || a == "--output"
            || a == "--route"
            || a == "--block"
            || a == "--block-size"
            || a == "--history"
            || a == "--flush-interval"
        {
            i += 1;
            if i == args.len() {
                return Err(format!("{a} requires a value"));
            }
            match a.as_str() {
                "--threads" => o.threads = args[i].parse().map_err(|_| "invalid thread count")?,
                "--memory" => o.memory = parse_size(&args[i])?,
                "--route" => o.route = Some(args[i].clone()),
                "--block" => o.block = Some(args[i].parse().map_err(|_| "invalid block size")?),
                "--block-size" => {
                    o.block = Some(
                        parse_size(&args[i])?
                            .try_into()
                            .map_err(|_| "block size overflows")?,
                    )
                }
                "--history" => o.history = parse_size(&args[i])?,
                "--flush-interval" => o.flush_interval = Some(parse_duration(&args[i])?),
                _ => o.output = Some(args[i].clone()),
            }
        } else if a.starts_with('-') && a != "-" {
            return Err(format!("unsupported option: {a}"));
        } else {
            files.push(a.clone())
        }
        i += 1
    }
    if files.is_empty() {
        return Err("missing input file".into());
    }
    if files.len() != 1 {
        return Err("this build accepts one input at a time".into());
    }
    o.input = files.remove(0);
    if o.threads == 0 {
        return Err("--threads must be positive".into());
    }
    Ok(o)
}
fn parse_size(s: &str) -> Result<usize, String> {
    let (n, m) = s.split_at(s.find(|c: char| !c.is_ascii_digit()).unwrap_or(s.len()));
    let v: usize = n.parse().map_err(|_| "invalid memory size")?;
    let mul = match m.to_ascii_lowercase().as_str() {
        "" | "b" => 1,
        "k" | "kb" | "kib" => 1024,
        "m" | "mb" | "mib" => 1024 * 1024,
        "g" | "gb" | "gib" => 1024 * 1024 * 1024,
        _ => return Err("size accepts bytes, KiB, MiB or GiB".into()),
    };
    v.checked_mul(mul)
        .ok_or_else(|| "memory size overflow".into())
}
fn parse_duration(s: &str) -> Result<std::time::Duration, String> {
    let (n, unit) = s.split_at(s.find(|c: char| !c.is_ascii_digit()).unwrap_or(s.len()));
    let value: u64 = n.parse().map_err(|_| "invalid flush interval")?;
    let millis = match unit.to_ascii_lowercase().as_str() {
        "ms" => value,
        "" | "s" | "sec" | "secs" => value.checked_mul(1000).ok_or("flush interval overflow")?,
        "m" | "min" | "mins" => value.checked_mul(60_000).ok_or("flush interval overflow")?,
        _ => return Err("flush interval accepts ms, seconds or minutes".into()),
    };
    if millis == 0 {
        return Err("flush interval must be positive".into());
    }
    Ok(std::time::Duration::from_millis(millis))
}
fn put_frame<W: Write>(w: &mut W, r: u8, n: u32, s: u32, h: &[u8; 32]) -> io::Result<()> {
    w.write_all(&[r])?;
    w.write_all(&n.to_le_bytes())?;
    w.write_all(&s.to_le_bytes())?;
    w.write_all(h)
}
fn read_u32<R: Read>(r: &mut R, fd: i32) -> Result<u32, String> {
    let mut b = [0; 4];
    read_exact_poll(r, &mut b, fd)?;
    Ok(u32::from_le_bytes(b))
}
#[cfg(unix)]
fn open_input(path: &str) -> Result<File, String> {
    if path != "-" {
        return File::open(path).map_err(ioerr);
    }
    use std::os::fd::FromRawFd;
    let fd = unsafe { libc::dup(libc::STDIN_FILENO) };
    if fd < 0 {
        return Err(ioerr(io::Error::last_os_error()));
    }
    Ok(unsafe { File::from_raw_fd(fd) })
}
#[cfg(not(unix))]
fn open_input(path: &str) -> Result<File, String> {
    if path == "-" {
        return Err("stdin streaming is not implemented on this platform".into());
    }
    File::open(path).map_err(ioerr)
}
#[cfg(unix)]
fn wait_input(fd: std::os::fd::RawFd, timeout: std::time::Duration) -> io::Result<bool> {
    let mut descriptor = libc::pollfd {
        fd,
        events: libc::POLLIN,
        revents: 0,
    };
    let milliseconds = timeout.as_millis().min(i32::MAX as u128) as i32;
    loop {
        let ready = unsafe { libc::poll(&mut descriptor, 1, milliseconds) };
        if ready >= 0 {
            return Ok(ready != 0);
        }
        let error = io::Error::last_os_error();
        if INTERRUPTED.load(Ordering::Relaxed) {
            return Err(io::Error::new(io::ErrorKind::Interrupted, "interrupted"));
        }
        if error.kind() != io::ErrorKind::Interrupted {
            return Err(error);
        }
    }
}
#[cfg(not(unix))]
fn wait_input(_fd: i32, _timeout: std::time::Duration) -> io::Result<bool> {
    Err(io::Error::new(
        io::ErrorKind::Unsupported,
        "timed pipe reads require Unix poll",
    ))
}
#[cfg(unix)]
fn input_fd(file: &File) -> i32 {
    use std::os::fd::AsRawFd;
    file.as_raw_fd()
}
#[cfg(not(unix))]
fn input_fd(_file: &File) -> i32 {
    -1
}
fn rle(b: &[u8]) -> Vec<u8> {
    let mut o = Vec::new();
    let mut i = 0;
    while i < b.len() {
        let mut j = i + 1;
        while j < b.len() && b[j] == b[i] {
            j += 1
        }
        o.push(b[i]);
        let mut n = (j - i) as u64;
        while n >= 128 {
            o.push((n as u8 & 127) | 128);
            n >>= 7
        }
        o.push(n as u8);
        i = j
    }
    o
}
fn unvar(b: &[u8], p: &mut usize) -> Result<usize, String> {
    let mut v = 0usize;
    for sh in (0..35).step_by(7) {
        if *p >= b.len() {
            return Err("truncated run varint".into());
        }
        let x = b[*p];
        *p += 1;
        v |= ((x & 127) as usize) << sh;
        if x < 128 {
            return Ok(v);
        }
    }
    Err("oversized run varint".into())
}
fn unrle(b: &[u8], n: usize) -> Result<Vec<u8>, String> {
    let (mut p, mut o) = (0, Vec::with_capacity(n));
    while p < b.len() {
        let c = b[p];
        p += 1;
        let k = unvar(b, &mut p)?;
        if k == 0 || o.len().checked_add(k).filter(|&x| x <= n).is_none() {
            return Err("invalid run length".into());
        }
        o.resize(o.len() + k, c)
    }
    if o.len() != n {
        return Err("run output length mismatch".into());
    }
    Ok(o)
}
fn deflate(b: &[u8], level: u8) -> io::Result<Vec<u8>> {
    let mut e = DeflateEncoder::new(Vec::new(), Compression::new(level as u32));
    e.write_all(b)?;
    e.finish()
}
fn entropy(b: &[u8]) -> f64 {
    if b.is_empty() {
        return 0.0;
    }
    let mut counts = [0usize; 256];
    let mut order = Vec::new();
    for &x in b {
        let c = &mut counts[x as usize];
        if *c == 0 {
            order.push(x as usize);
        }
        *c += 1;
    }
    let n = b.len() as f64;
    n.log2()
        - order
            .into_iter()
            .map(|i| counts[i] as f64 * (counts[i] as f64).log2())
            .sum::<f64>()
            / n
}

fn stream_encode(data: &[u8], level: u8, backend: &str) -> Result<Vec<u8>, String> {
    let mut candidates: Vec<(u8, Vec<u8>)> = vec![(0, data.to_vec()), (1, rle(data))];
    if matches!(backend, "cix" | "hybrid") && entropy(&data[..data.len().min(8192)]) < 7.5 {
        candidates.push((2, rank::encode_composition_tiles(data)?));
    }
    if matches!(backend, "deflate" | "hybrid") {
        let compressed = deflate(data, level).map_err(ioerr)?;
        candidates.push((3, compressed));
    }
    // Python min() keeps the first equal-sized candidate; preserve its order.
    let (coder, payload) = candidates
        .into_iter()
        .min_by_key(|(_, payload)| payload.len())
        .ok_or("no CIX substream candidates")?;
    let mut out = Vec::with_capacity(13 + payload.len());
    out.push(1);
    out.push(coder);
    out.extend_from_slice(&(data.len() as u32).to_le_bytes());
    out.extend_from_slice(&(payload.len() as u32).to_le_bytes());
    out.extend_from_slice(&payload);
    Ok(out)
}

fn stream_decode(blob: &[u8], expected: usize) -> Result<Vec<u8>, String> {
    if blob.len() < 10 || blob[0] != 1 {
        return Err("invalid CIX substream descriptor".into());
    }
    let coder = blob[1];
    let n = u32::from_le_bytes(blob[2..6].try_into().unwrap()) as usize;
    let size = u32::from_le_bytes(blob[6..10].try_into().unwrap()) as usize;
    if n != expected || size != blob.len() - 10 {
        return Err("invalid CIX substream lengths".into());
    }
    let payload = &blob[10..];
    match coder {
        0 => {
            if size != n {
                return Err("raw substream size mismatch".into());
            }
            Ok(payload.to_vec())
        }
        1 => unrle(payload, n),
        2 => rank::decode_composition_tiles(payload, n),
        5 => Err("unsupported CIX count-range substream coder".into()),
        3 => inflate(payload, n),
        _ => Err(format!("unsupported CIX substream coder {coder}")),
    }
}
fn inflate(b: &[u8], n: usize) -> Result<Vec<u8>, String> {
    let mut d = Decompress::new(false);
    let mut out = Vec::with_capacity(n.saturating_add(1));
    let status = d
        .decompress_vec(b, &mut out, FlushDecompress::Finish)
        .map_err(|e| format!("DEFLATE: {e}"))?;
    if status != Status::StreamEnd || d.total_in() != b.len() as u64 || out.len() != n {
        return Err("DEFLATE framing/size mismatch".into());
    }
    Ok(out)
}
fn encode<R: Read, W: Write>(
    mut src: R,
    mut dst: W,
    block: u32,
    level: u8,
    forced: Option<&str>,
    input_fd: i32,
    flush_interval: Option<std::time::Duration>,
) -> Result<(), String> {
    dst.write_all(MAGIC).map_err(ioerr)?;
    dst.write_all(&block.to_le_bytes()).map_err(ioerr)?;
    dst.write_all(&0u32.to_le_bytes()).map_err(ioerr)?;
    let mut whole = Sha256::new();
    let mut total_bytes = 0u64;
    let mut buf = vec![0; block as usize];
    let mut eof = false;
    loop {
        let mut got = 0;
        let mut symbol_counts = [0u32; 256];
        let mut buffered_since: Option<std::time::Instant> = None;
        while got < buf.len() {
            let timeout = match (flush_interval, buffered_since) {
                (Some(interval), Some(since)) => {
                    let elapsed = since.elapsed();
                    if elapsed >= interval {
                        break;
                    }
                    Some(interval - elapsed)
                }
                _ => None,
            };
            let n = match read_poll(&mut src, &mut buf[got..], input_fd, timeout)? {
                Some(n) => n,
                None => continue,
            };
            if n == 0 {
                eof = true;
                break;
            }
            for &byte in &buf[got..got + n] {
                symbol_counts[byte as usize] += 1;
            }
            got += n;
            if buffered_since.is_none() {
                buffered_since = Some(std::time::Instant::now());
            }
        }
        if got == 0 {
            if eof {
                break;
            }
            continue;
        }
        if symbol_counts.iter().sum::<u32>() != got as u32 {
            return Err("internal block symbol count mismatch".into());
        }
        total_bytes = total_bytes
            .checked_add(got as u64)
            .ok_or("input length overflow")?;
        let data = &buf[..got];
        let rh: [u8; 32] = Sha256::digest(data).into();
        whole.update(data);
        let mut candidates = vec![(0u8, data.to_vec()), (1, rle(data))];
        candidates.push((2, stream_encode(data, level, "cix")?));
        candidates.push((10, stream_encode(data, level, "deflate")?));
        let (route, payload) = if let Some(f) = forced {
            let id = match f {
                "raw" => 0,
                "runs" => 1,
                "deflate" => 10,
                "composition" => 2,
                _ => return Err(format!("unsupported route: {f}")),
            };
            candidates.into_iter().find(|x| x.0 == id).unwrap()
        } else {
            candidates.sort_by_key(|x| x.1.len());
            candidates.remove(0)
        };
        put_frame(&mut dst, route, got as u32, payload.len() as u32, &rh).map_err(ioerr)?;
        dst.write_all(&payload).map_err(ioerr)?;
        dst.flush().map_err(ioerr)?;
        if eof {
            break;
        }
    }
    let h: [u8; 32] = whole.finalize().into();
    put_frame(&mut dst, END, 0, 0, &h).map_err(ioerr)?;
    dst.flush().map_err(ioerr)?;
    Ok(())
}
fn decode<R: Read, W: Write>(
    mut src: R,
    mut dst: W,
    verify_only: bool,
    list: bool,
    input_fd: i32,
) -> Result<(), String> {
    let mut h = [0; HEADER];
    read_exact_poll(&mut src, &mut h, input_fd)?;
    if &h[..5] != MAGIC {
        return Err("unsupported archive (expected CIXG1)".into());
    }
    let block = u32::from_le_bytes(h[5..9].try_into().unwrap());
    let hist = u32::from_le_bytes(h[9..13].try_into().unwrap());
    if block == 0 || block > MAX_BLOCK || hist != 0 && hist != 65536 {
        return Err("invalid CIXG1 header".into());
    }
    let mut whole = Sha256::new();
    let mut total_bytes = 0u64;
    loop {
        let mut r = [0; 1];
        read_exact_poll(&mut src, &mut r, input_fd)?;
        let n = read_u32(&mut src, input_fd)?;
        let s = read_u32(&mut src, input_fd)?;
        let mut sum = [0; 32];
        read_exact_poll(&mut src, &mut sum, input_fd)?;
        if r[0] == END {
            if n != 0 || s != 0 || sum != <[u8; 32]>::from(whole.clone().finalize()) {
                return Err("archive checksum/terminator mismatch".into());
            }
            let mut x = [0];
            loop {
                match read_poll(&mut src, &mut x, input_fd, None)? {
                    Some(0) => break,
                    Some(_) => return Err("trailing archive bytes".into()),
                    None => continue,
                }
            }
            if !verify_only {
                dst.flush().map_err(ioerr)?;
            }
            if list {
                eprintln!("CIXG1 stream: {} decoded bytes", total_bytes);
            }
            return Ok(());
        }
        if n == 0 || n > block || s as u64 > 8 * n as u64 + 4096 {
            return Err("invalid block descriptor".into());
        }
        let mut b = vec![0; s as usize];
        read_exact_poll(&mut src, &mut b, input_fd)?;
        let data = match r[0] {
            0 => {
                if b.len() != n as usize {
                    return Err("raw size mismatch".into());
                }
                b
            }
            1 => unrle(&b, n as usize)?,
            2 => stream_decode(&b, n as usize)?,
            10 => stream_decode(&b, n as usize)?,
            _ => return Err(format!("unsupported CIXG1 route ID {}", r[0])),
        };
        if <[u8; 32]>::from(Sha256::digest(&data)) != sum {
            return Err("block checksum mismatch".into());
        }
        whole.update(&data);
        total_bytes = total_bytes
            .checked_add(data.len() as u64)
            .ok_or("decoded length overflow")?;
        if list {
            eprintln!(
                "CIXG1 block: route={}, source={} bytes, payload={} bytes",
                r[0], n, s
            )
        }
        if !verify_only {
            dst.write_all(&data).map_err(ioerr)?;
            dst.flush().map_err(ioerr)?;
        }
    }
}
fn ioerr(e: io::Error) -> String {
    e.to_string()
}
fn default_output(input: &str, dec: bool) -> String {
    if input == "-" {
        return "-".into();
    }
    let p = Path::new(input);
    if dec {
        if p.extension().map(|x| x == "cix").unwrap_or(false) {
            let mut q = p.to_path_buf();
            q.set_extension("");
            q.to_string_lossy().into_owned()
        } else {
            format!("{input}.out")
        }
    } else {
        format!("{input}.cix")
    }
}
fn atomic_file(
    path: &str,
    force: bool,
    run: impl FnOnce(&mut File) -> Result<(), String>,
) -> Result<(), String> {
    let p = Path::new(path);
    if fs::symlink_metadata(p).is_ok() && !force {
        return Err(format!("refusing to overwrite {path} (use -f)"));
    }
    let parent = p.parent().unwrap_or(Path::new("."));
    let name = p.file_name().unwrap_or_default().to_string_lossy();
    let stamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    let tmp = parent.join(format!(".{name}.cix-tmp-{}-{stamp}", process::id()));
    let mut f = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&tmp)
        .map_err(ioerr)?;
    let result = run(&mut f);
    if result.is_ok() {
        if let Err(e) = f.sync_all() {
            drop(f);
            let _ = fs::remove_file(&tmp);
            return Err(ioerr(e));
        }
    }
    drop(f);
    if let Err(e) = result {
        let _ = fs::remove_file(&tmp);
        return Err(e);
    }
    if force {
        fs::rename(&tmp, p).map_err(|e| {
            let _ = fs::remove_file(&tmp);
            ioerr(e)
        })?;
    } else {
        fs::hard_link(&tmp, p).map_err(|e| {
            let _ = fs::remove_file(&tmp);
            if e.kind() == io::ErrorKind::AlreadyExists {
                format!("refusing to overwrite {path} (use -f)")
            } else {
                ioerr(e)
            }
        })?;
        fs::remove_file(&tmp).map_err(ioerr)?;
    }
    if let Some(dir) = p.parent() {
        if let Ok(d) = File::open(dir) {
            let _ = d.sync_all();
        }
    }
    Ok(())
}
fn run() -> Result<(), String> {
    let o = parse()?;
    if o.threads != 1 {
        return Err(
            "this portable build supports --threads 1; parallel coding is not implemented".into(),
        );
    }
    if o.memory < 128 * 1024 {
        return Err("--memory must be at least 128 KiB for a CIXG1 frame".into());
    }
    if o.history != 0 {
        if o.independent_blocks {
            return Err("--history conflicts with --independent-blocks".into());
        }
        return Err("persistent history is not supported by the current native routes".into());
    }
    if o.decode && o.flush_interval.is_some() {
        return Err("--flush-interval applies to encoding only".into());
    }
    if o.flush_interval.is_some() && !cfg!(unix) {
        return Err("--flush-interval on non-seekable input requires Unix poll support".into());
    }
    if let Some(r) = &o.route {
        if !["auto", "raw", "runs", "composition", "deflate"].contains(&r.as_str()) {
            return Err(format!("unsupported native route: {r}"));
        }
    }
    let requested_block = o
        .block
        .unwrap_or(if o.level == 9 { MAX_BLOCK } else { 32768 });
    if requested_block == 0 {
        return Err("--block-size must be positive".into());
    }
    let block = requested_block.min(MAX_BLOCK);
    if requested_block > MAX_BLOCK {
        eprintln!("cix: CIXG1 limits frames to 65536 bytes; effective block size is 65536 bytes");
    }
    let estimated_working = block as usize * 8 + 65536;
    if estimated_working > o.memory {
        return Err(format!("block needs about {estimated_working} bytes working memory; reduce --block-size or raise --memory"));
    }
    let forced = o.route.as_deref().filter(|r| *r != "auto");
    let out = o
        .output
        .clone()
        .unwrap_or_else(|| default_output(&o.input, o.decode));
    if o.test || o.list {
        let f = open_input(&o.input)?;
        let fd = input_fd(&f);
        decode(f, io::sink(), true, o.list, fd)?;
        eprintln!("archive OK");
        return Ok(());
    }
    if o.stdout || out == "-" {
        let src = open_input(&o.input)?;
        let fd = input_fd(&src);
        let dst = io::stdout();
        let mut lock = dst.lock();
        if o.decode {
            decode(src, &mut lock, false, false, fd)
        } else {
            encode(src, &mut lock, block, o.level, forced, fd, o.flush_interval)
        }?
    } else {
        if o.input == out {
            return Err("input and output paths must differ".into());
        }
        atomic_file(&out, o.force, |dst| {
            let src = open_input(&o.input)?;
            let fd = input_fd(&src);
            if o.decode {
                decode(src, dst, false, false, fd)
            } else {
                encode(src, dst, block, o.level, forced, fd, o.flush_interval)
            }
        })?;
        eprintln!("{}", out)
    }
    let _ = (o.keep, o.stream);
    Ok(())
}
fn main() {
    if let Err(e) = ctrlc::set_handler(|| INTERRUPTED.store(true, Ordering::Relaxed)) {
        eprintln!("cix: could not install interrupt handler: {e}");
        process::exit(2);
    }
    if let Err(e) = run() {
        eprintln!("cix: {e}");
        process::exit(2)
    }
}
