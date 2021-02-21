from wutils.general import save_pickle, load_pickle
import json
from datetime import timedelta

def transcribe_gcs_with_word_time_offsets(gcs_uri):
    """Transcribe the given audio file asynchronously and output the word time
    offsets."""
    from google.cloud import speech

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
    result = operation.result(timeout=180)

    words = []
    for result in result.results:
        alternative = result.alternatives[0]
        print("Transcript: {}".format(alternative.transcript))
        print("Confidence: {}".format(alternative.confidence))

        for word_info in alternative.words:
            word = word_info.word
            start_time = word_info.start_time
            end_time = word_info.end_time
            words.append({
                'word': word,
                'start_time': word_info.start_time / timedelta(milliseconds=1),
                'end_time': word_info.end_time / timedelta(milliseconds=1)
            })

            print(
                f"Word: {word} - start_time: {start_time.total_seconds()}, end_time: {end_time.total_seconds()}"
            )
    return words


with open('transcript.json', 'w') as f:
    json.dump(transcribe_gcs_with_word_time_offsets('gs://nutshell-audio/psych.flac'), f)
