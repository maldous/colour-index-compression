//! Audit-only comparison of legacy preallocation and bounded source reading.
#[path = "../bounded_reader.rs"]
mod bounded_reader;

use std::io::{Cursor, Read};

#[global_allocator]
static ALLOC: dhat::Alloc = dhat::Alloc;

const MAX: usize = 128 * 1024 * 1024;

fn input(size: usize) -> Vec<u8> {
    (0..size).map(|i| (i as u8).wrapping_mul(37).wrapping_add(11)).collect()
}

fn old(data: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(MAX);
    Cursor::new(data).take((MAX + 1) as u64).read_to_end(&mut out).unwrap();
    out
}

fn main() {
    let mode = std::env::args().nth(1).expect("mode old|new");
    let size: usize = std::env::args().nth(2).expect("size").parse().expect("numeric size");
    let cgroup = std::fs::read_to_string("/proc/self/cgroup").expect("cgroup");
    let path = cgroup.lines().find_map(|line| line.strip_prefix("0::")).expect("unified cgroup");
    let root = format!("/sys/fs/cgroup{path}");
    let read = |name: &str| std::fs::read_to_string(format!("{root}/{name}")).expect("cgroup property").trim().to_owned();
    let affinity = std::fs::read_to_string("/proc/self/status").expect("status").lines().find(|line| line.starts_with("Cpus_allowed_list:")).expect("affinity").to_owned();
    println!("child cgroup={path} memory.max={} memory.swap.max={} cpuset={} {affinity}", read("memory.max"), read("memory.swap.max"), read("cpuset.cpus.effective"));
    {
        let source = input(size); // deliberately outside the profiled interval
        let profiler = dhat::Profiler::new_heap();
        let output = match mode.as_str() {
            "old" => old(&source),
            "new" => bounded_reader::read_bounded(Cursor::new(&source), MAX, bounded_reader::conservative_allowance(MAX)).unwrap(),
            _ => panic!("mode old|new"),
        };
        println!("{{\"mode\":\"{mode}\",\"size\":{size},\"returned_capacity\":{},\"equal\":{}}}", output.capacity(), output == source);
        drop(output);
        drop(profiler);
    }
}
