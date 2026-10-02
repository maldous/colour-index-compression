#[path = "../src/bounded_reader.rs"]
mod bounded_reader;

use std::io::{self, Read};

struct Partial { data: Vec<u8>, at: usize, step: usize }
impl Read for Partial {
    fn read(&mut self, dst: &mut [u8]) -> io::Result<usize> {
        if self.at == self.data.len() { return Ok(0); }
        let n = (self.data.len() - self.at).min(self.step).min(dst.len());
        dst[..n].copy_from_slice(&self.data[self.at..self.at + n]);
        self.at += n; Ok(n)
    }
}

#[test]
fn preserves_irregular_partial_reads() {
    let data: Vec<u8> = (0..251).cycle().take(999).collect();
    let got = bounded_reader::read_bounded(Partial { data: data.clone(), at: 0, step: 7 }, 1_024, 1_024).unwrap();
    assert_eq!(got, data);
    assert!(got.capacity() <= 1_024);
}

#[test]
fn limit_boundary_and_stack_overflow_probe() {
    let data = vec![9; 32];
    assert_eq!(bounded_reader::read_bounded(&data[..], 32, 32).unwrap(), data);
    assert!(bounded_reader::read_bounded(&[9; 33][..], 32, 32).is_err());
}

#[test]
fn separate_admission_limit_is_enforced() {
    assert!(bounded_reader::read_bounded(&[1; 17][..], 32, 16).is_err());
    assert!(bounded_reader::read_bounded(&[][..], 16, 17).is_err());
}
