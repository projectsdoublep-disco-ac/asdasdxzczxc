import requests
import asyncio
import os
import io
import re
import time
import json
import math
import random
import struct
import logging
import tempfile
import threading
from datetime import datetime
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from mutagen.mp4 import MP4, MP4Cover

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger(__name__)

# ====================== ACCESS CONTROL ======================

ALLOWED_USER_ID = 7862911835

async def check_access(update: Update) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    if chat.type in ('group', 'supergroup', 'channel'):
        await update.message.reply_text("❌ This bot doesn't work in groups. DM it directly.")
        return False
    if user.id != ALLOWED_USER_ID:
        await update.message.reply_text(
            "⛔ You don't have access to this bot.\n"
            "Ask for access: @tumbandolos"
        )
        return False
    return True

# ====================== CONFIG ======================

TELEGRAM_TOKEN = "8807771466:AAFQbXlaSQb2Odeh-bJVoXg0IXnAmYHhYww"

AUTH_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiIsImtpZCI6IldlYlBsYXlLaWQifQ.eyJpc3MiOiJBTVBXZWJQbGF5IiwiaWF0IjoxNzgzNDA1OTU1LCJleHAiOjE3ODY0Mjk5NTUsInJvb3RfaHR0cHNfb3JpZ2luIjpbImFwcGxlLmNvbSJdfQ.X5XtoYobneo0Z8yi9cXHMA7JckjSJUUTtAnNUTuPZAG30TxgMBzgHJuGsgBM4uLeWdoFsuTztKBB212izvwJiw"
MEDIA_USER_TOKEN = "0.AvAZj9y+qod8t6Z18QxQr7RKasExuLYp4clxsZ/ZQl2aGtHqYuWssX9PCmPf7LSzTOBGc5xEmefdUcxGTTYHWwPGQZ4980u1Gn5I9QgwLFDXJnk5RSGvWRTjcIj/LB3giFRgDk8APfODB8J00xnX3qT/BHiGhXerTQDoU2R0IMiGxNEV4H17Bcq329sxAm0c7DYtO1r7gNeGr2X6pYhcYk5RViBrl4qUXIidDIlrI9J6NjuO9w=="
TREBEL_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIxOTc5NzA4MDEiLCJkZXZpY2VJZCI6IjE3NTcyMDExOSIsInRyYW5zYWN0aW9uSWQiOjAsImlhdCI6MTc3ODA0MzA0Mn0.XXmQbB1daTY9A_FHlYbAfdqlr5bN8RKWP2hkBUyv33I"

XKAL_CHANNEL = "t.me/canalseventeen"
XKAL_HANDLE  = "@canalseventeen"

PROVIDERS = [
    'Warner', 'Orchard', 'SonyMusic', 'UMG', 'INgrooves', 'Fuga', 'Vydia', 'Empire',
    'LabelCamp', 'AudioSalad', 'ONErpm', 'Symphonic', 'Colonize', 'DistroKid',
    'TuneCore', 'CDBaby', 'Amuse', 'Believe', 'AWAL', 'Stem', 'Repost',
    'Ditto', 'RouteNote', 'Spinnup', 'Horus', 'Kontor', 'Zebralution',
    'Idol', 'The Orchard', 'Altafonte', 'Finetunes', 'Phonofile'
]

AM_HEADERS = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'authorization': f'Bearer {AUTH_TOKEN}',
    'media-user-token': MEDIA_USER_TOKEN,
    'origin': 'https://music.apple.com',
    'referer': 'https://music.apple.com/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# ====================== FAKE AUDIO MODE ======================
smd_mode = {}

# ====================== XKAL MODE ======================
# Per-chat toggle: chat_id -> True/False
xkal_mode = {}

