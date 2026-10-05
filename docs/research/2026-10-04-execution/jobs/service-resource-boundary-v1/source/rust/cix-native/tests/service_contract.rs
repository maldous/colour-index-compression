#![cfg(feature = "server")]
use cix_native::service::{auth::Principal,contracts::*,repository::Repository};
use serde_json::json;

fn principal(tenant:&str,subject:&str)->Principal {
    Principal {tenant:tenant.into(),subject:subject.into(),scopes:vec!["jobs:*".into()],collections:vec![]}
}
fn request(key:&str)->TransformRequest {
    TransformRequest {operation:Operation::Compress,source:InputRef::Artifact{id:new_id()},options:CompressionOptions::default(),limits:ResourceLimits::default(),idempotency_key:key.into()}
}
async fn repository()->Repository {
    let r=Repository::connect("sqlite::memory:").await.unwrap(); r.migrate().await.unwrap();r
}

#[test]
fn counters_are_exact_and_paths_are_confined() {
    assert_eq!(serde_json::to_value(Count(u64::MAX)).unwrap(),json!("18446744073709551615"));
    assert_eq!(serde_json::from_value::<Count>(json!("18446744073709551615")).unwrap().0,u64::MAX);
    for bad in [json!(1),json!("01"),json!("-1"),json!("18446744073709551616")] {assert!(serde_json::from_value::<Count>(bad).is_err());}
    for bad in ["/etc/passwd","../secret","a/../secret","a//b","a\\b",""] {assert!(check_path(bad).is_err());}
    assert!(check_path("日本語/é.txt").is_ok());
    assert_eq!(Profile::default(),Profile::Fast);
}

#[tokio::test]
async fn submission_is_idempotent_and_scoped() {
    let r=repository().await;let alice=principal("team","alice");let bob=principal("team","bob");let other=principal("other","alice");
    let request=request("stable");let j=r.submit(&alice,request.clone(),4).await.unwrap();
    assert_eq!(r.submit(&alice,request.clone(),4).await.unwrap().id,j.id);
    let mut different=request.clone(); different.options.profile=Profile::Best;
    assert_eq!(r.submit(&alice,different,4).await.unwrap_err().code,"idempotency_conflict");
    assert!(r.job(&bob,&j.id).await.is_err());assert!(r.job(&other,&j.id).await.is_err());
    assert_ne!(r.submit(&bob,request,4).await.unwrap().id,j.id);
}

#[tokio::test]
async fn queued_cancel_releases_admission_and_stale_worker_cannot_publish() {
    let r=repository().await;let p=principal("team","alice");
    let j=r.submit(&p,request("one"),1).await.unwrap();
    assert_eq!(r.submit(&p,request("two"),1).await.unwrap_err().code,"queue_full");
    assert_eq!(r.cancel(&p,&j.id).await.unwrap().state,JobState::Cancelled);
    let next=r.submit(&p,request("two"),1).await.unwrap();
    let mut claimed=r.claim("worker-a",30_000).await.unwrap().unwrap();assert_eq!(claimed.id,next.id);
    let before=claimed.revision.0;claimed.revision.0+=1;claimed.state=JobState::Succeeded;
    r.cancel(&p,&next.id).await.unwrap();
    assert!(!r.update_job(&claimed,before,Some("worker-a")).await.unwrap());
    assert_eq!(r.job(&p,&next.id).await.unwrap().state,JobState::Cancelling);
}

#[tokio::test]
async fn only_one_worker_claims_a_revision() {
    let r=repository().await;let p=principal("team","alice");
    r.submit(&p,request("one"),2).await.unwrap();
    let (a,b)=tokio::join!(r.claim("a",30_000),r.claim("b",30_000));
    assert_eq!(usize::from(a.unwrap().is_some())+usize::from(b.unwrap().is_some()),1);
}

fn assert_resource_limit(problem: cix_native::service::error::Problem, resource: &str) {
    assert_eq!(problem.code, "resource_limit");
    assert_eq!(problem.arguments["resource"], json!(resource));
}

