import asyncio
from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as MediaManager, GlobalSystemMediaTransportControlsSessionPlaybackStatus as SessionPlaybackStatus
import winrt.windows.storage.streams as wss
from lrclib import LrcLibAPI
from datetime import datetime, timedelta
import re
import time
import io
import cv2
import PIL
from tkinter import *
import pyglet
import async_tkinter_loop
import numpy as np
import colors
def convert_to_timedelta(time_string):
    clean_time_string = time_string.strip("[]")
    time_obj = datetime.strptime(clean_time_string, "%M:%S.%f")
    return timedelta(minutes=time_obj.minute, seconds=time_obj.second, milliseconds=time_obj.microsecond / 1000)

def pil_to_cv2(pil_image):
    open_cv_image = np.array(pil_image)
    # Convert RGB to BGR
    open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2BGR)
    return open_cv_image

def parse_lyric_file(file_content):
    pattern = re.compile(r"\[(\d{2}:\d{2}\.\d{2})\] (.+)")
    lyrics = []
    for line in file_content.split("\n"):
        match = pattern.match(line)
        if match:
            time_string, text = match.groups()
            time_delta = convert_to_timedelta(time_string)
            lyrics.append((time_delta, text))
    return lyrics

async def get_media_info(sync=False):
    sessions = await MediaManager.request_async()
    current_session = sessions.get_current_session()
    
    if current_session:
        if sync:
            await current_session.try_pause_async()
            await asyncio.sleep(0.1)
            await current_session.try_play_async()
            
        info = await current_session.try_get_media_properties_async()
        timeline_properties = current_session.get_timeline_properties()
        
        position_seconds = timeline_properties.position
        start_time_seconds = timeline_properties.start_time
        end_time_seconds = timeline_properties.end_time

        info_dict = {song_attr: getattr(info, song_attr) for song_attr in dir(info) if song_attr[0] != '_'}
        info_dict['position_seconds'] = position_seconds
        info_dict['start_time_seconds'] = start_time_seconds
        info_dict['end_time_seconds'] = end_time_seconds
        info_dict['playback_status'] = current_session.get_playback_info().playback_status
        info_dict['genres'] = list(info_dict.get('genres', []))

        if info.thumbnail:
            stream_ref = info.thumbnail
            stream = await stream_ref.open_read_async()

            # Read the stream into bytes
            buffer = bytearray(stream.size)
            reader = wss.DataReader(stream)
            await reader.load_async(stream.size)
            reader.read_bytes(buffer)

            # Convert bytes to PIL image
            image = PIL.Image.open(io.BytesIO(buffer))
            info_dict['thumbnail'] = image
        else:
            info_dict['thumbnail'] = None
        if(info_dict):
            return info_dict
        else:
            return None

    raise Exception('No active media session found.')

def round_rectangle(canvas, x1, y1, x2, y2, radius=25, **kwargs):
    points = [
        x1 + radius, y1,
        x1 + radius, y1,
        x2 - radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1 + radius,
        x1, y1
    ]
    return canvas.create_polygon(points, **kwargs, smooth=True)

class LyricDisplay:
    def __init__(self, root, text, color1='gray10', color2='white'):
        self.root = root
        self.canvas = Canvas(self.root, bg='magenta', highlightthickness=0)
        self.canvas.pack(fill=BOTH, expand=True)
        self.color1 = color1
        self.color2 = color2
        self.font = ('ProximaNova', 15)
        self.padding = 10
        self.update_text(text)

    def update_text(self, text, ucolor1='gray10', ucolor2='white'):
        self.color1=ucolor1
        self.color2=ucolor2
        self.canvas.delete("all")
        temp_text = self.canvas.create_text(0, 0, text=text, font=self.font, anchor=NW)
        bbox = self.canvas.bbox(temp_text)
        self.canvas.delete(temp_text)
        x1, y1, x2, y2 = bbox
        x1 += self.padding
        y1 += self.padding
        x2 += 2 * self.padding
        y2 += 2 * self.padding
        self.canvas.config(width=x2-x1+30, height=y2-y1+30)
        round_rectangle(self.canvas, x1, y1, x2, y2, radius=20, fill=self.color1, outline=self.color1)
        self.canvas.create_text((x1 + x2) // 2, (y1 + y2) // 2, text=text, font=self.font, fill=self.color2, anchor=CENTER)
        window_height = y2 - y1 + 30
        window_width = x2 - x1 + 30
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = screen_height - window_height -30
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        

async def display_lyrics(lyrics, lyric_display, startinfo):
    last_displayed_index = -1
    current_media_info = await get_media_info(True)
    initial_position = current_media_info['position_seconds'].total_seconds()
    start_time = time.monotonic()
    playback_status = current_media_info['playback_status']
    color1, color2 = colors.get_contrasting_colors(pil_to_cv2(current_media_info['thumbnail']),10)
    while True:
        current_media_info = await get_media_info()
        if current_media_info['playback_status'] != playback_status:
            print(current_media_info['playback_status'])
        playback_status = current_media_info['playback_status']
        if current_media_info['title'] != startinfo['title']:
            raise Exception('music change')
        if playback_status == SessionPlaybackStatus.PLAYING:
            elapsed_time = time.monotonic() - start_time
            current_position = initial_position + elapsed_time

            for i, (time_delta, text) in enumerate(lyrics):
                if time_delta.total_seconds() <= current_position:
                    if i > last_displayed_index:
                        print(text)
                        lyric_display.update_text(text,color1,color2)
                        last_displayed_index = i

        elif playback_status == SessionPlaybackStatus.PAUSED:
            initial_position = current_media_info['position_seconds'].total_seconds() - 0.5
            start_time = time.monotonic()

        await asyncio.sleep(0.5)  # Increase the interval to reduce lag

async def main_loop():
    while True:
        try:
            current_media_info = await get_media_info()
            print(current_media_info)
            cv2_image = pil_to_cv2(current_media_info['thumbnail'])
            cv2.imshow('cover',cv2_image)
            startmediainfo = current_media_info

            results = api.search_lyrics(
                track_name=current_media_info['title'],
                artist_name=current_media_info['artist'],
                album_name=current_media_info['album_title']
            )
            if len(results) < 1:
                results = api.search_lyrics(
                    track_name=current_media_info['title'],
                )

            if len(results) < 1:
                raise Exception('Lyrics not found in api')

            lyrics = api.get_lyrics_by_id(lrclib_id=results[0].id).synced_lyrics
            parsed_lyrics = parse_lyric_file(lyrics)

            await display_lyrics(parsed_lyrics, lyric_display, startmediainfo)
        except Exception as e:
            print('Error:', e)
        await asyncio.sleep(2)  # Increase the interval to reduce lag

if __name__ == '__main__':
    pyglet.font.add_file('ProximaNova.otf')

    root = Tk()
    root.overrideredirect(True)
    root.geometry("+250+250")
    root.lift()
    root.wm_attributes("-topmost", True)
    root.wm_attributes("-transparentcolor", "magenta")
    lyric_display = LyricDisplay(root, text="Initial Text")
    root.after(1, async_tkinter_loop.async_handler(main_loop))
    api = LrcLibAPI(user_agent="my-app/0.0.1")
    
    async_tkinter_loop.async_mainloop(root)