import json
from summarizer import Summarizer
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip

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

doc = ''
curr_sent = ''
sents = []
curr_start = None
# curr_end = None
sent_start = []
sent_end = []
cnt = 0
with open('./transcript.json', 'r') as f:
    words = json.load(f)
    for val in words:
        word = val['word']
        if word[-1] in '!.?':
            if curr_start is None:
                print('WARNING: unknown start time!')
            curr_sent += word
            sents.append((curr_sent, curr_start, val['end_time']/1000))
            # print('sent_end')
            # sent_end.append(val['end_time']/1000000)
            # curr_end = val['end_time']/100
            curr_sent = ''
        else:
            if not curr_sent:
                # print('sent_start')
                curr_start = val['start_time']/1000
                # sent_start.append()
            curr_sent += word + ' '
        cnt += 1
        doc += word + ' '
    if curr_sent:
        sents.append(curr_sent[:-1])

model = Summarizer()
N = 5
summary = model(doc, num_sentences=N)
print(doc)
print(cnt)

intervals = []
for sent, st, end in sents:
    if sent in summary:
        intervals.append((st, end))
print(intervals)
intervals = merge_intervals(intervals)
print(intervals)

from moviepy.editor import *
clip = VideoFileClip("psych.mp4")
clips = []
for i in range(len(intervals)):
    st, end = intervals[i]
    clips.append(clip.subclip(st, end))
    # ffmpeg_extract_subclip("css.mp4", st, end, targetname="pieces/piece{}.mp4".format(i))

final = concatenate_videoclips(clips)
final.write_videofile(f"psych(n={N}).mp4")

print('-'*25)
print(summary) 
# print(sents)
print(len(sents))
# print(list(zip(sent_start, sent_end)))
