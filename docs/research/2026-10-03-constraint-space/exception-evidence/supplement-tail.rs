// Append this tail verbatim to executed-record_exceptions.rs before `rustc --test`.
// It is a forced-model mechanical-accounting supplement, not discovery evidence.

#[test]
fn supplement_forced_exception_accounting() -> Result<(), String> {
    use std::path::Path;

    const ROOT: &str = "benchmark-work/record-exceptions/supplement";
    let root = Path::new(ROOT);
    fs::create_dir_all(root).map_err(|error| error.to_string())?;
    let model = Model {
        b: 6,
        mask: 1,
        count: Count::Exact,
        param: 3,
    };
    let symbols = [0u8, 1u8];
    let valid = table(model);
    if valid.len() != 8 {
        return Err(fail("supplement expected eight valid words"));
    }

    let write_case = |name: &str,
                      input: Vec<u8>,
                      archive: Vec<u8>,
                      expected_e: usize,
                      expected_len: Option<usize>|
     -> Result<(), String> {
        if decode(&archive)? != input {
            return Err(fail("supplement decode"));
        }
        let observed_e = if archive[5] == Kind::Exceptions as u8 {
            u32::from_le_bytes(archive[17..21].try_into().unwrap()) as usize
        } else {
            0
        };
        if observed_e != expected_e || expected_len.is_some_and(|length| archive.len() != length) {
            return Err(fail("supplement accounting"));
        }
        fs::write(root.join(format!("{name}.input")), &input).map_err(|error| error.to_string())?;
        fs::write(root.join(format!("{name}.rex")), &archive).map_err(|error| error.to_string())?;
        println!(
            "supplement case={name} bytes={} e={observed_e}",
            archive.len()
        );
        Ok(())
    };
    let words_to_bytes = |words: &[u16]| -> Vec<u8> {
        words
            .iter()
            .flat_map(|&word| (0..6).map(move |bit| symbols[((word >> (5 - bit)) & 1) as usize]))
            .collect()
    };
    let cyclic = |records: usize| -> Vec<u16> {
        (0..records)
            .map(|index| valid[index % valid.len()])
            .collect()
    };
    let invalid = |word: u16| -> u16 { word ^ (1 << 5) };

    let empty = Vec::new();
    write_case("empty-raw", empty.clone(), raw(&empty), 0, None)?;

    let e0_words = cyclic(16);
    let e0_input = words_to_bytes(&e0_words);
    write_case(
        "e0",
        e0_input.clone(),
        build(&e0_input, symbols, model)?,
        0,
        None,
    )?;

    let all_words: Vec<u16> = cyclic(16).into_iter().map(invalid).collect();
    let all_input = words_to_bytes(&all_words);
    write_case(
        "e-all",
        all_input.clone(),
        build(&all_input, symbols, model)?,
        16,
        None,
    )?;

    let mut first_words = cyclic(16);
    first_words[0] = invalid(first_words[0]);
    let first_input = words_to_bytes(&first_words);
    write_case(
        "e-first",
        first_input.clone(),
        build(&first_input, symbols, model)?,
        1,
        None,
    )?;

    let mut last_words = cyclic(16);
    let last = last_words.len() - 1;
    last_words[last] = invalid(last_words[last]);
    let last_input = words_to_bytes(&last_words);
    write_case(
        "e-last",
        last_input.clone(),
        build(&last_input, symbols, model)?,
        1,
        None,
    )?;

    for (name, exceptions, expected_len) in [
        ("weak-r2048-e269", 269usize, 1048usize),
        ("weak-r2048-e270", 270usize, 1049usize),
    ] {
        let mut words = cyclic(2048);
        for word in words.iter_mut().take(exceptions) {
            *word = invalid(*word);
        }
        let input = words_to_bytes(&words);
        write_case(
            name,
            input.clone(),
            build(&input, symbols, model)?,
            exceptions,
            Some(expected_len),
        )?;
    }
    Ok(())
}
