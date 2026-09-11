#!/usr/bin/env python3
"""断言门禁:index.html 是否仍与 claims.json 里的技术报告原文一致。

用法: python3 verify.py            # 逐条检查,任一条失败则退出码 1
      python3 verify.py --json     # 机器可读输出

它不判断「报告说的对不对」(那是报告的事),只判断「页面有没有偏离已核实的事实」:
每个 claim 的 must_contain 必须出现、must_not_contain 必须不出现。改数字时同步改
claims.json,否则这里会红。
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
DOC = json.loads((ROOT / "claims.json").read_text(encoding="utf-8"))


def check():
    results, failures = [], 0
    for c in DOC["claims"]:
        src, view = c["source"], c["viewer"]
        problems = []
        if not src.get("quote") or not src.get("section"):
            problems.append("receipt incomplete: quote/section missing")
        for s in view["must_contain"]:
            if s not in HTML:
                problems.append(f"missing: {s!r}")
        for s in view.get("must_not_contain", []):
            if s in HTML:
                problems.append(f"should be gone: {s!r}")
        if problems:
            failures += 1
        results.append({"id": c["id"], "level": "error" if problems else "ok",
                        "section": src.get("section", "?"), "problems": problems})
    # the report-absence checks must at least be recorded with how they were checked
    for r in DOC.get("removed_claims", []):
        if not r.get("checked"):
            failures += 1
            results.append({"id": r["id"], "level": "error", "section": "-",
                            "problems": ["absence check has no 'checked' record"]})
    return results, failures


def main():
    results, failures = check()
    if "--json" in sys.argv:
        print(json.dumps({
            "tool": "dsv41-verify",
            "target": str(ROOT),
            "source": DOC["source"]["url"],
            "source_sha256": DOC["source"]["sha256"],
            "summary": {"ok": len(results) - failures, "error": failures},
            "results": results,
        }, ensure_ascii=False))
        return 1 if failures else 0
    src = DOC["source"]
    print(f"dsv41-verify  {ROOT}")
    print(f"source: {src['title']} ({src['date']}, {src['pages']} pp.)")
    print(f"        {src['url']}")
    print(f"        sha256 {src['sha256']}\n")
    for r in results:
        mark = "✓" if r["level"] == "ok" else "✗"
        print(f"  {mark} [{r['id']}] {r['section']}")
        for p in r["problems"]:
            print(f"      → {p}")
    ok = len(results) - failures
    print(f"\nverified: ok {ok} · error {failures} "
          f"({len(DOC['claims'])} claims, {len(DOC.get('removed_claims', []))} report-absence records)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
