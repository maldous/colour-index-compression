cd /tmp/cix-sonar-final/rust/cix-native
export CARGO_TARGET_DIR=/tmp/cix-sonar-final-target
export CARGO_BUILD_JOBS=2
exec /home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo clippy --locked --all-targets --all-features --message-format=json
