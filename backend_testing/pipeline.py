from summarizer import Summarizer
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from pytube import YouTube, extract
from google.cloud import storage
from moviepy.editor import *
import json
from datetime import timedelta

BUCKET_NAME = 'nutshell-audio'

def upload_to_bucket(blob_name, path_to_file):
    storage_client = storage.Client.from_service_account_json(
        'gcp.json')

    bucket = storage_client.get_bucket(BUCKET_NAME)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(path_to_file)

    return blob.public_url


def transcribe_gcs_with_word_time_offsets(filename):
    """Transcribe the given audio file asynchronously and output the word time
    offsets."""
    from google.cloud import speech
    gcs_uri = f'gs://nutshell-audio/{filename}'

    client = speech.SpeechClient()

    audio = speech.RecognitionAudio(uri=gcs_uri)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.FLAC,
        language_code="en-US",
        enable_word_time_offsets=True,
        model='video',
        audio_channel_count=2,
        enable_automatic_punctuation=True
    )

    operation = client.long_running_recognize(config=config, audio=audio)

    print("Waiting for operation to complete...")
    result = operation.result(timeout=60*10)

    words = []
    for result in result.results:
        alternative = result.alternatives[0]

        for word_info in alternative.words:
            words.append({
                'word': word_info.word,
                'start_time': word_info.start_time / timedelta(milliseconds=1),
                'end_time': word_info.end_time / timedelta(milliseconds=1)
            })
    return words

def merge_intervals(ints, thresh=1):
    out = []
    for interval in ints:
        if len(out) > 0 and interval[0] - out[-1][1] < thresh:
            old_st = out[-1][0]
            out.pop()
            out.append((old_st, interval[1]))
        else:
            out.append(interval)
    return out

def words2sents(words):
    doc = ''
    curr_sent = ''
    sents = []
    curr_start = None
    cnt = 0
    for val in words:
        word = val['word']
        if word[-1] in '!.?':
            if curr_start is None:
                print('WARNING: unknown start time!')
            curr_sent += word
            sents.append((curr_sent, curr_start, val['end_time']/1000))
            curr_sent = ''
        else:
            if not curr_sent:
                curr_start = val['start_time']/1000
            curr_sent += word + ' '
        cnt += 1
        doc += word + ' '
    # if curr_sent:
    #     sents.append(curr_sent[:-1])
    return doc, sents

def summarize(doc, sents, ratio=0.5):
    model = Summarizer()
    N = 5
    summary = model(doc, ratio=ratio)
    print(doc)
    # print(cnt)

    intervals = []
    for sent, st, end in sents:
        if sent in summary:
            intervals.append((st, end))
    print(intervals)
    intervals = merge_intervals(intervals)
    return intervals

def make_video(in_filename, intervals, out_filename):
    clip = VideoFileClip(in_filename)
    clips = []
    for i in range(len(intervals)):
        st, end = intervals[i]
        clips.append(clip.subclip(st, end))

    final = concatenate_videoclips(clips)
    final.write_videofile(out_filename)


def process_video(url, ratio=0.5):
    video = YouTube(url)
    vid_id = extract.video_id(url)
    filename = f'{vid_id}'
    # video.streams[0].download(VID_DIR, filename)
    video.streams.filter(file_extension='mp4')[0] \
        .download('./videos/', filename=filename)

    video_path = f'videos/{filename}.mp4'
    output_path = f'videos/out_{filename}.mp4'
    audio_path = f'videos/{filename}.flac'

    clip = VideoFileClip(video_path)
    clip.audio.write_audiofile(audio_path, codec='flac')
    bucket_audio = f'audio/{filename}.flac'

    upload_to_bucket(bucket_audio, audio_path)
    words = transcribe_gcs_with_word_time_offsets(bucket_audio)
    doc, sents = words2sents(words)
    intervals = summarize(doc, sents, ratio=ratio)
    make_video(video_path, intervals, output_path)

url = 'https://www.youtube.com/watch?v=OuC519ni1aE'
process_video(url)
