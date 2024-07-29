import asyncio
from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as MediaManager, GlobalSystemMediaTransportControlsSessionPlaybackStatus as SessionPlaybackStatus
from lrclib import LrcLibAPI
from datetime import datetime, timedelta
import re
import time

def convert_to_timedelta(time_string):
    clean_time_string = time_string.strip("[]")
    time_obj = datetime.strptime(clean_time_string, "%M:%S.%f")
    return timedelta(minutes=time_obj.minute, seconds=time_obj.second, milliseconds=time_obj.microsecond / 1000)

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

async def get_media_info(sync = False):
    sessions = await MediaManager.request_async()
    current_session = sessions.get_current_session()
    
    if current_session:  # there needs to be a media session running
        if sync:
            await current_session.try_pause_async()
            await asyncio.sleep(0.1)
            await current_session.try_play_async()
            
        info = await current_session.try_get_media_properties_async()

        # Fetch timeline properties for playback position
        timeline_properties = current_session.get_timeline_properties()
        
        position_seconds = timeline_properties.position
        start_time_seconds = timeline_properties.start_time
        end_time_seconds = timeline_properties.end_time

        # song_attr[0] != '_' ignores system attributes
        info_dict = {song_attr: getattr(info, song_attr) for song_attr in dir(info) if song_attr[0] != '_'}
        
        # Add playback position information to the dictionary
        info_dict['position_seconds'] = position_seconds
        info_dict['start_time_seconds'] = start_time_seconds
        info_dict['end_time_seconds'] = end_time_seconds
        info_dict['playback_status'] = current_session.get_playback_info().playback_status
        
        # converts winrt vector to list
        info_dict['genres'] = list(info_dict.get('genres', []))

        return info_dict

    raise Exception('No active media session found.')

async def display_lyrics(lyrics):
    last_displayed_index = -1

    # Get initial media info
    current_media_info = await get_media_info(True)
    initial_position = current_media_info['position_seconds'].total_seconds()
    start_time = time.monotonic()  # Start high-resolution timer

    while True:
        current_media_info = await get_media_info()
        playback_status = current_media_info['playback_status']
        if current_media_info['title'] != startmediainfo['title']:
            raise Exception('music change')
        if playback_status == SessionPlaybackStatus.PLAYING:
            # Calculate the elapsed time since the start
            elapsed_time = time.monotonic() - start_time
            current_position = initial_position + elapsed_time
            
            # Find the correct line to display based on the current playback position
            for i, (time_delta, text) in enumerate(lyrics):
                if time_delta.total_seconds() <= current_position:
                    if i > last_displayed_index:
                        print(text)
                        last_displayed_index = i

        elif playback_status == SessionPlaybackStatus.PAUSED:
            # Update initial position and start time when resuming playback
            initial_position = current_media_info['position_seconds'].total_seconds()-0.5 #time added for sync purposes
            start_time = time.monotonic()

        await asyncio.sleep(0.1)  # Check the position every 0.1 seconds

if __name__ == '__main__':
    while True:
        try:
            api = LrcLibAPI(user_agent="my-app/0.0.1")
            current_media_info = asyncio.run(get_media_info())
            print(current_media_info)
            startmediainfo=current_media_info
            
            results = api.search_lyrics(
                track_name=current_media_info['title'],
                artist_name=current_media_info['artist'],
                album_name=current_media_info['album_title']
            )
            if len(results)<1:
                results = api.search_lyrics(
                track_name=current_media_info['title'],
            )
                
            if len(results)<1:
                raise Exception('Lyrics not found in api')
            
            lyrics = api.get_lyrics_by_id(lrclib_id=results[0].id).synced_lyrics
            parsed_lyrics = parse_lyric_file(lyrics)
                
            asyncio.run(display_lyrics(parsed_lyrics))
        except Exception as e:
            print('Error:',e)
        asyncio.sleep(1)