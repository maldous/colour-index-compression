# Exact docs/package integration draft

Apply this only in the planned documentation-only successor export after the
final Cargo.lock and package receipt are bound to the generated notice. The
patch assumes `THIRD_PARTY_NOTICES_RUST.md` has been generated at the export
root from the final lock. It does not change CIX source or archive behaviour.

```diff
diff --git a/Makefile b/Makefile
@@
-	$(INSTALL) -m 0644 README.md LICENSE THIRD_PARTY_NOTICES.txt $(DOCDIR)
+	$(INSTALL) -m 0644 README.md LICENSE THIRD_PARTY_NOTICES.txt THIRD_PARTY_NOTICES_RUST.md $(DOCDIR)
@@
-	$(RM) $(DOCDIR)/README.md $(DOCDIR)/LICENSE $(DOCDIR)/THIRD_PARTY_NOTICES.txt
+	$(RM) $(DOCDIR)/README.md $(DOCDIR)/LICENSE $(DOCDIR)/THIRD_PARTY_NOTICES.txt $(DOCDIR)/THIRD_PARTY_NOTICES_RUST.md

diff --git a/packaging/debian/rules b/packaging/debian/rules
@@
 	install -D -m 0644 LICENSE debian/cix/usr/share/doc/cix/copyright
 	install -D -m 0644 THIRD_PARTY_NOTICES.txt debian/cix/usr/share/doc/cix/THIRD_PARTY_NOTICES.txt
+	install -D -m 0644 THIRD_PARTY_NOTICES_RUST.md debian/cix/usr/share/doc/cix/THIRD_PARTY_NOTICES_RUST.md

diff --git a/packaging/debian/copyright b/packaging/debian/copyright
@@
 Files: vendor/libbsc/*
 Copyright: 2009-2025 Ilya Grebnov and contributors
 License: Apache-2.0
  Comment: Full text and author attribution are retained in the vendor tree and
  THIRD_PARTY_NOTICES.txt.
+
+Files: THIRD_PARTY_NOTICES_RUST.md
+Copyright: See the per-crate entries in THIRD_PARTY_NOTICES_RUST.md
+License: MIT and Apache-2.0 and Zlib
+ Comment: This generated attribution document records the exact Cargo.lock
+ crate set, Cargo-declared license expressions, retained notices, and the
+ build/runtime/target scope for this source package. It is not a grant of
+ project licensing terms.

diff --git a/packaging/rpm/cix.spec b/packaging/rpm/cix.spec
@@
 install -Dpm 0644 man/cixcat.1 %{buildroot}%{_mandir}/man1/cixcat.1
+install -Dpm 0644 THIRD_PARTY_NOTICES_RUST.md %{buildroot}%{_defaultdocdir}/%{name}/THIRD_PARTY_NOTICES_RUST.md
@@
-%license LICENSE THIRD_PARTY_NOTICES.txt
+%license LICENSE THIRD_PARTY_NOTICES.txt THIRD_PARTY_NOTICES_RUST.md
 %doc README.md
```

The binary-tar assembly and private package harness must likewise add
`THIRD_PARTY_NOTICES_RUST.md` beside `LICENSE` and
`THIRD_PARTY_NOTICES.txt`, then include the file's SHA-256 in their final
package receipt. The Debian source package naturally carries the file once it
is present in the source export.
