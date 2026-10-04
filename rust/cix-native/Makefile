PREFIX ?= /usr/local
DESTDIR ?=
PROFILE ?= release
CARGO ?= cargo
CARGO_TARGET_DIR ?= target
INSTALL ?= install
RM ?= rm -f

BINDIR := $(DESTDIR)$(PREFIX)/bin
MANDIR := $(DESTDIR)$(PREFIX)/share/man/man1
DOCDIR := $(DESTDIR)$(PREFIX)/share/doc/cix
TARGETDIR := $(CARGO_TARGET_DIR)/$(PROFILE)
BINS := cix uncix cixcat

.PHONY: all build check test install install-only uninstall clean

all: build

build:
	CARGO_TARGET_DIR=$(CARGO_TARGET_DIR) $(CARGO) build --locked --profile $(PROFILE) --bins

check:
	CARGO_TARGET_DIR=$(CARGO_TARGET_DIR) $(CARGO) check --locked --bins --lib

test:
	CARGO_TARGET_DIR=$(CARGO_TARGET_DIR) $(CARGO) test --locked

install: build install-only

install-only:
	$(INSTALL) -d $(BINDIR) $(MANDIR) $(DOCDIR)
	for bin in $(BINS); do $(INSTALL) -m 0755 $(TARGETDIR)/$$bin $(BINDIR)/$$bin; done
	$(INSTALL) -m 0644 man/cix.1 man/uncix.1 man/cixcat.1 $(MANDIR)
	$(INSTALL) -m 0644 README.md LICENSE THIRD_PARTY_NOTICES.txt THIRD_PARTY_NOTICES_RUST.md $(DOCDIR)

uninstall:
	for bin in $(BINS); do $(RM) $(BINDIR)/$$bin; done
	$(RM) $(MANDIR)/cix.1 $(MANDIR)/uncix.1 $(MANDIR)/cixcat.1
	$(RM) $(DOCDIR)/README.md $(DOCDIR)/LICENSE $(DOCDIR)/THIRD_PARTY_NOTICES.txt $(DOCDIR)/THIRD_PARTY_NOTICES_RUST.md

clean:
	CARGO_TARGET_DIR=$(CARGO_TARGET_DIR) $(CARGO) clean
