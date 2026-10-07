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
