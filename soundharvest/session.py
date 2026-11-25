'''
Function:
    SoundHarvest - batch download queue (add / remove / persist)
Author:
    SoundHarvest Team
License:
    PolyForm-Noncommercial-1.0.0 (inherited from musicdl)
Copyright:
    Derivative work of musicdl (https://github.com/CharlesPikachu/musicdl) by Zhenchao Jin.
'''
from __future__ import annotations
import json
import os
import threading
from itertools import chain
from typing import Any, Dict, List, Optional

from musicdl.modules import SongInfo

from .quality import pickbesttracks, qualityscore


'''HarvestQueue'''
class HarvestQueue(object):
    '''batch queue holding SongInfo objects selected from one or more searches'''
    def __init__(self, auto_dedup: bool = True, best_only: bool = False, policy: str = 'lossless'):
        self.auto_dedup = auto_dedup
        self.best_only = best_only
        self.policy = policy
        self._items: List[SongInfo] = []
        self._keys: set = set()
    '''keyof'''
    @staticmethod
    def keyof(song_info: SongInfo) -> str:
        return '|'.join([str(getattr(song_info, f, None) or '') for f in ('source', 'identifier', 'song_name', 'singers', 'ext')])
    '''add'''
    def add(self, song_infos: Any, replace: bool = False) -> int:
        '''batch add; accepts SongInfo / list / dict {source: [SongInfo]}; returns added count'''
        if song_infos is None: return 0
        if isinstance(song_infos, dict):
            candidates = list(chain.from_iterable([v if isinstance(v, (list, tuple)) else [v] for v in song_infos.values()]))
        elif isinstance(song_infos, (list, tuple)):
            candidates = list(song_infos)
        else:
            candidates = [song_infos]
        if self.best_only: candidates = pickbesttracks(candidates, policy=self.policy)
        added = 0
        if replace:
            self.clear()
        for si in candidates:
            if si is None or not isinstance(si, SongInfo): continue
            key = self.keyof(si)
            if self.auto_dedup and key in self._keys: continue
            self._keys.add(key); self._items.append(si); added += 1
        return added
    '''remove'''
    def remove(self, indices: List[int] = None, song_infos: Any = None, keyword: str = None, source: str = None, clear_all: bool = False) -> int:
        '''batch remove by indices / matched SongInfo objects / keyword / source; returns removed count'''
        if clear_all:
            removed = len(self._items); self.clear(); return removed
        doomed: set = set()
        if indices:
            for idx in indices:
                if isinstance(idx, int) and 0 <= idx < len(self._items): doomed.add(idx)
        if song_infos is not None:
            if not isinstance(song_infos, (list, tuple)): song_infos = [song_infos]
            for si in song_infos:
                if isinstance(si, SongInfo):
                    for i, item in enumerate(self._items):
                        if self.keyof(item) == self.keyof(si): doomed.add(i)
        if keyword:
            kw = str(keyword).lower()
            for i, item in enumerate(self._items):
                if kw in str(item.song_name or '').lower() or kw in str(item.singers or '').lower() or kw in str(item.album or '').lower(): doomed.add(i)
        if source:
            for i, item in enumerate(self._items):
                if str(item.source) == str(source): doomed.add(i)
        kept = [item for i, item in enumerate(self._items) if i not in doomed]
        removed = len(self._items) - len(kept)
        self._items = kept
        self._keys = {self.keyof(item) for item in kept}
        return removed
    '''list'''
    def list(self) -> List[SongInfo]:
        return list(self._items)
    '''summary'''
    def summary(self) -> List[Dict[str, Any]]:
        def shortsource(source: Optional[str]) -> str:
            source = str(source or '')
            return source[:-len('MusicClient')] if source.endswith('MusicClient') else source
        return [{'idx': i, 'source': shortsource(si.source), 'song_name': si.song_name, 'singers': si.singers, 'album': si.album, 'ext': si.ext, 'file_size': si.file_size, 'duration': si.duration, 'quality_score': round(qualityscore(si), 1)} for i, si in enumerate(self._items)]
    '''popall'''
    def popall(self) -> List[SongInfo]:
        items = list(self._items); self.clear(); return items
    '''clear'''
    def clear(self):
        self._items = []; self._keys = set()
    '''len'''
    def __len__(self) -> int:
        return len(self._items)
    '''savetojson'''
    def savetojson(self, filepath: str) -> str:
        data = {'version': 1, 'policy': self.policy, 'best_only': self.best_only, 'items': [si.todict() for si in self._items]}
        with open(filepath, 'w', encoding='utf-8') as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
        return filepath
    '''loadfromjson'''
    @classmethod
    def loadfromjson(cls, filepath: str, **kwargs) -> "HarvestQueue":
        with open(filepath, 'r', encoding='utf-8') as fp:
            data = json.load(fp)
        queue = cls(best_only=bool(data.get('best_only', False)), policy=data.get('policy', 'lossless'), **kwargs)
        for item in data.get('items', []):
            try: queue.add(SongInfo.fromdict(item))
            except Exception: continue
        return queue
