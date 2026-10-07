use cix_native::full_engine::address_relations::{relocated_pointer_inverse, relocated_pointer_transform};
use std::{env, fs};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    let result = match args.get(1).map(String::as_str) {
        Some("encode") if args.len() == 6 => relocated_pointer_transform(
            &fs::read(&args[2])?, args[4].parse()?, args[5].parse::<u8>()? != 0,
        ),
        Some("decode") if args.len() == 4 => relocated_pointer_inverse(&fs::read(&args[2])?),
        _ => return Err("encode INPUT OUTPUT MODE SHARED or decode INPUT OUTPUT".into()),
    }.map_err(|e| format!("native transform error: {e:?}"))?;
    fs::write(&args[3], result)?;
    Ok(())
}
