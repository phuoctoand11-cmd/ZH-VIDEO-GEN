import os

# moviepy resolves its ffmpeg binary at import time (moviepy.config reads
# FFMPEG_BINARY once, at module import). By default it uses the ffmpeg
# bundled with imageio-ffmpeg rather than the system ffmpeg on PATH. That
# bundled binary can estimate mp3 duration slightly differently than the
# system ffmpeg/ffprobe used elsewhere in tests (e.g. to generate/verify
# fixture audio in tests/render/test_assemble.py), which can make
# duration-sensitive assertions flaky or fail outright.
#
# Setting this here, in a conftest.py at the root of `testpaths`, ensures
# it is set before pytest imports any test module (and therefore before
# moviepy itself is ever imported), so moviepy consistently resolves
# ffmpeg via PATH instead of its bundled binary.
os.environ.setdefault("FFMPEG_BINARY", "auto-detect")
