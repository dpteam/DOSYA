"""Verify every relative link in the docs points at something real.

Run from the repo root. Exits non-zero on a broken link, so CI can use it.
"""
import os
import re
import sys

DOCS = ["README.md", "CONTRIBUTING.md"]


def doc_files():
    out = list(DOCS)
    d = "docs"
    if os.path.isdir(d):
        out += [os.path.join(d, f) for f in sorted(os.listdir(d))
                if f.endswith(".md")]
    return out


def refs_in(path):
    txt = open(path, encoding="utf-8").read()
    return re.findall(r"\]\(([^)]+)\)", txt) + re.findall(r'src="([^"]+)"', txt)


def main():
    bad = []
    checked = 0
    for doc in doc_files():
        base = os.path.dirname(doc)
        for ref in refs_in(doc):
            if ref.startswith(("http://", "https://", "#", "mailto:")):
                continue
            checked += 1
            target = os.path.normpath(os.path.join(base, ref.split("#")[0]))
            if not os.path.exists(target):
                bad.append("%s -> %s" % (doc, ref))

    print("checked %d relative links in %d files" % (checked, len(doc_files())))
    if bad:
        print("broken:")
        for b in bad:
            print("  " + b)
        return 1
    print("all documentation links resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
