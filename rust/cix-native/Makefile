PREFIX ?= /usr/local
DESTDIR ?=
PROFILE ?= release
CARGO ?= cargo
CARGO_TARGET_DIR ?= target
INSTALL ?= install
LN_S ?= ln -sfn
RM ?= rm -f

BINDIR := $(DESTDIR)$(PREFIX)/bin
MANDIR := $(DESTDIR)$(PREFIX)/share/man/man1
DOCDIR := $(DESTDIR)$(PREFIX)/share/doc/cix
TARGETDIR := $(CARGO_TARGET_DIR)/$(PROFILE)
RUNTIME_BINARY := $(TARGETDIR)/cix
ALIASES := uncix cixcat

.PHONY: all build check test install install-only uninstall clean

all: build

build:
	CARGO_TARGET_DIR=$(CARGO_TARGET_DIR) $(CARGO) build --locked --profile $(PROFILE) --bin cix

check:
	CARGO_TARGET_DIR=$(CARGO_TARGET_DIR) $(CARGO) check --locked --bins --lib

test:
	CARGO_TARGET_DIR=$(CARGO_TARGET_DIR) $(CARGO) test --locked

install: build install-only

# Install one physical executable.  uncix and cixcat are argv[0]-selected
# Unix symlinks to it; the CLI owns their distinct modes.
install-only:
	$(INSTALL) -d $(BINDIR) $(MANDIR) $(DOCDIR)
	$(INSTALL) -m 0755 $(RUNTIME_BINARY) $(BINDIR)/cix
	for alias in $(ALIASES); do $(LN_S) cix $(BINDIR)/$$alias; done
	$(INSTALL) -m 0644 man/cix.1 man/uncix.1 man/cixcat.1 $(MANDIR)
	$(INSTALL) -m 0644 README.md LICENSE THIRD_PARTY_NOTICES.txt THIRD_PARTY_NOTICES_RUST.md $(DOCDIR)

uninstall:
	$(RM) $(BINDIR)/cix
	for alias in $(ALIASES); do $(RM) $(BINDIR)/$$alias; done
	$(RM) $(MANDIR)/cix.1 $(MANDIR)/uncix.1 $(MANDIR)/cixcat.1
	$(RM) $(DOCDIR)/README.md $(DOCDIR)/LICENSE $(DOCDIR)/THIRD_PARTY_NOTICES.txt $(DOCDIR)/THIRD_PARTY_NOTICES_RUST.md

clean:
	CARGO_TARGET_DIR=$(CARGO_TARGET_DIR) $(CARGO) clean