def generate_fake_m4a(duration_secs=None) -> bytes:
    if duration_secs is None:
        duration_secs = random.randint(120, 180)

    sample_rate = 44100
    num_samples = duration_secs * sample_rate

    root = random.choice([60, 80, 100, 110, 120, 130, 160, 180])

    harmonics = [
        (root,        0.35),
        (root * 2,    0.20),
        (root * 3,    0.10),
        (root * 0.5,  0.25),
        (root * 4,    0.05),
    ]

    lfo_rate   = random.uniform(0.3, 0.8)
    lfo_depth  = random.uniform(0.004, 0.01)

    fade_len = min(sample_rate * 3, num_samples // 4)

    frames = bytearray()
    for n in range(num_samples):
        t = n / sample_rate
        lfo = math.sin(2 * math.pi * lfo_rate * t)

        sample = 0.0
        for (freq, amp) in harmonics:
            f_mod = freq * (1.0 + lfo_depth * lfo)
            sample += amp * math.sin(2 * math.pi * f_mod * t)

        sample += random.uniform(-0.015, 0.015)

        if n < fade_len:
            sample *= n / fade_len
        elif n > num_samples - fade_len:
            sample *= (num_samples - n) / fade_len

        clamped = max(-1.0, min(1.0, sample))
        pcm = int(clamped * 32767)
        frames += struct.pack('<h', pcm)

    data_size   = len(frames)
    header_size = 44
    total_size  = header_size + data_size - 8

    wav  = b'RIFF'
    wav += struct.pack('<I', total_size)
    wav += b'WAVE'
    wav += b'fmt '
    wav += struct.pack('<I', 16)
    wav += struct.pack('<H', 1)
    wav += struct.pack('<H', 1)
    wav += struct.pack('<I', sample_rate)
    wav += struct.pack('<I', sample_rate * 2)
    wav += struct.pack('<H', 2)
    wav += struct.pack('<H', 16)
    wav += b'data'
    wav += struct.pack('<I', data_size)
    wav += bytes(frames)

    return wav, duration_secs

# ====================== APPLE MUSIC ======================

def parse_apple_music_link(url):
    url = url.strip()
    single = re.search(r'[?&]i=(\d+)', url)
    if single:
        return 'song', single.group(1), _storefront(url)
    song_path = re.search(r'/song/(?:[^/]+/)?(\d+)', url)
    if song_path:
        return 'song', song_path.group(1), _storefront(url)
    album = re.search(r'/album/[^/]+/(\d+)', url)
    if album:
        return 'album', album.group(1), _storefront(url)
    playlist = re.search(r'/playlist/[^/]+/(pl\.[a-zA-Z0-9]+)', url)
    if playlist:
        return 'playlist', playlist.group(1), _storefront(url)
    return None, None, None

def _storefront(url):
    m = re.search(r'music\.apple\.com/([a-z]{2})/', url)
    return m.group(1) if m else 'us'

def get_album_tracks(album_id, storefront='us'):
    url = (
        f"https://amp-api.music.apple.com/v1/catalog/{storefront}/albums/{album_id}"
        f"?include=tracks"
    )
    try:
        r = requests.get(url, headers=AM_HEADERS, timeout=15)
        if r.status_code != 200:
            log.error(f"Album fetch failed: {r.status_code}")
            return [], {}
        data = r.json().get('data', [])
        if not data:
            return [], {}
        album_attrs = data[0].get('attributes', {})
        album_info = {
            'name': album_attrs.get('name', ''),
            'artist': album_attrs.get('artistName', ''),
            'artwork': album_attrs.get('artwork', {}),
            'total_tracks': album_attrs.get('trackCount', 0),
            'release_date': (album_attrs.get('releaseDate', '') or '')[:4],
        }
        tracks_data = data[0].get('relationships', {}).get('tracks', {}).get('data', [])
        if tracks_data:
            song_ids = [t['id'] for t in tracks_data]
            enriched = get_songs_by_ids(song_ids, storefront)
            enriched_map = {s['id']: s for s in enriched}
            for t in tracks_data:
                if t['id'] in enriched_map:
                    t['attributes'] = enriched_map[t['id']].get('attributes', t.get('attributes', {}))
        return tracks_data, album_info
    except Exception as e:
        log.error(f"Exception in get_album_tracks: {e}")
        return [], {}

def get_songs_by_ids(song_ids, storefront='us'):
    all_songs = []
    for chunk in [song_ids[i:i+50] for i in range(0, len(song_ids), 50)]:
        ids_str = ','.join(chunk)
        url = (
            f"https://amp-api.music.apple.com/v1/catalog/{storefront}/songs"
            f"?ids={ids_str}"
            f"&fields[songs]=name,artistName,albumName,trackNumber,discNumber,"
            f"releaseDate,genreNames,durationInMillis,isrc,artwork,composerName"
            f"&include=albums"
        )
        try:
            r = requests.get(url, headers=AM_HEADERS, timeout=15)
            if r.status_code == 200:
                all_songs.extend(r.json().get('data', []))
            else:
                log.error(f"Songs fetch failed: {r.status_code}")
        except Exception as e:
            log.error(f"Exception fetching songs: {e}")
        time.sleep(0.3)
    return all_songs

def get_playlist_tracks(playlist_id, storefront='us'):
    url = (
        f"https://amp-api.music.apple.com/v1/catalog/{storefront}/playlists/{playlist_id}"
        f"?include=tracks&fields[songs]=name,artistName,albumName,trackNumber,"
        f"releaseDate,genreNames,durationInMillis,isrc,artwork,composerName"
    )
    try:
        r = requests.get(url, headers=AM_HEADERS, timeout=15)
        if r.status_code != 200:
            return [], {}
        data = r.json().get('data', [])
        if not data:
            return [], {}
        pl_attrs = data[0].get('attributes', {})
        pl_info = {
            'name': pl_attrs.get('name', 'Playlist'),
            'artist': pl_attrs.get('curatorName', ''),
            'artwork': pl_attrs.get('artwork', {}),
            'total_tracks': 0,
            'release_date': pl_attrs.get('lastModifiedDate', '')[:4] or str(datetime.now().year),
        }
        tracks_data = data[0].get('relationships', {}).get('tracks', {}).get('data', [])
        pl_info['total_tracks'] = len(tracks_data)
        if tracks_data:
            song_ids = [t['id'] for t in tracks_data]
            enriched = get_songs_by_ids(song_ids, storefront)
            enriched_map = {s['id']: s for s in enriched}
            for t in tracks_data:
                if t['id'] in enriched_map:
                    t['attributes'] = enriched_map[t['id']].get('attributes', t.get('attributes', {}))
        return tracks_data, pl_info
    except Exception as e:
        log.error(f"Exception in get_playlist_tracks: {e}")
        return [], {}

def download_artwork(artwork_dict, size=1400):
    url_template = artwork_dict.get('url', '')
    if not url_template:
        return None
    url = url_template.replace('{w}', str(size)).replace('{h}', str(size))
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            return r.content
    except Exception as e:
        log.error(f"Artwork download error: {e}")
    return None

# ====================== TREBEL ======================

FULL_THRESHOLD = 2 * 1024 * 1024

def download_track(isrc):
    for provider in PROVIDERS:
        url = f"https://mds.projectcarmen.com/stream/download?provider={provider}&isrc={isrc}"
        headers = {
            "Authorization": f"Bearer {TREBEL_TOKEN}",
            "User-Agent": "Trebel/1.0.0 (Android)"
        }
        try:
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code in (200, 206) and len(r.content) > 1000:
                label = "full" if len(r.content) >= FULL_THRESHOLD else "download"
                log.info(f"  [{provider}] download: {len(r.content):,} bytes ({label})")
                return r.content, provider, label
        except Exception:
            continue
    for provider in PROVIDERS:
        url = f"https://mds.projectcarmen.com/stream/preview?provider={provider}&isrc={isrc}"
        headers = {
            "Authorization": f"Bearer {TREBEL_TOKEN}",
            "User-Agent": "Trebel/1.0.0 (Android)"
        }
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code in (200, 206) and len(r.content) > 1000:
                log.info(f"  [{provider}] preview: {len(r.content):,} bytes")
                return r.content, provider, "preview"
        except Exception:
            continue
    return None, None, None

# ====================== TAGGING ======================

def detect_format(data):
    if data[:4] == b'fLaC':
        return 'flac'
    if data[:3] == b'ID3' or data[:2] == b'\xff\xfb':
        return 'mp3'
    if b'ftyp' in data[:12]:
        return 'm4a'
    return 'm4a'

def tag_file(filepath, track_info, cover_data=None, xkal=False):
    try:
        audio = MP4(filepath)
        audio['\xa9nam'] = [track_info['name']]

        artist = track_info['artist']
        if xkal:
            artist = f"{artist} ~ {XKAL_HANDLE}"
        audio['\xa9ART'] = [artist]

        audio['\xa9alb'] = [track_info['album']]
        audio['\xa9day'] = [str(track_info.get('release_date', ''))]
        audio['\xa9gen'] = [track_info.get('genre', '')]
        audio['aART'] = [track_info.get('album_artist', track_info['artist'])]
        audio['trkn'] = [(track_info.get('track_number', 1), track_info.get('total_tracks', 0))]
        audio['disk'] = [(track_info.get('disc_number', 1), 0)]

        isrc = track_info.get('isrc', '')
        if isrc:
            audio['----:com.apple.iTunes:ISRC'] = [isrc.encode('utf-8')]

        if xkal:
            # Comment
            audio['\xa9cmt'] = [XKAL_CHANNEL]
            # Composer (if available)
            composer = track_info.get('composer', '')
            if composer:
                audio['\xa9wrt'] = [composer]
            # Copyright
            cprt = track_info.get('copyright', '')
            if cprt:
                audio['cprt'] = [cprt]
            # BPM
            bpm = track_info.get('bpm', 0)
            if bpm:
                audio['tmpo'] = [int(bpm)]
            # Lyrics
            lyrics = track_info.get('lyrics', '')
            if lyrics:
                audio['\xa9lyr'] = [lyrics]

        if cover_data:
            fmt = MP4Cover.FORMAT_JPEG
            if cover_data[:8] == b'\x89PNG\r\n\x1a\n':
                fmt = MP4Cover.FORMAT_PNG
            audio['covr'] = [MP4Cover(cover_data, imageformat=fmt)]

        audio.save()
        return True
    except Exception as e:
        log.warning(f"Tagging error: {e}")
        return False

def tag_wav_file(filepath, track_info, cover_data=None):
    try:
        from mutagen.wave import WAVE
        from mutagen.id3 import TIT2, TPE1, TALB, TRCK, TDRC, TCON, TSRC, APIC
        try:
            audio = WAVE(filepath)
        except Exception:
            return False
        audio.tags.add(TIT2(encoding=3, text=track_info['name']))
        audio.tags.add(TPE1(encoding=3, text=track_info['artist']))
        audio.tags.add(TALB(encoding=3, text=track_info['album']))
        trk = str(track_info.get('track_number', 1))
        tot = str(track_info.get('total_tracks', 0))
        audio.tags.add(TRCK(encoding=3, text=f"{trk}/{tot}"))
        audio.tags.add(TDRC(encoding=3, text=str(track_info.get('release_date', ''))))
        audio.tags.add(TCON(encoding=3, text=track_info.get('genre', '')))
        isrc = track_info.get('isrc', '')
        if isrc:
            audio.tags.add(TSRC(encoding=3, text=isrc))
        if cover_data:
            mime = 'image/png' if cover_data[:8] == b'\x89PNG\r\n\x1a\n' else 'image/jpeg'
            audio.tags.add(APIC(encoding=3, mime=mime, type=3, desc='Cover', data=cover_data))
        audio.save()
        return True
    except Exception as e:
        log.warning(f"WAV tagging error: {e}")
        return False

def make_thumbnail(cover_data: bytes) -> bytes:
    if not cover_data:
        return None
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(cover_data)).convert("RGB")
        img.thumbnail((320, 320))
        quality = 85
        while True:
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality)
            if buf.tell() <= 200_000 or quality <= 30:
                break
            quality -= 15
        return buf.getvalue()
    except ImportError:
        log.warning("Pillow not installed — no thumbnail.")
        return None
    except Exception as e:
        log.warning(f"Thumbnail build failed: {e}")
        return None

