//! Also runnable in isolation with `rustc --test --edition=2021` so catalog
//! contract checks do not need to rebuild/link the compression providers.
#[path = "../src/i18n.rs"]
#[allow(dead_code)]
mod i18n;

use i18n::{Catalog, Direction, Localizer, Message, Number, PluralCategory, RenderError, Value};
use std::collections::BTreeMap;

struct FixtureCatalog {
    rtl: bool,
    patterns: BTreeMap<(String, u8), String>,
}
fn category(category: PluralCategory) -> u8 {
    match category {
        PluralCategory::Zero => 0, PluralCategory::One => 1, PluralCategory::Two => 2,
        PluralCategory::Few => 3, PluralCategory::Many => 4, PluralCategory::Other => 5,
    }
}
impl FixtureCatalog {
    fn new() -> Self { Self { rtl: false, patterns: BTreeMap::new() } }
    fn insert(&mut self, id: &str, form: PluralCategory, pattern: &str) {
        self.patterns.insert((id.into(), category(form)), pattern.into());
    }
}
impl Catalog for FixtureCatalog {
    fn locale(&self) -> &str { "qps-test" }
    fn direction(&self) -> Direction { if self.rtl { Direction::Rtl } else { Direction::Ltr } }
    fn pattern(&self, id: &str, form: PluralCategory) -> Option<&str> {
        self.patterns.get(&(id.into(), category(form))).map(String::as_str)
    }
    fn plural_category(&self, count: &Number) -> PluralCategory {
        match count {
            Number::Unsigned(0) => PluralCategory::Zero,
            Number::Unsigned(1) => PluralCategory::One,
            Number::Unsigned(2) => PluralCategory::Two,
            Number::Unsigned(3..=10) => PluralCategory::Few,
            Number::Unsigned(11..=99) => PluralCategory::Many,
            _ => PluralCategory::Other,
        }
    }
    fn format_number(&self, count: &Number) -> String { format!("⟦{count}⟧") }
}
fn summary(total: u64) -> Message {
    Message::new("cli.files.failed")
        .arg("failures", Value::Number(Number::Unsigned(1)))
        .arg("total", Value::Number(Number::Unsigned(total)))
}

#[test]
fn english_catalog_renders_every_entry_with_declared_argument_types() {
    for entry in i18n::definitions() {
        assert!(!entry.context.trim().is_empty());
        let mut message = Message::new(entry.id);
        for parameter in entry.parameters {
            let value = match parameter.kind {
                i18n::ParameterKind::Text => Value::Text("東京 e\u{301} العربية {literal}".into()),
                i18n::ParameterKind::Code => Value::Code("--help".into()),
                i18n::ParameterKind::Path => Value::Path("目录/اسم/é.cix".into()),
                i18n::ParameterKind::Number => Value::Number(Number::Unsigned(2)),
                i18n::ParameterKind::Message => Value::Message(Box::new(Message::new("cli.archive.ok"))),
            };
            message = message.arg(parameter.name, value);
        }
        assert!(Localizer::english().render(&message).is_ok(), "{}", entry.id);
        if let Some(name) = entry.plural {
            assert!(Localizer::english().render(&message.arg(name, Value::Number(Number::Unsigned(1)))).is_ok());
        }
    }
}

#[test]
fn english_plural_agrees_with_total_files() {
    assert_eq!(Localizer::english().render(&summary(1)).unwrap(), "1 of 1 input file failed");
    assert_eq!(Localizer::english().render(&summary(2)).unwrap(), "1 of 2 input files failed");
    assert_eq!(Localizer::english().render(&summary(u64::MAX)).unwrap(),
        "1 of 18446744073709551615 input files failed");
}

#[test]
fn all_six_plural_categories_and_reordered_parameters_are_available() {
    let mut catalog = FixtureCatalog::new();
    for (n, form) in [(0, PluralCategory::Zero), (1, PluralCategory::One),
        (2, PluralCategory::Two), (3, PluralCategory::Few),
        (11, PluralCategory::Many), (100, PluralCategory::Other)] {
        catalog.insert("cli.files.failed", form, &format!("form={n}: {{total}} / {{failures}}"));
    }
    for n in [0, 1, 2, 3, 11, 100] {
        assert_eq!(Localizer::new(&catalog).render(&summary(n)).unwrap(),
            format!("form={n}: ⟦{n}⟧ / ⟦1⟧"));
    }
}

#[test]
fn missing_or_invalid_translation_falls_back_as_a_whole_message() {
    let mut catalog = FixtureCatalog::new();
    for pattern in ["missing {total}", "extra {total} {failures} {unknown}", "{total} {failures", "}"] {
        catalog.insert("cli.files.failed", PluralCategory::Two, pattern);
        assert_eq!(Localizer::new(&catalog).render(&summary(2)).unwrap(), "1 of 2 input files failed");
    }
    catalog.insert("cli.files.failed", PluralCategory::Other, "{total} / {failures}");
    assert_eq!(Localizer::new(&catalog).render(&summary(1)).unwrap(), "1 of 1 input file failed");
}

