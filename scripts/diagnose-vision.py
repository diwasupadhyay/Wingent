"""Send an in-memory synthetic red image to the local Ollama vision model."""

import base64
import os
import struct
import zlib

import httpx


def chunk(kind, data):
    body = kind + data
    return struct.pack('!I', len(data)) + body + struct.pack('!I', zlib.crc32(body))


def red_png(size=64):
    row = b'\x00' + b'\xff\x00\x00' * size
    return (b'\x89PNG\r\n\x1a\n' +
            chunk(b'IHDR', struct.pack('!2I5B', size, size, 8, 2, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(row * size)) + chunk(b'IEND', b''))


if __name__ == '__main__':
    model = os.getenv('OLLAMA_VISION_MODEL', 'qwen3-vl:4b-instruct')
    with httpx.Client(timeout=90) as client:
        response = client.post('http://127.0.0.1:11434/api/generate', json={
            'model': model, 'stream': False, 'prompt': 'What is the main color of this image? Answer briefly.',
            'images': [base64.b64encode(red_png()).decode('ascii')],
            'options': {'temperature': 0, 'num_predict': 40, 'num_ctx': 4096},
        })
        response.raise_for_status()
        print('model:', model)
        print('response:', response.json().get('response', '').strip()[:300])
