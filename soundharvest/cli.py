'''
Function:
    SoundHarvest - command line interface
Author:
    SoundHarvest Team
License:
    PolyForm-Noncommercial-1.0.0 (inherited from musicdl)
Copyright:
    Derivative work of musicdl (https://github.com/CharlesPikachu/musicdl) by Zhenchao Jin.
'''
from __future__ import annotations
import click

from .core import DEFAULT_SOURCES, HarvestClient, __version__
from .quality import QualityPolicy


'''settings'''
BANNER = '''SoundHarvest v%s — harvest the best-quality audio across sources
Engine: musicdl by Zhenchao Jin (https://github.com/CharlesPikachu/musicdl)
License: PolyForm-Noncommercial-1.0.0 — personal / educational use ONLY.
By continuing you agree to respect copyright: download only what you are
authorized to access; do not redistribute or use commercially.''' % (__version__)


'''brandcmd'''
@click.command(name='soundharvest')
@click.version_option(version=__version__, prog_name='soundharvest')
@click.option('-k', '--keyword', default=None, help='Search keyword; empty starts interactive mode.', type=str)
@click.option('-p', '--playlist-url', '--playlist_url', default=None, help='Parse a playlist URL and collect its tracks into the batch queue.', type=str)
@click.option('-m', '--music-sources', '--music_sources', default=','.join(DEFAULT_SOURCES), help='Comma-separated music sources (musicdl client names).', type=str, show_default=True)
@click.option('-d', '--download-dir', '--download_dir', default=None, help='Directory where audio files are saved.', type=str)
@click.option('-q', '--quality', default=QualityPolicy.LOSSLESS, type=click.Choice([QualityPolicy.LOSSLESS, QualityPolicy.HIGH, QualityPolicy.STANDARD]), help='Best-quality policy.', show_default=True)
@click.option('--no-best', '--no_best', 'no_best', is_flag=True, default=False, help='Disable best-quality filtering (queue keeps every search hit).')
@click.option('--save-queue', '--save_queue', default=None, help='Save the batch queue to a JSON file and exit without downloading.', type=str)
@click.option('--load-queue', '--load_queue', default=None, help='Load a queue JSON file and download it.', type=str)
def brandcmd(keyword: str, playlist_url: str, music_sources: str, download_dir: str, quality: str, no_best: bool, save_queue: str, load_queue: str):
    # banner & compliance notice
    click.echo(BANNER)
    # load queue file
    if load_queue:
        from .session import HarvestQueue
        queue = HarvestQueue.loadfromjson(load_queue)
        client = HarvestClient(music_sources=[ms.strip() for ms in music_sources.replace(' ', '').split(',') if ms.strip()], download_dir=download_dir, policy=quality, best_only=not no_best)
        click.echo('Loaded %d queued songs from %s; start downloading...' % (len(queue), load_queue))
        client.downloadqueue(song_infos=queue.popall())
        return
    # instance client
    music_sources = [ms.strip() for ms in music_sources.replace(' ', '').split(',') if ms.strip()]
    client = HarvestClient(music_sources=music_sources, download_dir=download_dir, policy=quality, best_only=not no_best)
    # playlist mode
    if playlist_url:
        added = client.collectplaylist(playlist_url)
        click.echo('Collected %d tracks from playlist into queue.' % (added))
    # keyword mode
    elif keyword:
        search_results = client.search(keyword)
        client.collect(search_results=search_results)
        click.echo('Collected best-quality matches into queue (%d songs in total).' % (len(client.queue)))
    # interactive mode: loop search -> batch add / remove -> download
    else:
        while True:
            kw = click.prompt('\n[SoundHarvest] keyword (or "q" to quit)', default='', show_default=False).strip()
            if kw.lower() in ('q', 'quit', 'exit'): break
            search_results = client.search(kw)
            client.collect(search_results=search_results)
            click.echo('Queue now holds %d songs. Next keyword, or "q" to download-and-exit? (input "dl" to download now)' % (len(client.queue)))
            nxt = click.prompt('', default='', show_default=False).strip()
            if nxt.lower() in ('q', 'quit', 'exit'): break
            if nxt.lower() == 'dl': break
        # show queue summary
        summary = client.queuesummary()
        if summary:
            click.echo('\nBatch queue (%d songs):' % (len(summary)))
            for item in summary:
                click.echo('  [%2d] %-10s %-30s %-15s %6s  score=%s' % (item['idx'], item['source'], str(item['song_name'])[:30], str(item['singers'])[:15], item['ext'], item['quality_score']))
        else:
            click.echo('Queue is empty; nothing to download.')
            return
    # save queue only
    if save_queue:
        client.queue.savetojson(save_queue)
        click.echo('Queue saved to %s (download skipped).' % (save_queue))
        return
    # download everything queued
    downloaded = client.downloadqueue()
    click.echo('SoundHarvest finished: %d audio file(s) downloaded to %s.' % (len(downloaded), client.download_dir or 'per-source default dirs'))


'''main'''
if __name__ == '__main__':
    brandcmd()
