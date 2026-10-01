//! Cooperative cancellation for candidate work.
//!
//! The flag is process-wide because Ctrl-C is process-wide.  Candidate
//! deadlines are deliberately thread-local: an expensive worker must not
//! cancel unrelated decoding or output work on another thread.
use std::cell::{Cell, RefCell};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};

/// Set by the CLI's interruption handler.  Workers only observe it at safe
/// codec polling points and return an error before publishing a partial frame.
pub static INTERRUPTED: AtomicBool = AtomicBool::new(false);

pub const INTERRUPTED_ERROR: &str = "CIX interrupted";
pub const CANCELLED_ERROR: &str = "CIX candidate cancelled";
pub const DEADLINE_ERROR: &str = "CIX candidate deadline exceeded";

thread_local! {
    static DEADLINE: Cell<Option<Instant>> = const { Cell::new(None) };
    static CANCELLATION: RefCell<Option<Arc<AtomicBool>>> = const { RefCell::new(None) };
}

/// Installs a pipeline-local cancellation token for this thread.  A worker
/// failure can set that token to stop its peers without pretending that the
/// user interrupted the whole process.
#[must_use]
pub struct CancellationGuard {
    // Keeps the installed token alive even if the caller drops its Arc while
    // the guarded operation is still running.
    _current: Arc<AtomicBool>,
    previous: Option<Arc<AtomicBool>>,
}

impl CancellationGuard {
    pub fn new(token: Arc<AtomicBool>) -> Self {
        let previous = CANCELLATION.with(|slot| slot.replace(Some(token.clone())));
        Self {
            _current: token,
            previous,
        }
    }
}

impl Drop for CancellationGuard {
    fn drop(&mut self) {
        CANCELLATION.with(|slot| {
            slot.replace(self.previous.take());
        });
    }
}

/// Installs a deadline for the current thread and restores the prior one when
/// dropped.  Nested candidate searches therefore cannot leak their budget to
/// their caller.
#[must_use]
pub struct DeadlineGuard {
    previous: Option<Instant>,
}

impl DeadlineGuard {
    pub fn new(duration: Duration) -> Self {
        let previous = DEADLINE.with(|slot| {
            let old = slot.get();
            // A nested scope may narrow a budget but cannot evade an outer
            // deadline by asking for more time.
            let requested = Instant::now().checked_add(duration);
            let deadline = match (old, requested) {
                (Some(outer), Some(inner)) => Some(outer.min(inner)),
                (Some(outer), None) => Some(outer),
                (None, requested) => requested,
            };
            slot.set(deadline);
            old
        });
        Self { previous }
    }
}

impl Drop for DeadlineGuard {
    fn drop(&mut self) {
        DEADLINE.with(|slot| slot.set(self.previous));
    }
}

/// Returns a stable error for cancellation or expiry.  Cancellation has
/// priority so Ctrl-C is never reported as an ordinary candidate timeout.
#[inline]
pub fn check() -> Result<(), String> {
    if INTERRUPTED.load(Ordering::Relaxed) {
        return Err(INTERRUPTED_ERROR.into());
    }
    let cancelled = CANCELLATION.with(|slot| {
        slot.borrow()
            .as_ref()
            .is_some_and(|token| token.load(Ordering::Relaxed))
    });
    if cancelled {
        return Err(CANCELLED_ERROR.into());
    }
    let expired = DEADLINE.with(|slot| slot.get().is_some_and(|at| Instant::now() >= at));
    if expired {
        Err(DEADLINE_ERROR.into())
    } else {
        Ok(())
    }
}
