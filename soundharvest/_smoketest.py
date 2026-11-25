'''SoundHarvest smoke tests (offline, no network calls)'''
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from musicdl.modules import SongInfo
from soundharvest import HarvestClient, HarvestQueue, QualityPolicy, besttrack, pickbesttracks, qualityscore


def mk(name, ext, bitrate=None, size_mb=8, source='NeteaseMusicClient', singers='Tester'):
    return SongInfo(source=source, song_name=name, singers=singers, album='Album', ext=ext,
                    file_size='%dMB' % size_mb, file_size_bytes=int(size_mb * 1024 * 1024),
                    duration='04:00', bitrate=bitrate, identifier='%s-%s' % (name, ext))


'''T1 quality score order: flac > 320mp3 > aac'''
a, b, c = mk('s', 'flac'), mk('s', 'mp3', 320), mk('s', 'aac', 128)
assert qualityscore(a) > qualityscore(b) > qualityscore(c), 'score order broken'
print('T1 quality score order: OK (%.0f > %.0f > %.0f)' % (qualityscore(a), qualityscore(b), qualityscore(c)))

'''T2 besttrack lossless policy'''
bt = besttrack([c, b, a], policy=QualityPolicy.LOSSLESS)
assert bt.ext == 'flac', 'besttrack failed'
print('T2 besttrack picks flac: OK')

'''T3 lossless fallback when no lossless exists'''
bt2 = besttrack([c, b], policy=QualityPolicy.LOSSLESS)
assert bt2.ext == 'mp3', 'fallback failed'
print('T3 fallback to best available: OK')

'''T4 pickbesttracks dedup keeps one best per identity'''
mixed = [mk('s', 'flac'), mk('s', 'mp3', 320), mk('t', 'aac', 128, source='QQMusicClient')]
picked = pickbesttracks(mixed)
assert len(picked) == 2 and any(p.ext == 'flac' for p in picked), 'dedup failed'
print('T4 dedup + best per identity: OK')

'''T5 queue add/remove batch ops'''
q = HarvestQueue()
n1 = q.add([a, b, c]); assert n1 == 3, 'add failed'
n2 = q.add([mk('s', 'flac')], replace=False); assert n2 == 0, 'dedup failed'
n3 = q.add([mk('s', 'wav')]); assert n3 == 1, 'new ext should add'
r1 = q.remove(indices=[0, 1]); assert r1 == 2 and len(q) == 2
n4 = q.add([a, b, c]); assert n4 == 2, 'only removed items re-added'
r2 = q.remove(song_infos=[b]); assert r2 == 1 and len(q) == 3
q.add([mk('unicorn', 'mp3', 128, singers='Voc')])
r3 = q.remove(keyword='uni'); assert r3 == 1 and len(q) == 3, 'keyword remove failed'
r4 = q.remove(clear_all=True); assert r4 == 3 and len(q) == 0
print('T5 queue batch add/remove/dedup: OK')

'''T6 queue persistence roundtrip'''
q2 = HarvestQueue(); q2.add([a, b])
fp = os.path.join(tempfile.gettempdir(), 'sh_queue_test.json')
q2.savetojson(fp)
q3 = HarvestQueue.loadfromjson(fp)
assert len(q3) == 2, 'persist failed'
os.remove(fp)
print('T6 queue save/load roundtrip: OK')

'''T7 HarvestClient init with custom download dir'''
client = HarvestClient(music_sources=['NeteaseMusicClient'], download_dir=tempfile.gettempdir(), best_only=True)
wd = client.engine.music_clients['NeteaseMusicClient'].work_dir
assert os.path.isabs(wd), 'work_dir not absolute'
print('T7 download_dir routed to work_dir: OK (%s)' % wd)

'''T8 best_only queue filters to lossless'''
client2 = HarvestClient(music_sources=['NeteaseMusicClient'], best_only=True, policy=QualityPolicy.LOSSLESS)
client2.collect(song_infos=[c, b, a, mk('t', 'aac', 128, source='QQMusicClient')])
assert len(client2.queue) == 2 and any(si.ext == 'flac' for si in client2.queue.list()), 'best_only collect failed'
print('T8 best_only collect: OK')
print('ALL SMOKE TESTS PASSED')