# ====================== JOB STATE ======================
active_jobs = {}

_fake_audio_cache = None

def _build_fake_cache():
    global _fake_audio_cache
    if _fake_audio_cache is not None:
        return
    log.info("Generating fake audio (one-time)...")
    _fake_audio_cache = generate_fake_m4a()
    log.info("Fake audio ready.")

# ====================== PIPELINE ======================

async def process_link(url, update: Update, context: ContextTypes.DEFAULT_TYPE, mode='normal'):
    """
    mode: 'normal' | 'smd' | 'xkal'
    """
    chat_id = update.effective_chat.id
    is_smd  = (mode == 'smd')
    is_xkal = (mode == 'xkal')

    cancel_event = asyncio.Event()
    skip_event   = asyncio.Event()
    active_jobs[chat_id] = {'cancel': cancel_event, 'skip': skip_event}

    async def msg(text):
        for attempt in range(3):
            try:
                await context.bot.send_message(chat_id=chat_id, text=text)
                return
            except Exception as e:
                if attempt == 2:
                    log.error(f'send_message failed: {e}')
                else:
                    await asyncio.sleep(2)

    try:
        link_type, link_id, storefront = parse_apple_music_link(url)
        if not link_type:
            await msg("Could not parse that Apple Music link.")
            return

        await msg(f"Fetching {link_type} from Apple Music...")

        if link_type == 'album':
            tracks, collection_info = get_album_tracks(link_id, storefront)
        elif link_type == 'playlist':
            tracks, collection_info = get_playlist_tracks(link_id, storefront)
        elif link_type == 'song':
            songs = get_songs_by_ids([link_id], storefront)
            tracks = songs
            collection_info = {}
            if songs:
                a = songs[0].get('attributes', {})
                collection_info = {
                    'name': a.get('albumName', ''),
                    'artist': a.get('artistName', ''),
                    'artwork': a.get('artwork', {}),
                    'total_tracks': 1,
                    'release_date': a.get('releaseDate', '')[:4],
                }
        else:
            await msg("Unsupported link type.")
            return

        if not tracks:
            await msg("No tracks found.")
            return

        total = len(tracks)
        await msg(f"Found {total} track(s). Downloading artwork...")

        cover_data = None
        artwork_dict = collection_info.get('artwork', {})
        if not artwork_dict and tracks:
            artwork_dict = tracks[0].get('attributes', {}).get('artwork', {})
        if artwork_dict:
            cover_data = download_artwork(artwork_dict)

        collection_name = collection_info.get('name', 'Unknown Album')
        mode_label = " [XKAL]" if is_xkal else (" [SMD]" if is_smd else "")
        await msg(
            f"Starting download{mode_label} of \"{collection_name}\" "
            f"({total} tracks)...\n\nUse /skip to skip current track, /cancel to stop."
        )

        success = 0
        fail    = 0
        thumb_bytes = make_thumbnail(cover_data) if cover_data else None

        for i, song in enumerate(tracks, 1):
            if cancel_event.is_set():
                await msg(f"❌ Cancelled after {success} sent, {fail} failed.")
                return

            skip_event.clear()

            attrs        = song.get('attributes', {})
            isrc         = attrs.get('isrc', '')
            name         = attrs.get('name', f'Track {i}')
            artist       = attrs.get('artistName', '')
            album        = attrs.get('albumName', collection_info.get('name', ''))
            track_number = attrs.get('trackNumber', i)
            disc_number  = attrs.get('discNumber', 1)
            total_tracks = collection_info.get('total_tracks', total)
            release_date = (attrs.get('releaseDate', collection_info.get('release_date', '')) or '')[:4]
            genre        = (attrs.get('genreNames') or [''])[0]
            composer     = attrs.get('composerName', '')
            copyright_   = attrs.get('copyright', '')
            bpm          = attrs.get('currentVersionReleaseDate', 0)  # placeholder; AM doesn't give BPM

            log.info(f"[{i}/{total}] {name} | ISRC: {isrc} | mode={mode}")

            track_info = {
                'name':         name,
                'artist':       artist,
                'album':        album,
                'album_artist': collection_info.get('artist', artist),
                'isrc':         isrc,
                'track_number': track_number,
                'disc_number':  disc_number,
                'total_tracks': total_tracks,
                'release_date': release_date,
                'genre':        genre,
                'composer':     composer,
                'copyright':    copyright_,
            }

            safe_name   = re.sub(r'[\\/*?:"<>|]', '', name)
            safe_artist = re.sub(r'[\\/*?:"<>|]', '', artist)

            # ---- SMD FAKE AUDIO BRANCH ----
            if is_smd:
                if _fake_audio_cache is None:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, _build_fake_cache)

                wav_data, dur_secs = _fake_audio_cache
                filename = f"{i:02d} - {safe_name}.wav"
                tmp_fd, tmppath = tempfile.mkstemp(suffix='.wav')
                os.close(tmp_fd)

                try:
                    with open(tmppath, 'wb') as f:
                        f.write(wav_data)
                except Exception as e:
                    log.error(f"Failed to write fake audio: {e}")
                    await msg(f"[{i}/{total}] {name} — Failed to write file")
                    fail += 1
                    continue

                tag_wav_file(tmppath, track_info, cover_data)

                sent = False
                for attempt in range(3):
                    if cancel_event.is_set() or skip_event.is_set():
                        break
                    try:
                        with open(tmppath, 'rb') as audio_f:
                            send_kwargs = dict(
                                chat_id=chat_id,
                                audio=audio_f,
                                filename=filename,
                                title=name,
                                performer=artist,
                                duration=dur_secs,
                                caption=f"{i}/{total} — {name} 🎵 Full",
                                read_timeout=120,
                                write_timeout=120,
                            )
                            if thumb_bytes:
                                send_kwargs['thumbnail'] = io.BytesIO(thumb_bytes)
                            await context.bot.send_audio(**send_kwargs)
                        sent = True
                        break
                    except Exception as e:
                        log.warning(f"send_audio fake attempt {attempt+1} failed: {e}")
                        if attempt == 0 and thumb_bytes:
                            thumb_bytes = None
                        elif attempt < 2:
                            await asyncio.sleep(3)

                if os.path.exists(tmppath):
                    os.remove(tmppath)

                if cancel_event.is_set():
                    await msg(f"❌ Cancelled after {success} sent, {fail} failed.")
                    return
                if skip_event.is_set():
                    await msg(f"⏭ Skipped: {name}")
                    fail += 1
                    continue

                if sent:
                    success += 1
                else:
                    await msg(f"[{i}/{total}] {name} — failed to send after 3 attempts")
                    fail += 1

                await asyncio.sleep(0.3)
                continue

            # ---- REAL DOWNLOAD BRANCH (normal + xkal) ----
            if not isrc:
                await msg(f"[{i}/{total}] {name} — No ISRC, skipping")
                fail += 1
                continue

            content  = None
            endpoint = None
            try:
                loop = asyncio.get_event_loop()
                download_future = loop.run_in_executor(None, download_track, isrc)
                while not download_future.done():
                    if cancel_event.is_set() or skip_event.is_set():
                        download_future.cancel()
                        break
                    await asyncio.sleep(0.2)
                if not download_future.cancelled() and not cancel_event.is_set() and not skip_event.is_set():
                    result = await download_future
                    content, provider, endpoint = result if result else (None, None, None)
            except Exception as e:
                log.error(f"download_track exception: {e}")
                content = None

            if cancel_event.is_set():
                await msg(f"❌ Cancelled after {success} sent, {fail} failed.")
                return
            if skip_event.is_set():
                await msg(f"⏭ Skipped: {name}")
                fail += 1
                continue

            if not content:
                await msg(f"[{i}/{total}] {name} — No preview available")
                fail += 1
                continue

            fmt = detect_format(content)

            # XKAL: filename formatted as "Song Name - Artist (FULL).ext"
            if is_xkal:
                filename = f"{safe_name} - {safe_artist} (FULL).{fmt}"
            else:
                filename = f"{i:02d} - {safe_name}.{fmt}"

            tmp_fd, tmppath = tempfile.mkstemp(suffix=f'.{fmt}')
            os.close(tmp_fd)

            try:
                with open(tmppath, 'wb') as f:
                    f.write(content)
            except Exception as e:
                log.error(f"Failed to write temp file: {e}")
                await msg(f"[{i}/{total}] {name} — Failed to save file")
                fail += 1
                continue

            try:
                tag_file(tmppath, track_info, cover_data, xkal=is_xkal)
            except Exception as e:
                log.warning(f"Tagging failed for {name}: {e}")

            # Caption label
            if is_xkal:
                cap_label = f"🎵 Full — {XKAL_CHANNEL}"
            else:
                cap_label = '🎵 Full' if endpoint == 'full' else '🔊 Preview'

            # Performer shown in Telegram (artist + credit for xkal)
            telegram_performer = f"{artist} ~ {XKAL_HANDLE}" if is_xkal else artist

            sent = False
            for attempt in range(3):
                if cancel_event.is_set() or skip_event.is_set():
                    break
                try:
                    with open(tmppath, 'rb') as audio_f:
                        send_kwargs = dict(
                            chat_id=chat_id,
                            audio=audio_f,
                            filename=filename,
                            title=name,
                            performer=telegram_performer,
                            caption=f"{i}/{total} — {name} {cap_label}",
                            read_timeout=120,
                            write_timeout=120,
                        )
                        if thumb_bytes:
                            send_kwargs['thumbnail'] = io.BytesIO(thumb_bytes)
                        await context.bot.send_audio(**send_kwargs)
                    sent = True
                    break
                except Exception as e:
                    log.warning(f"send_audio attempt {attempt+1} failed: {e}")
                    if attempt == 0 and thumb_bytes:
                        thumb_bytes = None
                    elif attempt < 2:
                        await asyncio.sleep(3)

            if os.path.exists(tmppath):
                os.remove(tmppath)

            if cancel_event.is_set():
                await msg(f"❌ Cancelled after {success} sent, {fail} failed.")
                return
            if skip_event.is_set():
                await msg(f"⏭ Skipped: {name}")
                fail += 1
                continue

            if sent:
                success += 1
            else:
                await msg(f"[{i}/{total}] {name} — failed to send after 3 attempts")
                fail += 1

            await asyncio.sleep(0.5)

        await msg(f"✅ Done! {success}/{total} sent, {fail} failed.")

    finally:
        active_jobs.pop(chat_id, None)

