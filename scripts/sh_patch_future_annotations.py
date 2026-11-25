'''Inject `from __future__ import annotations` into ALL upstream musicdl files lacking it (Py3.8 compat shim).'''
import os
import sys

MARKER = 'from __future__ import annotations'
ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'musicdl')


def patch(path: str) -> None:
    with open(path, 'r', encoding='utf-8') as fp:
        content = fp.read()
    if MARKER in content:
        return
    lines = content.splitlines(keepends=True)
    insert_idx = 0
    for i, line in enumerate(lines[:20]):
        if line.startswith(('import ', 'from ')):
            insert_idx = i
            break
    lines.insert(insert_idx, MARKER + '\n')
    with open(path, 'w', encoding='utf-8', newline='') as fp:
        fp.write(''.join(lines))
    print('patched: %s' % path)


def main() -> None:
    count = 0
    for dirpath, _, filenames in os.walk(ROOT):
        for filename in filenames:
            if not filename.endswith('.py'): continue
            path = os.path.join(dirpath, filename)
            try:
                with open(path, 'r', encoding='utf-8') as fp:
                    needs = MARKER not in fp.read()
            except Exception:
                continue
            if needs:
                patch(path)
                count += 1
    print('total patched: %d' % count)


if __name__ == '__main__':
    main()
