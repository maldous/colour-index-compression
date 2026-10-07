use std::{env, path::Path};
fn main() {
    let args: Vec<String> = env::args().collect();
    let result = if args.len() == 6 {
        cix_native::physical::execute(&args[1], &args[2], Path::new(&args[3]), Path::new(&args[4]), Path::new(&args[5]))
    } else { Err("operation backend input output work".into()) };
    if let Err(error) = result {
        eprintln!("CIX_PHYSICAL_ERROR: {error}");
        std::process::exit(2);
    }
}