#[test]
fn arbitrary_unicode_and_braces_are_inserted_once_and_never_normalized() {
    let value = "目录/e\u{301}/العربية/{detail}/🙂";
    let message = Message::new("cli.output.path").arg("path", Value::Path(value.into()));
    assert_eq!(Localizer::english().render(&message).unwrap(), value);
    assert_eq!(message.args["path"], Value::Path(value.into()));
}

#[test]
fn rtl_display_isolates_values_without_mutating_data() {
    let mut catalog = FixtureCatalog::new();
    catalog.rtl = true;
    catalog.insert("cli.output.path", PluralCategory::Other, "⟦{path}⟧");
    let message = Message::new("cli.output.path").arg("path", Value::Path("目录/a.cix".into()));
    let before = message.clone();
    let localizer = Localizer::new(&catalog);
    assert_eq!(localizer.locale(), "qps-test");
    assert_eq!(localizer.direction(), Direction::Rtl);
    assert_eq!(localizer.render(&message).unwrap(), "⟦\u{2068}目录/a.cix\u{2069}⟧");
    assert_eq!(message, before);
}

#[test]
fn malformed_caller_messages_are_typed_errors() {
    assert_eq!(Localizer::english().render(&Message::new("missing.id")), Err(RenderError::UnknownMessage));
    assert_eq!(Localizer::english().render(&Message::new("cli.output.path")), Err(RenderError::InvalidArguments));
    assert_eq!(Localizer::english().render(&Message::new("cli.output.path").arg("path", Value::Text("x".into()))), Err(RenderError::InvalidArguments));
    assert_eq!(Localizer::english().render(&summary(2).arg("extra", Value::Text("x".into()))), Err(RenderError::InvalidArguments));
}

#[test]
fn locale_resolution_has_explicit_precedence_and_deterministic_fallbacks() {
    let values = BTreeMap::from([
        ("CIX_LOCALE", "zh_Hant_TW.UTF-8"), ("LANGUAGE", "ar:fr"),
        ("LC_ALL", "de_DE.UTF-8"), ("LC_MESSAGES", "it_IT"), ("LANG", "ja_JP"),
    ]);
    let lookup = |key: &str| values.get(key).map(|value| value.to_string());
    assert_eq!(i18n::locale_preferences(Some("pt-BR"), lookup), ["pt-br", "pt", "en"]);
    assert_eq!(i18n::locale_preferences(None, lookup), ["zh-hant-tw", "zh-hant", "zh", "en"]);
    assert_eq!(i18n::locale_preferences(None, |key| match key {
        "LANGUAGE" => Some("ar:fr".into()), "LC_ALL" => Some("C.UTF-8".into()), _ => None,
    }), ["en"]);
    assert_eq!(i18n::locale_preferences(Some("../../x"), |_| None), ["en"]);
    assert_eq!(i18n::locale_preferences(Some("de-DE-u-nu-latn"), |_| None),
        ["de-de-u-nu-latn", "de-de", "de", "en"]);
    assert_eq!(i18n::normalize_locale("POSIX"), Some("en".into()));
    assert_eq!(i18n::normalize_locale("en_"), None);
}

#[test]
fn localizers_are_isolated_across_concurrent_host_requests() {
    let mut first = FixtureCatalog::new();
    first.insert("cli.archive.ok", PluralCategory::Other, "first");
    let mut second = FixtureCatalog::new();
    second.insert("cli.archive.ok", PluralCategory::Other, "second");
    std::thread::scope(|scope| {
        let a = scope.spawn(|| Localizer::new(&first).render(&Message::new("cli.archive.ok")).unwrap());
        let b = scope.spawn(|| Localizer::new(&second).render(&Message::new("cli.archive.ok")).unwrap());
        assert_eq!(a.join().unwrap(), "first");
        assert_eq!(b.join().unwrap(), "second");
    });
    assert_eq!(Localizer::english().render(&Message::new("cli.archive.ok")).unwrap(), "archive OK");
}

#[test]
fn long_expanded_text_is_not_silently_truncated_to_an_english_buffer() {
    let mut catalog = FixtureCatalog::new();
    let expanded = "⟦expanded 東京 العربية⟧ ".repeat(200);
    catalog.insert("cli.archive.ok", PluralCategory::Other, &expanded);
    assert_eq!(Localizer::new(&catalog).render(&Message::new("cli.archive.ok")).unwrap(), expanded);
}
