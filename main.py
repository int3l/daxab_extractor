import gzip
import re
import sys
import urllib.request
from argparse import ArgumentParser
from base64 import b64decode
from json import loads


HEADERS={
    'Accept': 'text/html',
    'Accept-Encoding': 'gzip',
    'User-Agent': 'Mozilla/5.0',
}

PLAYER_PATTERN = re.compile(
    r'"video">.+?<iframe.+?src="(?P<url>.+?)"', re.DOTALL,
)

VIDEO_INFO_PATTERN = re.compile(
    r'globParams\s=\s(?P<info>{.+?});', re.DOTALL,
)


def extract(url):
    req = urllib.request.Request(url=url, headers=HEADERS)
    with urllib.request.urlopen(req) as response:
        html = gzip.decompress(response.read()).decode('utf-8')

    if match := PLAYER_PATTERN.search(html):
        player_url = match.group('url')
    else:
        print('Player info missing', file=sys.stderr)
        return 1

    HEADERS['Referer'] = url
    req = urllib.request.Request(url=player_url, headers=HEADERS)
    with urllib.request.urlopen(req) as response:
        html = gzip.decompress(response.read()).decode('utf-8')

    if match := VIDEO_INFO_PATTERN.search(html):
        info = re.sub("\s(\w+):", r'"\1":',  match.group('info'), re.DOTALL)
        try:
            info = loads(info)
        except Exception:
            print('JSON decode error', file=sys.stderr)
            return 1
    else:
        print('Video info missing', file=sys.stderr)
        return 1

    if b64_server := info.get('server'):
        server = b64decode(b64_server[::-1]).decode('utf-8')
    else:
        print('Server info missing', file=sys.stderr)
        return 1

    if not (video := info.get('video', {})):
        print('Video metadata missing', file=sys.stderr)
        return 1
    elif not (vid := video.get('cdn_id', video.get('id'))):
        print('Video ID missing', file=sys.stderr)
        return 1
    else:
        cdn_id = vid.replace('_', '/')

    if not (options := video.get('cdn_files')):
        if not (options := video.get('partial', {}).get('quality')):
            print('CDN metadata missing')
            return 1

    name = options[max(options)].replace('.', '.mp4?extra=')
    print(f'https://{server}/videos/{cdn_id}/{name}')


def main():
    parser = ArgumentParser(description='Daxab CDN video url extractor')
    parser.add_argument(
        'url',
        help='direct video link',
        type=str,
    )
    args = parser.parse_args()
    try:
        return extract(args.url)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    try:
        exit(main())
    except KeybaordInterrupt:
        raise SystemExit(130)
