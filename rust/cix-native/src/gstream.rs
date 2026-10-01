//! Ordered independent-frame streaming. One bounded CPU pool and one shared
//! scratch-memory ledger serve all blocks; stateful CIXM6 remains sequential.
use super::*;
use std::collections::VecDeque;

struct Completed {
    input: Vec<u8>,
    route: u8,
    payload: Vec<u8>,
    hash: [u8; 32],
    stats: AutoSelectionStats,
}

fn pipeline_error(error: parallel::PipelineError) -> String {
    match error {
        parallel::PipelineError::Worker(message) => message,
        parallel::PipelineError::WorkerPanic => "block encoder panicked".into(),
        parallel::PipelineError::Cancelled => "block encoding cancelled".into(),
    }
}

fn emit<W: Write>(
    dst: &mut W,
    mut item: Completed,
    totals: &mut AutoSelectionStats,
    archive_bytes: &mut u64,
    free: &mut VecDeque<Vec<u8>>,
) -> Result<(), String> {
    check_interrupted()?;
    put_frame(
        dst,
        item.route,
        item.input.len() as u32,
        u32::try_from(item.payload.len()).map_err(|_| "frame payload length overflow")?,
        &item.hash,
    )
    .map_err(ioerr)?;
    dst.write_all(&item.payload).map_err(ioerr)?;
    dst.flush().map_err(ioerr)?;
    *archive_bytes = archive_bytes
        .checked_add(41 + item.payload.len() as u64)
        .ok_or("archive length overflow")?;
    totals.blocks += item.stats.blocks;
    totals.profile_seconds += item.stats.profile_seconds;
    totals.search_seconds += item.stats.search_seconds;
    totals.candidate_seconds += item.stats.candidate_seconds;
    totals.candidate_attempts += item.stats.candidate_attempts;
    totals.memory_skips += item.stats.memory_skips;
    totals.budget_skips += item.stats.budget_skips;
    for (total, bytes) in totals
        .selected_source_bytes
        .iter_mut()
        .zip(item.stats.selected_source_bytes)
    {
        *total += bytes;
    }
    for explanation in item.stats.explanations.drain(..) {
        eprintln!("cix: region={} {}", totals.blocks, explanation);
    }
    item.input.clear();
    free.push_back(item.input);
    Ok(())
}

fn wait_one<W: Write>(
    pipeline: &mut parallel::OrderedPipeline<Vec<u8>, Completed>,
    dst: &mut W,
    totals: &mut AutoSelectionStats,
    archive_bytes: &mut u64,
    free: &mut VecDeque<Vec<u8>>,
) -> Result<(), String> {
    loop {
        check_interrupted()?;
        match pipeline
            .recv_next_timeout(Duration::from_millis(50))
            .map_err(pipeline_error)?
        {
            parallel::Poll::Item(item) => return emit(dst, item, totals, archive_bytes, free),
            parallel::Poll::Pending => {}
            parallel::Poll::Finished => {
                return Err("pipeline finished before expected frame".into())
            }
        }
    }
}

