'''
Function:
    SoundHarvest - harvest client wrapping musicdl engine
Author:
    SoundHarvest Team
License:
    PolyForm-Noncommercial-1.0.0 (inherited from musicdl)
Copyright:
    Derivative work of musicdl (https://github.com/CharlesPikachu/musicdl) by Zhenchao Jin.
'''
from __future__ import annotations
import copy
import os
from typing import Dict, List, Optional

from musicdl import musicdl as musicdl_pkg
from musicdl.modules import SongInfo, MusicClientBuilder

from .quality import QualityPolicy, besttrack, pickbesttracks, qualityscore, sortbyquality
from .session import HarvestQueue


'''settings'''
__title__ = 'soundharvest'
__version__ = '0.1.0'
DEFAULT_SOURCES = ['MiguMusicClient', 'NeteaseMusicClient', 'QQMusicClient', 'KuwoMusicClient', 'QianqianMusicClient']


'''HarvestClient'''
class HarvestClient(object):
    '''SoundHarvest client: musicdl engine + best-quality picking + batch queue + custom output dir'''
    def __init__(self, music_sources: List[str] = None, download_dir: str = None, policy: str = QualityPolicy.LOSSLESS, best_only: bool = True,
                 init_music_clients_cfg: Dict[str, Dict] = None, clients_threadings: Dict[str, int] = None, requests_overrides: Dict[str, Dict] = None, search_rules: Dict[str, Dict] = None):
        self.policy = policy if policy in QualityPolicy.VALID_POLICIES else QualityPolicy.LOSSLESS
        self.best_only = bool(best_only)
        self.download_dir = os.path.abspath(download_dir) if download_dir else None
        init_music_clients_cfg = copy.deepcopy(init_music_clients_cfg or {})
        # route every source's work_dir under user's download_dir
        if self.download_dir:
            for source in (music_sources or DEFAULT_SOURCES):
                cfg = init_music_clients_cfg.setdefault(source, {})
                if not cfg.get('work_dir'): cfg['work_dir'] = self.download_dir
        self.engine = musicdl_pkg.MusicClient(
            music_sources=music_sources or DEFAULT_SOURCES, init_music_clients_cfg=init_music_clients_cfg,
            clients_threadings=copy.deepcopy(clients_threadings or {}), requests_overrides=copy.deepcopy(requests_overrides or {}),
            search_rules=copy.deepcopy(search_rules or {}),
        )
        self.queue = HarvestQueue(best_only=self.best_only, policy=self.policy)
    '''search'''
    def search(self, keyword: str) -> Dict[str, List[SongInfo]]:
        return self.engine.search(keyword=keyword)
    '''bestmatches'''
    def bestmatches(self, search_results: Dict[str, List[SongInfo]]) -> List[SongInfo]:
        '''flatten search results and keep the best-quality SongInfo per song identity'''
        flattened: List[SongInfo] = []
        for items in (search_results or {}).values(): flattened.extend(items)
        return pickbesttracks(flattened, policy=self.policy)
    '''collect'''
    def collect(self, search_results: Dict[str, List[SongInfo]] = None, song_infos: List[SongInfo] = None) -> int:
        '''batch add search results (best-quality-filtered) or explicit song_infos into queue'''
        if song_infos is not None: return self.queue.add(song_infos)
        return self.queue.add(self.bestmatches(search_results or {}))
    '''downloadqueue'''
    def downloadqueue(self, song_infos: List[SongInfo] = None) -> List[SongInfo]:
        '''download queued songs (or given list) into download_dir'''
        items = self.queue.popall() if song_infos is None else song_infos
        if not items: return []
        if self.best_only: items = pickbesttracks(items, policy=self.policy)
        return self.engine.download(song_infos=items)
    '''download'''
    def download(self, song_infos) -> List[SongInfo]:
        '''direct download of SongInfo / list / dict {source: [SongInfo]}'''
        return self.engine.download(song_infos=song_infos)
    '''parseplaylist'''
    def parseplaylist(self, playlist_url: str) -> List[SongInfo]:
        return self.engine.parseplaylist(playlist_url)
    '''collectplaylist'''
    def collectplaylist(self, playlist_url: str) -> int:
        '''parse playlist and batch add all tracks into queue; returns added count'''
        return self.queue.add(self.parseplaylist(playlist_url))
    '''remove'''
    def remove(self, **kwargs) -> int:
        '''batch remove from queue; kwargs pass through HarvestQueue.remove (indices/song_infos/keyword/source/clear_all)'''
        return self.queue.remove(**kwargs)
    '''queuesummary'''
    def queuesummary(self) -> List[Dict]:
        return self.queue.summary()
    '''downloadbest'''
    def downloadbest(self, keyword: str) -> List[SongInfo]:
        '''one-shot: search -> pick best quality per song -> download'''
        return self.downloadqueue(song_infos=self.bestmatches(self.search(keyword)))
    '''str'''
    def __str__(self):
        return 'SoundHarvest v%s — auto-pick best quality, batch collect, download anywhere.\nBased on musicdl by Zhenchao Jin (PolyForm-Noncommercial).' % (__version__)
