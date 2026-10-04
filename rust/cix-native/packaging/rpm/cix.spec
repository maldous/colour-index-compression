Name:           cix
Version:        0.1.0
Release:        1%{?dist}
Summary:        Lossless command-line compressor
License:        MIT AND Apache-2.0
Source0:        %{name}-%{version}.tar.gz
BuildRequires:  cargo
BuildRequires:  rust
BuildRequires:  gcc-c++
BuildRequires:  zlib-devel
BuildRequires:  bzip2-devel
BuildRequires:  xz-devel
BuildRequires:  libzstd-devel
BuildRequires:  brotli-devel

%description
CIX creates and restores lossless, self-describing CIX archives.

%prep
%autosetup -n cix-%{version}

%build
cargo build --release --locked --bins

%install
install -Dpm 0755 target/release/cix %{buildroot}%{_bindir}/cix
install -Dpm 0755 target/release/uncix %{buildroot}%{_bindir}/uncix
install -Dpm 0755 target/release/cixcat %{buildroot}%{_bindir}/cixcat
install -Dpm 0644 man/cix.1 %{buildroot}%{_mandir}/man1/cix.1
install -Dpm 0644 man/uncix.1 %{buildroot}%{_mandir}/man1/uncix.1
install -Dpm 0644 man/cixcat.1 %{buildroot}%{_mandir}/man1/cixcat.1

%files
%license LICENSE THIRD_PARTY_NOTICES.txt THIRD_PARTY_NOTICES_RUST.md
%doc README.md
%{_bindir}/cix
%{_bindir}/uncix
%{_bindir}/cixcat
%{_mandir}/man1/cix.1*
%{_mandir}/man1/uncix.1*
%{_mandir}/man1/cixcat.1*

%changelog
* Sun Oct 04 2026 maldous <matthew.aldous@gmail.com> - 0.1.0-1
- Initial package.