pub(super) fn encode<R: Read, W: Write>(
    mut src: R,
    mut dst: W,
    block: u32,
    level: u8,
    forced: Option<&str>,
    backend: &str,
    backend_set: bool,
    format: &str,
    input_fd: i32,
    flush_interval: Option<Duration>,
    memory: usize,
    workers: usize,
    explain: bool,
    verbose: bool,
) -> Result<(), String> {
    let magic = native_magic(format, level, backend, backend_set);
    let resolved_format = if magic == MAGIC_V2 { "cixg2" } else { "cixg1" };
    // Two retained buffers per outstanding job (source and winning payload),
    // one reader block, thread stacks, and bounded descriptor/stat overhead.
    let retained = parallel_retained(block, workers);
    if retained >= memory {
        return Err(
            "parallel block buffers and thread stacks exceed --memory; reduce --threads".into(),
        );
    }
    let budget = resources::MemoryBudget::new(memory - retained);
    let worker_budget = budget.clone();
    let forced_id = forced.map(route_id).transpose()?;
    let backend = backend.to_owned();
    let cancelled = std::sync::Arc::new(AtomicBool::new(false));
    let worker_cancelled = cancelled.clone();
    // Output polling and input reads must observe a failed sibling too.
    let _output_cancel = crate::limits::CancellationGuard::new(cancelled.clone());
    let mut pipeline = parallel::OrderedPipeline::new_with_cancellation(
        workers,
        workers,
        cancelled,
        move |input: Vec<u8>| {
            let _cancel = crate::limits::CancellationGuard::new(worker_cancelled.clone());
            check_interrupted()?;
            let hash = Sha256::digest(&input).into();
            let mut stats = AutoSelectionStats::default();
            let override_backend = backend_set.then_some(backend.as_str());
            let (route, payload) = if let Some(id) = forced_id {
                select_cixg_fixed_route(
                    id,
                    &input,
                    override_backend,
                    resolved_format,
                    selector_effort_name(level),
                    &worker_budget,
                    1,
                    &mut stats,
                    explain,
                )?
            } else {
                select_cixg_auto(
                    &input,
                    level,
                    override_backend,
                    resolved_format,
                    &worker_budget,
                    1,
                    &mut stats,
                    explain,
                )?
            };
            Ok(Completed {
                input,
                route,
                payload,
                hash,
                stats,
            })
        },
    )
    .map_err(str::to_owned)?;

    let result = (|| -> Result<(), String> {
        dst.write_all(magic).map_err(ioerr)?;
        dst.write_all(&block.to_le_bytes()).map_err(ioerr)?;
        dst.write_all(&0u32.to_le_bytes()).map_err(ioerr)?;
        let mut buffer = vec![0u8; block as usize];
        let mut filled = 0usize;
        let mut counts = [0u32; 256];
        let mut since: Option<Instant> = None;
        let mut free = VecDeque::new();
        let mut whole = Sha256::new();
        let mut source_bytes = 0u64;
        let mut archive_bytes = HEADER as u64;
        let mut totals = AutoSelectionStats::default();
        let mut eof = false;
        let mut peak_outstanding = 0usize;
        loop {
            check_interrupted()?;
            while let parallel::Poll::Item(item) =
                pipeline.try_recv_next().map_err(pipeline_error)?
            {
                emit(&mut dst, item, &mut totals, &mut archive_bytes, &mut free)?;
            }
            // Do not read ahead while the writer's ordered output is backlogged.
            while pipeline.outstanding() == pipeline.capacity() {
                wait_one(
                    &mut pipeline,
                    &mut dst,
                    &mut totals,
                    &mut archive_bytes,
                    &mut free,
                )?;
            }
            let expired = since
                .zip(flush_interval)
                .is_some_and(|(start, interval)| start.elapsed() >= interval);
            if filled == buffer.len() || filled != 0 && (expired || eof) {
                if counts.iter().map(|&n| n as usize).sum::<usize>() != filled {
                    return Err("internal block symbol count mismatch".into());
                }
                buffer.truncate(filled);
                whole.update(&buffer);
                source_bytes = source_bytes
                    .checked_add(filled as u64)
                    .ok_or("input length overflow")?;
                match pipeline.try_submit(buffer) {
                    Ok(()) => {}
                    Err(parallel::TrySubmitError::Cancelled(_)) => {
                        return Err(pipeline
                            .try_recv_next()
                            .err()
                            .map(pipeline_error)
                            .unwrap_or_else(|| "block encoding cancelled".into()));
                    }
                    Err(_) => return Err("pipeline admission invariant failed".into()),
                }
                peak_outstanding = peak_outstanding.max(pipeline.outstanding());
                buffer = free.pop_front().unwrap_or_default();
                buffer.resize(block as usize, 0);
                filled = 0;
                counts.fill(0);
                since = None;
                continue;
            }
            if eof {
                break;
            }
            let mut timeout = since
                .zip(flush_interval)
                .map(|(start, interval)| interval.saturating_sub(start.elapsed()));
            if pipeline.outstanding() != 0 {
                timeout = Some(timeout.map_or(Duration::from_millis(50), |wait| {
                    wait.min(Duration::from_millis(50))
                }));
            }
            match read_poll(&mut src, &mut buffer[filled..], input_fd, timeout)? {
                Some(0) => eof = true,
                Some(n) => {
                    for &byte in &buffer[filled..filled + n] {
                        counts[byte as usize] += 1;
                    }
                    filled += n;
                    since.get_or_insert_with(Instant::now);
                }
                None => {}
            }
        }
        pipeline.close();
        while pipeline.outstanding() != 0 {
            wait_one(
                &mut pipeline,
                &mut dst,
                &mut totals,
                &mut archive_bytes,
                &mut free,
            )?;
        }
        pipeline.finish().map_err(pipeline_error)?;
        check_interrupted()?;
        put_frame(&mut dst, END, 0, 0, &whole.finalize().into()).map_err(ioerr)?;
        archive_bytes = archive_bytes
            .checked_add(41)
            .ok_or("archive length overflow")?;
        dst.flush().map_err(ioerr)?;
        if verbose || explain {
            let routes = totals
                .selected_source_bytes
                .iter()
                .enumerate()
                .filter(|(_, n)| **n != 0)
                .map(|(id, n)| format!("{}:{n}", selection::ROUTES[id]))
                .collect::<Vec<_>>()
                .join(",");
            eprintln!("cix: effort={} format={} parallelism=blocks workers={} queue_capacity={} peak_outstanding={} reserved_buffers={} peak_scratch_reserved={} source_bytes={} blocks={} candidates={} memory_skips={} budget_skips={} analyse_seconds={:.3} candidate_seconds={:.3} search_seconds={:.3} archive_bytes={} selected_source_bytes=[{}]",
            effort_display_name(level), resolved_format, workers, workers, peak_outstanding, retained,
            budget.stats().peak_reserved_bytes, source_bytes, totals.blocks, totals.candidate_attempts,
            totals.memory_skips, totals.budget_skips, totals.profile_seconds, totals.candidate_seconds,
            totals.search_seconds, archive_bytes, routes);
        }
        Ok(())
    })();
    // Cooperative I/O cancellation is secondary to the original worker error.
    result.map_err(|error| pipeline.failure().map(pipeline_error).unwrap_or(error))
}
