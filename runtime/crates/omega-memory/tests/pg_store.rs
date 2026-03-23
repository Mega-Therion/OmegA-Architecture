//! PgMemoryStore integration tests.
//!
//! These are opt-in because they require a reachable Postgres instance with the
//! `omega_memory_entries` table already created. Set `OMEGA_PG_TEST_URL` to run.

use omega_core::memory::{MemoryEntry, MemoryStore, MemoryWriteResult};
use omega_memory::PgMemoryStore;
use uuid::Uuid;

fn entry(namespace: &str, content: &str, importance: f64) -> MemoryEntry {
    MemoryEntry {
        id: None,
        content: content.to_string(),
        source: "test".to_string(),
        importance,
        created_at: None,
        namespace: namespace.to_string(),
        tags: vec![],
        domain: Default::default(),
        confidence: 1.0,
        version: 1,
        superseded_by: None,
        key: None,
        raw_artifact: None,
        tier: None,
    }
}

async fn make_store() -> Option<PgMemoryStore> {
    let url = match std::env::var("OMEGA_PG_TEST_URL") {
        Ok(u) => u,
        Err(_) => return None,
    };

    let store = match PgMemoryStore::new(&url).await {
        Ok(s) => s,
        Err(e) => {
            eprintln!("skipping pg tests: cannot connect ({e})");
            return None;
        }
    };

    // Probe for the required table via the trait API (no private field access).
    // If the table doesn't exist (or permissions are missing), skip.
    if let Err(e) = store.search("probe", 1).await {
        eprintln!("skipping pg tests: store not usable ({e})");
        return None;
    }

    Some(store)
}

#[tokio::test]
async fn pg_write_read_delete_roundtrip() {
    let Some(store) = make_store().await else {
        return;
    };

    let namespace = format!("pg-test-{}", Uuid::new_v4());
    let content = format!("hello from {namespace}");

    let id = match store
        .write(entry(&namespace, &content, 0.8))
        .await
        .expect("write failed")
    {
        MemoryWriteResult::Written(id) => id,
        MemoryWriteResult::Contradiction { new_id, .. } => new_id,
    };

    let fetched = store.read(&id).await.expect("read failed");
    assert!(fetched.is_some(), "entry should be readable after write");
    let fetched = fetched.unwrap();
    assert_eq!(fetched.content, content);
    assert_eq!(fetched.namespace, namespace);

    let deleted = store.delete(&id).await.expect("delete failed");
    assert!(deleted, "first delete should remove the entry");
    let deleted_again = store.delete(&id).await.expect("delete failed");
    assert!(!deleted_again, "second delete should return false");
}

#[tokio::test]
async fn pg_search_finds_written_entry() {
    let Some(store) = make_store().await else {
        return;
    };

    let namespace = format!("pg-test-{}", Uuid::new_v4());
    let marker = format!("marker-{}", Uuid::new_v4());
    let content = format!("pg search {marker} works");

    let id = match store
        .write(entry(&namespace, &content, 0.6))
        .await
        .expect("write failed")
    {
        MemoryWriteResult::Written(id) => id,
        MemoryWriteResult::Contradiction { new_id, .. } => new_id,
    };

    let hits = store.search(&marker, 20).await.expect("search failed");
    assert!(
        hits.iter().any(|e| e.id == Some(id.clone())),
        "expected search to return the inserted entry"
    );

    let _ = store.delete(&id).await;
}
