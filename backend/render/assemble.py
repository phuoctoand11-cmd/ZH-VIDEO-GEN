from moviepy import AudioFileClip, VideoClip, concatenate_audioclips, concatenate_videoclips

from render.kenburns import make_kenburns_clip

ASPECT_SIZES = {
    "9:16": (720, 1280),
    "16:9": (1280, 720),
}


def build_static_scene_clip(image_path: str, audio_paths: list[str], aspect_ratio: str) -> VideoClip:
    """Ken Burns pan over an already-fully-rendered card image (text baked in
    by the caller) plus its audio track — no per-frame text overlay.
    """
    size = ASPECT_SIZES[aspect_ratio]
    audio_clips = [AudioFileClip(p) for p in audio_paths]
    # concatenate_audioclips() reads from these clips lazily at write_videofile
    # time, so they must stay open — do not close them here.
    scene_audio = concatenate_audioclips(audio_clips)
    duration = sum(clip.duration for clip in audio_clips)
    background = make_kenburns_clip(image_path, duration=duration, size=size)
    return background.with_audio(scene_audio)


def assemble_video(scene_clips: list[VideoClip], out_path: str) -> str:
    final = concatenate_videoclips(scene_clips, method="compose")
    try:
        final.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
    finally:
        # write_videofile spawns an ffmpeg subprocess per clip in the chain;
        # closing releases those processes and their buffers instead of
        # holding them until the whole request (all items, all ratios) ends.
        final.close()
        for clip in scene_clips:
            clip.close()
    return out_path
