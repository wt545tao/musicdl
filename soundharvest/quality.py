'''
Function:
    SoundHarvest - best-quality engine
Author:
    SoundHarvest Team
License:
    PolyForm-Noncommercial-1.0.0 (inherited from musicdl)
Copyright:
    Derivative work of musicdl (https://github.com/CharlesPikachu/musicdl) by Zhenchao Jin.
'''
from __future__ import annotations
import copy
import logging
from typing import Dict, List, Optional, Tuple

try:
    from musicdl.modules import SongInfo
except ImportError:  # pragma: no cover
    from musicdl.modules.utils.data import SongInfo


'''settings'''
logger = logging.getLogger('soundharvest.quality')


'''quality ranking table (higher is better)'''
# lossless-first strategy: flac/wav/alac/ape/wv/tta/dsf/dff > 320k mp3 > aac > rest
LOSSLESS_EXTS = {'flac', 'wav', 'alac', 'ape', 'wv', 'tta', 'dsf', 'dff'}
EXT_SCORES = {'flac': 1000, 'wav': 1000, 'alac': 1000, 'ape': 990, 'wv': 990, 'tta': 990, 'dsf': 990, 'dff': 990, 'mp3': 400, 'aac': 300, 'm4a': 300, 'ogg': 250, 'opus': 260, 'wma': 200}
BITRATE_STEP_SCORES = ((320, 400), (256, 300), (192, 200), (128, 100))


'''QualityPolicy'''
class QualityPolicy(object):
    '''quality policy for best-track selection'''
    LOSSLESS = 'lossless'
    HIGH = 'high'
    STANDARD = 'standard'
    VALID_POLICIES = {LOSSLESS, HIGH, STANDARD}


'''qualityscore'''
def qualityscore(song_info: SongInfo) -> float:
    '''score a single SongInfo by audio quality; higher means better'''
    ext = str(song_info.ext or '').strip().lower().lstrip('.')
    score = float(EXT_SCORES.get(ext, 100))
    # lossless bonus
    if ext in LOSSLESS_EXTS: score += 500
    # bitrate bonus
    bitrate = song_info.bitrate
    if not bitrate and song_info.raw_data:
        bitrate = song_info.raw_data.get('bitrate') or song_info.raw_data.get('kbps')
    try:
        bitrate = int(bitrate)
    except (TypeError, ValueError):
        bitrate = 0
    if bitrate <= 0: return score
    for threshold, bonus in BITRATE_STEP_SCORES:
        if bitrate >= threshold:
            score += bonus
            break
    else:
        score += max(0.0, min(150.0, bitrate / 4.0))
    # bigger file usually means better quality among same ext
    try:
        score += min(50.0, float(song_info.file_size_bytes or 0) / (1024.0 * 1024.0))
    except Exception:
        pass
    return score


'''besttrack'''
def besttrack(song_infos: List[SongInfo], policy: str = QualityPolicy.LOSSLESS) -> Optional[SongInfo]:
    '''pick the best-quality track among candidates (None if empty)'''
    candidates = [si for si in (song_infos or []) if si is not None]
    if not candidates: return None
    if policy == QualityPolicy.STANDARD:
        scored = [(qualityscore(si), si) for si in candidates]
    else:
        pool = candidates
        if policy == QualityPolicy.LOSSLESS:
            lossless_pool = [si for si in candidates if str(si.ext or '').lstrip('.').lower() in LOSSLESS_EXTS]
            pool = lossless_pool or candidates
        elif policy == QualityPolicy.HIGH:
            high_pool = [si for si in candidates if qualityscore(si) >= 700]
            pool = high_pool or candidates
        scored = [(qualityscore(si), si) for si in pool]
    return copy.deepcopy(max(scored, key=lambda pair: pair[0])[1])


'''groupbyidentity'''
def groupbyidentity(song_infos: List[SongInfo]) -> Dict[Tuple[str, str], List[SongInfo]]:
    '''group SongInfo objects by (normalized songname, normalized singers)'''
    groups: Dict[Tuple[str, str], List[SongInfo]] = {}
    for si in song_infos:
        if si is None: continue
        key = (str(si.song_name or '').strip().lower(), str(si.singers or '').strip().lower())
        groups.setdefault(key, []).append(si)
    return groups


'''pickbesttracks'''
def pickbesttracks(song_infos: List[SongInfo], policy: str = QualityPolicy.LOSSLESS) -> List[SongInfo]:
    '''deduplicate by song identity then keep only the best-quality one per identity'''
    best_song_infos: List[SongInfo] = []
    for _, candidates in groupbyidentity(song_infos).items():
        picked = besttrack(candidates, policy=policy)
        if picked is not None: best_song_infos.append(picked)
    return best_song_infos


'''sortbyquality'''
def sortbyquality(song_infos: List[SongInfo], reverse: bool = True) -> List[SongInfo]:
    '''sort SongInfo list by quality score'''
    return sorted(song_infos, key=lambda si: qualityscore(si), reverse=reverse)
