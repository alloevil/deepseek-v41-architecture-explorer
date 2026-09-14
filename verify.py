#!/usr/bin/env python3
"""断言门禁:index.html 是否仍与 claims.json 里的三层来源一致。

用法: python3 verify.py            # 逐条检查,任一条失败则退出码 1
      python3 verify.py --json     # 机器可读输出

它不判断「报告说的对不对」(那是报告的事),只判断「页面有没有偏离已核实的事实」,
并且**把三层来源分开检查**:

  paper         报告(或 2017 论文)公布的数字 → 必须有 section + 逐字 quote + 页面片段
  derived       我们自己算出来的数字        → 必须有 formula + inputs,且 recompute 可复算
  visualization 为了画面做的取舍            → 必须同时记录 real_value 与 display_value,
                                             且页面必须带上说明用的 marker

改数字时同步改 claims.json,否则这里会红。
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
DOC = json.loads((ROOT / "claims.json").read_text(encoding="utf-8"))

SAFE = {"__builtins__": {}, "round": round, "abs": abs}


def check_paper():
    """报告公布的数字:收据完整 + 页面片段一致(正反两面)。"""
    results, failures = [], 0
    for c in DOC["claims"]:
        src, view = c["source"], c.get("viewer", {})
        problems = []
        if not src.get("quote") or not src.get("section"):
            problems.append("receipt incomplete: quote/section missing")
        if src.get("type") != "paper":
            problems.append(f"source.type must be 'paper', got {src.get('type')!r}")
        for s in view.get("must_contain", []):
            if s not in HTML:
                problems.append(f"missing: {s!r}")
        for s in view.get("must_not_contain", []):
            if s in HTML:
                problems.append(f"should be gone: {s!r}")
        if problems:
            failures += 1
        results.append({"id": c["id"], "layer": "paper",
                        "level": "error" if problems else "ok",
                        "section": src.get("section", "?"), "problems": problems})
    return results, failures


def check_derived():
    """我方推导:必须有公式与输入;能复算的必须复算通过;页面必须出现该数字。"""
    results, failures = [], 0
    for c in DOC.get("derived_claims", []):
        src = c.get("source", {})
        problems = []
        if src.get("type") != "derived":
            problems.append(f"source.type must be 'derived', got {src.get('type')!r}")
        if not src.get("formula"):
            problems.append("formula missing")
        if not src.get("inputs"):
            problems.append("inputs missing (a derived value must name what it is derived from)")
        rc = src.get("recompute")
        if rc:
            try:
                got = eval(rc["expr"], SAFE)  # noqa: S307 - repo-local gate, expression comes from claims.json
                if got != rc["expect"]:
                    problems.append(f"recompute mismatch: {rc['expr']} = {got}, expected {rc['expect']}")
            except Exception as e:  # noqa: BLE001
                problems.append(f"recompute failed: {rc.get('expr')!r} ({e})")
        elif c.get("value") != "approximate":
            problems.append("no recompute and the value is not declared 'approximate'")
        pm = c.get("page_marker")
        if not pm:
            problems.append("page_marker missing")
        elif pm not in HTML:
            problems.append(f"page_marker not found on the page: {pm!r}")
        if problems:
            failures += 1
        results.append({"id": c["id"], "layer": "derived",
                        "level": "error" if problems else "ok",
                        "section": src.get("formula", "?")[:60], "problems": problems})
    return results, failures


def check_visualization():
    """画面取舍:真实值与显示值都必须记录,且页面必须有说明文字。"""
    results, failures = [], 0
    for c in DOC.get("visualization_claims", []):
        src = c.get("source", {})
        problems = []
        if src.get("type") != "visualization":
            problems.append(f"source.type must be 'visualization', got {src.get('type')!r}")
        if not c.get("real_value"):
            problems.append("real_value missing (what the model actually does)")
        if not c.get("display_value"):
            problems.append("display_value missing (what the viewer draws)")
        if not src.get("note"):
            problems.append("note missing (why the two differ)")
        pm = c.get("page_marker")
        if not pm:
            problems.append("page_marker missing")
        elif pm not in HTML:
            problems.append(f"page_marker not found on the page: {pm!r}")
        if problems:
            failures += 1
        results.append({"id": c["id"], "layer": "visualization",
                        "level": "error" if problems else "ok",
                        "section": c.get("parameter", "?")[:60], "problems": problems})
    return results, failures


def check_absent():
    """报告没有的说法:必须留下「怎么核的」记录。"""
    results, failures = [], 0
    for r in DOC.get("removed_claims", []):
        if not r.get("checked"):
            failures += 1
            results.append({"id": r["id"], "layer": "paper", "level": "error", "section": "-",
                            "problems": ["absence check has no 'checked' record"]})
    return results, failures


def check():
    res = []
    fails = 0
    for fn in (check_paper, check_derived, check_visualization, check_absent):
        r, f = fn()
        res += r
        fails += f
    return res, fails


def main():
    results, failures = check()
    n_paper, n_derived, n_vis = (len(DOC["claims"]), len(DOC.get("derived_claims", [])),
                                 len(DOC.get("visualization_claims", [])))
    if "--json" in sys.argv:
        print(json.dumps({
            "tool": "dsv41-verify",
            "target": str(ROOT),
            "source": DOC["source"]["url"],
            "source_sha256": DOC["source"]["sha256"],
            "layers": {"paper": n_paper, "derived": n_derived, "visualization": n_vis},
            "summary": {"ok": len(results) - failures, "error": failures},
            "results": results,
        }, ensure_ascii=False))
        return 1 if failures else 0
    src = DOC["source"]
    print(f"dsv41-verify  {ROOT}")
    print(f"source: {src['title']} ({src['date']}, {src['pages']} pp.)")
    print(f"        {src['url']}")
    print(f"        sha256 {src['sha256']}\n")
    layer_now = None
    for r in results:
        if r["layer"] != layer_now:
            layer_now = r["layer"]
            label = {"paper": "PAPER        (报告公布)",
                     "derived": "DERIVED      (我方推导,含公式)",
                     "visualization": "VISUALIZATION(画面取舍,记录真实值)"}[layer_now]
            print(f"\n{label}")
        mark = "✓" if r["level"] == "ok" else "✗"
        print(f"  {mark} [{r['id']}] {r['section']}")
        for p in r["problems"]:
            print(f"      → {p}")
    ok = len(results) - failures
    print(f"\nverified: ok {ok} · error {failures} "
          f"(paper {n_paper} · derived {n_derived} · visualization {n_vis} · "
          f"{len(DOC.get('removed_claims', []))} report-absence records)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