#[test]
fn temporary_storage_budget_preserves_zero_as_a_prohibition() {
    let mut requested = ResourceLimits::default();
    requested.temporary_bytes = Count(0);
    requested.within(&ResourceLimits::default()).unwrap();

    let cap = requested.clone();
    requested.within(&cap).unwrap();
    requested.temporary_bytes = Count(1);
    assert_resource_limit(requested.within(&cap).unwrap_err(), "temporary_bytes");

    let mut positive_cap = cap.clone();
    positive_cap.temporary_bytes = Count(1);
    requested.within(&positive_cap).unwrap();
    requested.temporary_bytes = Count(2);
    assert_resource_limit(requested.within(&positive_cap).unwrap_err(), "temporary_bytes");

    // Configuration loading must retain this prohibition instead of widening it.
    let mut config = cix_native::service::config::Config::default();
    config.state_directory = std::env::temp_dir().join("cix-resource-validation-only");
    config.limits = cap;
    config.validate().unwrap();
    assert_eq!(config.effective_policy().unwrap().limits.temporary_bytes, 0);
}

#[test]
fn required_positive_resources_and_upper_caps_remain_enforced() {
    let fields: [(&str, fn(&mut ResourceLimits) -> &mut Count); 4] = [
        ("input_bytes", |limits| &mut limits.input_bytes),
        ("output_bytes", |limits| &mut limits.output_bytes),
        ("memory_bytes", |limits| &mut limits.memory_bytes),
        ("deadline_ms", |limits| &mut limits.deadline_ms),
    ];
    for (name, field) in fields {
        let mut cap = ResourceLimits::default();
        let mut requested = cap.clone();
        *field(&mut requested) = Count(0);
        assert_resource_limit(requested.within(&cap).unwrap_err(), name);
        *field(&mut cap) = Count(1);
        *field(&mut requested) = Count(2);
        assert_resource_limit(requested.within(&cap).unwrap_err(), name);
    }
    let cap = ResourceLimits::default();
    for workers in [0, cap.workers + 1] {
        let mut requested = cap.clone();
        requested.workers = workers;
        assert_resource_limit(requested.within(&cap).unwrap_err(), "workers");
    }
}

struct ServiceTestDirectory(std::path::PathBuf);

impl ServiceTestDirectory {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!("cix-service-resource-{}", new_id()));
        let mut builder = std::fs::DirBuilder::new();
        #[cfg(unix)]
        {
            use std::os::unix::fs::DirBuilderExt;
            builder.mode(0o700);
        }
        builder.create(&path).unwrap();
        Self(path)
    }
}

impl Drop for ServiceTestDirectory {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

#[tokio::test]
async fn zero_temp_worker_rejects_before_admission_or_storage_effects() {
    use cix_native::service::{config::Config, engine::Engine, jobs::Jobs, objects::Objects};
    use std::sync::Arc;

    let directory = ServiceTestDirectory::new();
    let mut config = Config::default();
    config.state_directory = directory.0.clone();
    config.limits.temporary_bytes = Count(0);
    config.validate().unwrap();
    // No provider directory or input artifact exists. A late check would return
    // providers_not_configured or not_found instead of the required budget error.
    let repository = repository().await;
    let objects = Objects::open(&config, repository.clone()).await.unwrap();
    let config = Arc::new(config);
    let engine = Engine::new(config.clone(), objects).unwrap();
    let jobs = Jobs::new(repository.clone(), engine.clone(), config);
    let mut actor = principal("team", "alice");
    actor.scopes.push("codec:encode".into());
    let mut zero_temp = request("no-temporary-storage");
    zero_temp.limits.temporary_bytes = Count(0);

    assert!(repository.jobs(&actor, None).await.unwrap().items.is_empty());
    assert_resource_limit(engine.validate(&zero_temp).unwrap_err(), "temporary_bytes");
    assert_resource_limit(
        jobs.submit(&actor, zero_temp.clone()).await.unwrap_err(),
        "temporary_bytes",
    );
    assert!(repository.jobs(&actor, None).await.unwrap().items.is_empty());

    // Direct execution must recheck the same prohibition before reading the
    // nonexistent input or creating the worker's temporary directory.
    let job = Job {
        id: new_id(),
        tenant: actor.tenant.clone(),
        subject: actor.subject.clone(),
        state: JobState::Running,
        revision: Count(1),
        attempt: 1,
        created_ms: Count(now_ms()),
        updated_ms: Count(now_ms()),
        request: zero_temp,
        result: None,
        error: None,
    };
    let (_cancel, receiver) = tokio::sync::watch::channel(false);
    assert_resource_limit(
        engine.execute(&actor, &job, receiver).await.unwrap_err(),
        "temporary_bytes",
    );
    assert!(!directory.0.join("workers").exists());
    assert_eq!(std::fs::read_dir(directory.0.join("objects")).unwrap().count(), 0);
}
