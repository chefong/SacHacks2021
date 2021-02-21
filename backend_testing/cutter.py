from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
ffmpeg_extract_subclip("css.mp4", 10.5, 11.5, targetname="css_seg.mp4")
