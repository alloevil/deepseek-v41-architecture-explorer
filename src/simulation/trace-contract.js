// Contract shared by the Walk renderer, future trace exporters, and Verify UI.
export const TRACE_LAYERS = Object.freeze(['swa', 'full', 'reindex', 'reuse']);
export const TRACE_FIELDS = Object.freeze({
  schedule: 'paper',
  visiblePositions: 'derived',
  globalRead: 'paper',
  windowRead: 'paper',
  newKV: 'derived',
  reusedKV: 'paper',
  reusedIndex: 'paper',
  experts: 'simulated',
  mhcStreams: 'simulated',
});

export const TRACE_LIMITATION =
  'Router weights, mHC coefficients, and per-token KV selections are not published for V4.1; those fields are simulated.';