# ====================== COMMANDS ======================

async def cmd_cnmds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        return
    await update.message.reply_text(
        "Music bot ready.\n\n"
        "Commands:\n"
        "/amisrc <link> — Download tracks from Apple Music link\n"
        "/xkal <link>  — Download with xkalibr branding & full tags\n"
        "/meta <link>  — Show metadata for all tracks\n"
        "/smd          — Toggle SMD mode\n"
        "/skip         — Skip current track\n"
        "/cancel       — Cancel current job\n\n"
        "Supports album, playlist, and single song links."
    )

async def cmd_smd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        return
    chat_id = update.effective_chat.id
    current = smd_mode.get(chat_id, False)
    smd_mode[chat_id] = not current
    if smd_mode[chat_id]:
        await update.message.reply_text(
            "SMD mode ON — Full\n"
            "Next /amisrc will send full tracks for each song.\n"
            "Use /smd again to turn off."
        )
    else:
        await update.message.reply_text("✅ SMD mode OFF.")

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        return
    chat_id = update.effective_chat.id
    job = active_jobs.get(chat_id)
    if job:
        job['cancel'].set()
        await update.message.reply_text("❌ Cancelling...")
    else:
        await update.message.reply_text("Nothing running.")

async def cmd_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        return
    chat_id = update.effective_chat.id
    job = active_jobs.get(chat_id)
    if job:
        job['skip'].set()
        await update.message.reply_text("⏭ Skipping...")
    else:
        await update.message.reply_text("Nothing running.")

