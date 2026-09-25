// Shared epistemic contract. Renderers and inspectors must preserve this distinction.
export const PROVENANCE_TYPES = Object.freeze({
  PAPER: 'paper',
  DERIVED: 'derived',
  MEASURED: 'measured',
  SIMULATED: 'simulated',
  VISUALIZATION: 'visualization',
});

export const SOURCE_LABELS = Object.freeze({
  paper: { zh: '报告', en: 'paper' },
  derived: { zh: '推导', en: 'derived' },
  measured: { zh: '实测', en: 'measured' },
  simulated: { zh: '模拟', en: 'simulated' },
  visualization: { zh: '示意', en: 'schematic' },
});

export const REAL_MODEL_LIMIT =
  'DeepSeek-V4.1-Flash router weights and per-token traces are not public; V4.1 traces in this viewer are specification-faithful simulations.';
