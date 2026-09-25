// Scene-level constants shared by future renderers.
export const MOE_GRID = Object.freeze({ columns: 24, rows: 16, expertsPerLayer: 384 });
export const REAL_V41 = Object.freeze({ layers: 40, routedExpertsPerLayer: 384, activeRoutedExperts: 6, context: 1048576 });
export const DISPLAY_POLICY = Object.freeze({
  expertGrid: 'one layer mapped to a 24×16 grid; V4.1 has 40 such layer sets',
  sideModules: 'ViT, Engram and DSpark positions are visualization layout choices',
});