async def cmd_amisrc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /amisrc <apple_music_link>")
        return
    url = args[0]
    if 'music.apple.com' not in url:
        await update.message.reply_text("Please send a valid Apple Music link.")
        return
    chat_id = update.effective_chat.id
    if chat_id in active_jobs:
        await update.message.reply_text("⚠️ A download is already running. Use /cancel to stop it first.")
        return
    # Respect SMD toggle
    mode = 'smd' if smd_mode.get(chat_id, False) else 'normal'
    asyncio.create_task(process_link(url, update, context, mode=mode))

async def cmd_xkal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /xkal <apple_music_link>")
        return
    url = args[0]
    if 'music.apple.com' not in url:
        await update.message.reply_text("Please send a valid Apple Music link.")
        return
    chat_id = update.effective_chat.id
    if chat_id in active_jobs:
        await update.message.reply_text("⚠️ A download is already running. Use /cancel to stop it first.")
        return
    await update.message.reply_text(
        "🎵 XKAL mode — downloading with full tags & xkalibr branding.\n"
        "Files will be named: Song - Artist (FULL).m4a\n"
        "Artist tag: Artist ~ @canalxkalibr\n"
        "Comment tag: t.me/canalxkalibvr"
    )
    asyncio.create_task(process_link(url, update, context, mode='xkal'))

