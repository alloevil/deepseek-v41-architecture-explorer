// One source of truth for the Cost Lab. Browser and future 2D renderers can import this.
export const KV_NAIVE = 36 * 1024;
export const KV_FP4 = 890;

export const LAB_REF = Object.freeze({ experts: 384, topK: 6, swa: 128, gTopK: 512, bits: 4, ctx: 1048576 });

export function labMetrics(state) {
  const precision = state.bits / 4;
  return {
    kvBytes: KV_FP4 * precision * state.ctx,
    swaCache: state.swa * precision,
    attentionRead: state.gTopK * precision + state.swa * precision * 0.1,
    moeCompute: state.topK,
    communication: state.topK,
    capacity: state.experts,
  };
}

export function compareToReference(state) {
  const value = labMetrics(state);
  const reference = labMetrics(LAB_REF);
  return Object.fromEntries(Object.keys(value).map(key => [key, value[key] / reference[key]]));
}
