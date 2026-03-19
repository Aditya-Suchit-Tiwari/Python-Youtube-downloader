#!/usr/bin/env python3
"""
yt_downloader_m4a_fixed.py

Usage:
    python yt_downloader_m4a_fixed.py <YouTube URL> [--list] [--cookies path_to_cookies.txt]

Notes:
- Use `--list` to just list formats (no download).
- If you have trouble with 403, export cookies from your browser (or use yt-dlp's --cookies-from-browser) and pass the cookies file with --cookies.
"""

import sys
import argparse
import traceback
import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

def make_base_opts(cookiefile=None):
    # Browser-like headers (helps with some 403s)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        # 'Referer' or 'Origin' can sometimes help; uncomment if necessary:
        # 'Referer': 'https://www.youtube.com/',
    }

    opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio',
        'outtmpl': '%(title)s_%(id)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'quiet': False,
        'no_warnings': False,
        'http_headers': headers,
        # try to bypass geo-restrictions if present
        'geo_bypass': True,
        # allow formats that might otherwise be considered unplayable
        'allow_unplayable_formats': True,
        # conversion to m4a if source is not m4a
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
                'preferredquality': '192',
            }
        ],
        # useful for debugging:
        # 'logger': MyLogger()  # put a logger here if desired
        # 'verbose': True
    }

    if cookiefile:
        opts['cookiefile'] = cookiefile

    return opts

def print_formats(info):
    fmts = info.get('formats', [])
    if not fmts:
        print("No formats found in info.")
        return
    print("\nAvailable formats (format_id | ext | abr | vcodec | has_url):")
    for f in fmts:
        fmt_id = f.get('format_id')
        ext = f.get('ext')
        abr = f.get('abr') or f.get('tbr') or ''
        vcodec = f.get('vcodec')
        has_url = bool(f.get('url'))
        print(f"{fmt_id:12} | {ext:4} | {abr:8} | {vcodec:10} | {'yes' if has_url else 'no'}")
    print()

def choose_fallback_format(info):
    fmts = info.get('formats', [])
    # Prefer opus (webm), then aac/m4a, then best audio
    opus = [f for f in fmts if f.get('ext') == 'webm' and f.get('acodec') and 'opus' in f.get('acodec', '') and f.get('url')]
    if opus:
        return sorted(opus, key=lambda x: (x.get('abr') or 0), reverse=True)[0]['format_id']
    aac = [f for f in fmts if f.get('ext') in ('m4a', 'mp4') and f.get('acodec') and ('aac' in f.get('acodec', '') or 'mp4a' in f.get('acodec', '')) and f.get('url')]
    if aac:
        return sorted(aac, key=lambda x: (x.get('abr') or 0), reverse=True)[0]['format_id']
    best_audio = [f for f in fmts if f.get('vcodec') == 'none' and f.get('url')]
    if best_audio:
        return sorted(best_audio, key=lambda x: (x.get('abr') or 0), reverse=True)[0]['format_id']
    return None

def download_audio_m4a(video_url, list_only=False, cookiefile=None):
    # First attempt with base options (headers + geo_bypass + cookiefile if given)
    opts = make_base_opts(cookiefile=cookiefile)

    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            if list_only:
                info = ydl.extract_info(video_url, download=False)
                print_formats(info)
                return

            print("Attempting download with browser-like headers and geo-bypass (prefer m4a)...")
            ydl.download([video_url])
            print("Download completed.")
            return

        except (DownloadError, ExtractorError) as e:
            print("Primary download attempt failed with error:")
            print(str(e))
            # Try a robust fallback flow
            try:
                print("\nInspecting formats for fallback...")
                info = ydl.extract_info(video_url, download=False)
                print_formats(info)
                fallback_fmt = choose_fallback_format(info)
                if not fallback_fmt:
                    print("No usable audio format with direct URL found. This could be due to YouTube serving HLS/SABR manifests requiring a newer extractor or authenticated access.")
                    print("Try:\n - Updating yt-dlp (py -3 -m pip install -U yt-dlp)\n - Passing a cookie file (--cookies-from-browser or --cookies)\n - Running yt-dlp with -v to capture debug info")
                    return

                print(f"Falling back to explicit format: {fallback_fmt} and converting to m4a.")
                fallback_opts = make_base_opts(cookiefile=cookiefile)
                fallback_opts['format'] = fallback_fmt
                with yt_dlp.YoutubeDL(fallback_opts) as ydl2:
                    ydl2.download([video_url])
                    print("Fallback download + conversion completed.")
                    return

            except Exception:
                print("Failed while trying fallback. Traceback:")
                traceback.print_exc()
                print("\nSuggestions:\n- Update yt-dlp\n- Use browser cookies (see README below)\n- Run with verbose logs: yt-dlp -v <url>")
                return
        except Exception:
            print("Unexpected error during download. Traceback:")
            traceback.print_exc()
            return

def parse_args():
    p = argparse.ArgumentParser(description="Download audio and convert to m4a with a few fallbacks.")
    p.add_argument('url', help='YouTube URL')
    p.add_argument('--list', action='store_true', help='List formats only (no download)')
    p.add_argument('--cookies', help='Path to cookies.txt (optional)', default=None)
    return p.parse_args()

if __name__ == '__main__':
    args = parse_args()
    download_audio_m4a(args.url, list_only=args.list, cookiefile=args.cookies)
