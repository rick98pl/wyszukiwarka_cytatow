import os
import json
import re
import pytube
from moviepy.editor import AudioFileClip
import whisper

# Define YouTube playlist URL
playlist_url = 'https://www.youtube.com/playlist?list=PLHtUOYOPwzJHnBmX0wOOqHo5lJ4FWxEyB'

# Create directories to save the files
downloads_path = 'downloads'
subtitles_path = 'kapitanBombaSubtitles'
os.makedirs(downloads_path, exist_ok=True)
os.makedirs(subtitles_path, exist_ok=True)

import os
import pytube
from moviepy.editor import AudioFileClip

import os
import pytube
import moviepy.editor as mp
from pytube.exceptions import PytubeError
from moviepy.audio.io.AudioFileClip import AudioFileClip
from retrying import retry

import os
import pytube
import moviepy.editor as mp
from pytube.exceptions import PytubeError
from retrying import retry
#from audio_separator.separator import Separator
#separator = Separator()
#separator.load_model()

def download_and_convert_to_wav(video_url, download_path, video_title, timeout=30):
    wav_file = os.path.join(download_path, f'{video_title}.wav')
    
    if os.path.exists(wav_file):
        print(f'WAV file already exists: {wav_file}')
        return wav_file
    
    @retry(wait_fixed=5000, stop_max_attempt_number=3)
    def download_video(url, path):
        try:
            yt = pytube.YouTube(url)
            video = yt.streams.filter(only_audio=True).first()
            print('Downloading from YouTube...')
            return video.download(output_path=path)
        except PytubeError as e:
            print(f'Error downloading video: {str(e)}')
            raise e

    try:
        # Download the video with retry logic
        out_file = download_video(video_url, download_path)
        print('Downloaded video file:', out_file)
        
        # Convert to WAV using moviepy
        base, ext = os.path.splitext(out_file)
        new_file = os.path.join(download_path, f'{video_title}.wav')
        
        audio_clip = mp.AudioFileClip(out_file)
        audio_clip = audio_clip.set_fps(16000)
        audio_clip.write_audiofile(new_file, codec='pcm_s16le')
        audio_clip.close()
        
        # Remove the original file after conversion
        os.remove(out_file)
        
        print(f'Converted video to WAV (16000 Hz): {new_file}')
        return new_file
    
    except Exception as e:
        print(f'Error downloading/converting: {str(e)}')
        return None



# Function to transcribe audio using OpenAI Whisper
def transcribe_audio(file_path):
    modelName = 'large'
    print('loading model ' + modelName)
    model = whisper.load_model(modelName)
    options = whisper.DecodingOptions().__dict__.copy()
    options['no_speech_threshold'] = 0.275
    options['logprob_threshold'] = None
    print(modelName + ' model loaded...')
    result = model.transcribe(file_path, language='pl')
    return result['text']


# Function to create subtitle json
def create_subtitle_json(video_title, transcription, video_id):
    subtitles = {}
    timestamp_url = f"https://youtu.be/{video_id}"
    time_key = video_title
    subtitles[time_key] = {"text": transcription, "url": timestamp_url}

    json_file_path = os.path.join(subtitles_path, f'{video_title}.json')
    with open(json_file_path, 'w', encoding='utf-8') as json_file:
        json.dump(subtitles, json_file, ensure_ascii=False, indent=4)

import numpy as np
import librosa
import soundfile as sf

def replace_odc_with_spaces(input_string):
    # Define the regular expression pattern
    pattern = r'ODC\.\s+'

    # Replace using re.sub
    replaced_string = re.sub(pattern, 'ODC.', input_string)

    return replaced_string

def format_episode_title(original_string):
    x = replace_odc_with_spaces(original_string)
    x = x.replace('ODC.', 'ODC. ')
    return x

def vocal_separation(input_file, output_file):
    # Load audio file
    y, sr = librosa.load(input_file, sr=None)

    # Separate harmonics and percussives into two waveforms
    y_harmonic, y_percussive = librosa.effects.hpss(y)

    # Save the percussive component as the separated vocal track
    sf.write(output_file, y_percussive, sr)

# Download playlist
playlist = pytube.Playlist(playlist_url)

for video_url in playlist.video_urls:
    video = pytube.YouTube(video_url)
    video_title = video.title
    video_title = format_episode_title(video_title)

    pattern = r'\(ODC\. (\d+)\)'
    match = re.search(pattern, video_title)
    print(video_title)
    episode_number = match.group(1)

    video_title = '[' + episode_number + '] ' + video_title
    if int(episode_number) < 51 or int(episode_number) == 52:
        continue

    video_id = pytube.extract.video_id(video_url)

    print(video_id)
    print(video_title)
    json_file_path = os.path.join(subtitles_path, f'{video_title}.json')
    print(json_file_path)
    
    if os.path.exists(json_file_path):
        print(f'Skipping already processed video: {video_title}')
        continue

    print(f'Downloading and processing: {video_title}')
    wav_file = download_and_convert_to_wav(video_url, downloads_path, video_title)
    print('separating...')
    vocal_separation(wav_file, wav_file)
    print('separating done..')
    #quit()

    transcription = transcribe_audio(wav_file)
    
    print(transcription)
    create_subtitle_json(video_title, transcription, video_id)
    print(f'Finished processing: {video_title}')

print('All videos processed.')