async def cmd_meta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /meta <apple_music_link>")
        return
    url = args[0]
    if 'music.apple.com' not in url:
        await update.message.reply_text("Please send a valid Apple Music link.")
        return

    chat_id = update.effective_chat.id

    async def send_photo_caption(photo_bytes, caption):
        for attempt in range(3):
            try:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=io.BytesIO(photo_bytes),
                    caption=caption,
                    parse_mode='HTML',
                    read_timeout=60,
                    write_timeout=60,
                )
                return
            except Exception as e:
                if attempt == 2:
                    log.error(f"send_photo failed: {e}")
                else:
                    await asyncio.sleep(2)

    async def send_msg(text):
        for attempt in range(3):
            try:
                await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML', disable_web_page_preview=True)
                return
            except Exception as e:
                if attempt == 2:
                    log.error(f"send_message failed: {e}")
                else:
                    await asyncio.sleep(2)

    link_type, link_id, storefront = parse_apple_music_link(url)
    if not link_type:
        await send_msg("Could not parse that Apple Music link.")
        return

    await send_msg("🔍 Fetching metadata...")

    if link_type == 'album':
        tracks, collection_info = get_album_tracks(link_id, storefront)
    elif link_type == 'playlist':
        tracks, collection_info = get_playlist_tracks(link_id, storefront)
    elif link_type == 'song':
        songs = get_songs_by_ids([link_id], storefront)
        tracks = songs
        collection_info = {}
        if songs:
            a = songs[0].get('attributes', {})
            collection_info = {
                'name': a.get('albumName', ''),
                'artist': a.get('artistName', ''),
                'artwork': a.get('artwork', {}),
                'total_tracks': 1,
                'release_date': (a.get('releaseDate', '') or '')[:4],
            }
    else:
        await send_msg("Unsupported link type.")
        return

    if not tracks:
        await send_msg("No tracks found.")
        return

    total = len(tracks)
    collection_name   = collection_info.get('name', 'Unknown')
    collection_artist = collection_info.get('artist', '')

    artwork_dict = collection_info.get('artwork', {})
    if not artwork_dict and tracks:
        artwork_dict = tracks[0].get('attributes', {}).get('artwork', {})

    hq_cover_url = ''
    cover_bytes  = None
    if artwork_dict:
        hq_cover_url = (artwork_dict.get('url', '')
                        .replace('{w}', '3000')
                        .replace('{h}', '3000'))
        cover_bytes = download_artwork(artwork_dict, size=1400)

    for i, song in enumerate(tracks, 1):
        attrs        = song.get('attributes', {})
        name         = attrs.get('name', f'Track {i}')
        artist       = attrs.get('artistName', collection_artist)
        album        = attrs.get('albumName', collection_name)
        isrc         = attrs.get('isrc', 'N/A')
        track_number = attrs.get('trackNumber', i)
        disc_number  = attrs.get('discNumber', 1)
        total_tracks = attrs.get('trackCount') or collection_info.get('total_tracks', total)
        release_date = (attrs.get('releaseDate', '') or 'N/A')
        genre        = (attrs.get('genreNames') or ['N/A'])[0]
        duration_ms  = attrs.get('durationInMillis', 0)
        explicit     = attrs.get('contentRating', '') == 'explicit'
        song_id      = song.get('id', 'N/A')
        album_id     = collection_info.get('id', link_id if link_type == 'album' else 'N/A')
        album_artist = collection_artist or artist
        composer     = attrs.get('composerName', 'N/A')

        if duration_ms:
            mins = duration_ms // 60000
            secs = (duration_ms % 60000) // 1000
            duration_str = f"{mins}:{secs:02d}"
        else:
            duration_str = 'N/A'

        am_link      = f"https://music.apple.com/{storefront}/song/{song_id}"
        explicit_tag = ' 🅴' if explicit else ''

        caption = (
            f"🎤 <b>Artist(s):</b> <code>{artist}</code>\n\n"
            f"🎵 <b>Title:</b> <code>{name}{explicit_tag}</code>\n"
            f"💿 <b>Album:</b> <code>{album}</code>\n"
            f"👤 <b>Album Artist:</b> <code>{album_artist}</code>\n\n"
            f"⌛️ <b>Duration:</b> <code>{duration_str}</code>\n"
            f"🔢 <b>Track:</b> <code>{track_number}/{total_tracks}  •  Disc {disc_number}</code>\n\n"
            f"🎼 <b>Composer:</b> <code>{composer}</code>\n\n"
            f"🆔 <b>SongID:</b> <code>{song_id}</code>\n"
            f"🆔 <b>AlbumID:</b> <code>{album_id}</code>\n\n"
            f"🔍 <b>ISRC:</b> <code>{isrc}</code>\n\n"
            f"🏷 <b>Genre:</b> <code>{genre}</code>\n"
            f"📅 <b>ReleaseDate:</b> <code>{release_date}</code>\n\n"
            f"🖼 <a href=\"{hq_cover_url}\">‎HQ Cover</a>\n"
            f"🔗 <b>Link:</b> <a href=\"{am_link}\">{name} — Apple Music</a>"
        )

        if cover_bytes:
            await send_photo_caption(cover_bytes, caption)
        else:
            await send_msg(caption)

        await asyncio.sleep(0.5)

    await send_msg(f"✅ Done — <b>{total}</b> track(s) from <b>{collection_name}</b>")

# ====================== FLASK KEEP-ALIVE (for Render free tier) ======================

flask_app = Flask(__name__)

@flask_app.route('/health')
def health():
    return 'ok', 200

@flask_app.route('/')
def index():
    return 'Telegram bot is running', 200

# ====================== MAIN ======================

if __name__ == "__main__":
    log.info("Bot started.")
    
    # Start Flask server on a background thread
    flask_thread = threading.Thread(
        target=lambda: flask_app.run(host='0.0.0.0', port=10000, debug=False),
        daemon=True
    )
    flask_thread.start()
    log.info("Flask keep-alive server started on port 10000")
    
    # Start Telegram bot
    from telegram.request import HTTPXRequest
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .request(HTTPXRequest(read_timeout=120, write_timeout=120, connect_timeout=30))
        .build()
    )
    app.add_handler(CommandHandler("cnmds",  cmd_cnmds))
    app.add_handler(CommandHandler("amisrc", cmd_amisrc))
    app.add_handler(CommandHandler("xkal",   cmd_xkal))
    app.add_handler(CommandHandler("meta",   cmd_meta))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CommandHandler("skip",   cmd_skip))
    app.add_handler(CommandHandler("smd",    cmd_smd))
    app.run_polling()