//! Integration tests for [`SqliteMemoryStore`].
//!
//! Each test opens an in-memory SQLite database so tests are isolated and
//! leave no files on disk.

use omega_core::memory::{MemoryEntry, MemoryId, MemoryStore};
use omega_memory::SqliteMemoryStore;
use std::time::Duration;

/// Helper — open an isolated in-memory store with migrations applied.
async fn make_store() -> SqliteMemoryStore {
    let store = SqliteMemoryStore::new("sqlite::memory:")
        .await
        .expect("failed to open in-memory SQLite");
    store.migrate().await.expect("migration failed");
    store
}

/// Helper — build a minimal MemoryEntry with configurable content and importance.
fn entry(content: &str, source: &str, importance: f64) -> MemoryEntry {
    MemoryEntry {
        id: None,
        content: content.to_string(),
        source: source.to_string(),
        importance,
        created_at: None,
        namespace: "default".to_string(),
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

// ---------------------------------------------------------------------------
// Test 1 — write then read round-trip
// ---------------------------------------------------------------------------

#[tokio::test]
async fn write_read_roundtrip() {
    let store = make_store().await;

    let e = entry("The quick brown fox", "chat", 0.8);
    let id = store
        .write(e.clone())
        .await
        .expect("write failed")
        .into_id();

    let retrieved = store.read(&id).await.expect("read failed");
    assert!(retrieved.is_some(), "entry should exist after write");

    let retrieved = retrieved.unwrap();
    assert_eq!(retrieved.content, "The quick brown fox");
    assert_eq!(retrieved.source, "chat");
    // The stored id should match the returned id.
    assert_eq!(retrieved.id, Some(id));
}

// ---------------------------------------------------------------------------
// Test 2 — search returns results ordered by importance DESC
// ---------------------------------------------------------------------------

/// With LIKE search, results are ordered by importance DESC.
/// With semantic search, results are ordered by embedding similarity — importance order is not guaranteed.
#[tokio::test]
#[cfg(not(feature = "semantic-search"))]
async fn search_ordered_by_importance() {
    let store = make_store().await;

    store
        .write(entry("omega low relevance", "user", 0.1))
        .await
        .unwrap();
    store
        .write(entry("omega high relevance", "user", 0.9))
        .await
        .unwrap();
    store
        .write(entry("omega medium relevance", "user", 0.5))
        .await
        .unwrap();

    let hits = store.search("omega", 10).await.expect("search failed");
    assert_eq!(hits.len(), 3, "expected 3 hits");

    let importances: Vec<f64> = hits.iter().map(|e| e.importance).collect();
    for w in importances.windows(2) {
        assert!(
            w[0] >= w[1],
            "expected descending importance order, got {:?}",
            importances
        );
    }
    assert!(
        (importances[0] - 0.9).abs() < 0.01,
        "first hit should have importance ~0.9"
    );
}

/// With semantic search, all three entries with "omega" should still be found (limit=10).
#[tokio::test]
#[cfg(feature = "semantic-search")]
async fn search_returns_all_omega_entries() {
    let store = make_store().await;

    store
        .write(entry("omega low relevance", "user", 0.1))
        .await
        .unwrap();
    store
        .write(entry("omega high relevance", "user", 0.9))
        .await
        .unwrap();
    store
        .write(entry("omega medium relevance", "user", 0.5))
        .await
        .unwrap();

    let hits = store.search("omega", 10).await.expect("search failed");
    assert_eq!(hits.len(), 3, "expected 3 hits");
}

// ---------------------------------------------------------------------------
// Test 3 — search with no matching entries returns empty vec
// ---------------------------------------------------------------------------

/// LIKE search: tokens with no keyword overlap return empty.
/// Semantic search: every query has some similarity to every entry, so empty-result
/// assertions are not meaningful — skip this test when the feature is active.
#[tokio::test]
#[cfg(not(feature = "semantic-search"))]
async fn search_no_matches_returns_empty() {
    let store = make_store().await;

    store
        .write(entry("totally unrelated content", "agent", 0.7))
        .await
        .unwrap();

    let hits = store
        .search("xyzzy_no_match_at_all", 10)
        .await
        .expect("search should not error on no matches");

    assert!(
        hits.is_empty(),
        "expected empty results for unmatched query"
    );
}

/// Semantic search: search should not error, and respects the limit parameter.
#[tokio::test]
#[cfg(feature = "semantic-search")]
async fn search_does_not_error_with_semantic() {
    let store = make_store().await;

    store
        .write(entry("some content about memory systems", "agent", 0.7))
        .await
        .unwrap();

    let hits = store
        .search("xyzzy_no_match_at_all", 10)
        .await
        .expect("search should not error");

    // Semantic search may or may not return results — just verify no panic/error.
    assert!(hits.len() <= 10);
}

// ---------------------------------------------------------------------------
// Test 4 — duplicate writes produce distinct UUIDs
// ---------------------------------------------------------------------------

#[tokio::test]
async fn duplicate_writes_get_distinct_uuids() {
    let store = make_store().await;

    let e = entry("same content every time", "user", 0.5);

    // Write the same logical content three times, each with id=None so a new
    // UUID is generated for each.
    let id1 = store.write(e.clone()).await.unwrap().into_id();
    let id2 = store.write(e.clone()).await.unwrap().into_id();
    let id3 = store.write(e.clone()).await.unwrap().into_id();

    assert_ne!(id1, id2, "first and second write should have distinct ids");
    assert_ne!(id2, id3, "second and third write should have distinct ids");
    assert_ne!(id1, id3, "first and third write should have distinct ids");
}

// ---------------------------------------------------------------------------
// Test 5 — read returns None for unknown id
// ---------------------------------------------------------------------------

#[tokio::test]
async fn read_unknown_id_returns_none() {
    let store = make_store().await;

    let missing = MemoryId::new("00000000-0000-0000-0000-000000000000");
    let result = store.read(&missing).await.expect("read should not error");
    assert!(result.is_none(), "unknown id should return None");
}

// ---------------------------------------------------------------------------
// Test 6 — limit is respected in search
// ---------------------------------------------------------------------------

#[tokio::test]
async fn search_respects_limit() {
    let store = make_store().await;

    for i in 0..10 {
        store
            .write(entry(&format!("needle entry number {i}"), "agent", 0.5))
            .await
            .unwrap();
    }

    let hits = store.search("needle", 3).await.unwrap();
    assert_eq!(hits.len(), 3, "search should respect the limit parameter");
}

// ---------------------------------------------------------------------------
// Test 7 — decay task prunes low-importance entries
// ---------------------------------------------------------------------------

#[tokio::test]
async fn decay_prunes_low_importance_entries() {
    let store = make_store().await;

    let id = store
        .write(entry("temporary low-importance memory", "agent", 0.001))
        .await
        .unwrap()
        .into_id();

    // Run a very fast decay loop; decay_factor=1.0 so only pruning matters.
    let handle = store.spawn_decay_task(Duration::from_millis(10), 1.0, 0.01);

    tokio::time::sleep(Duration::from_millis(50)).await;
    handle.abort();

    let retrieved = store.read(&id).await.unwrap();
    assert!(retrieved.is_none(), "entry should be pruned by decay task");
}
