from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as MediaManager, GlobalSystemMediaTransportControlsSessionPlaybackStatus as SessionPlaybackStatus

class MediaEventHandler:
    def __init__(self, update_callback):
        self.update_callback = update_callback

    async def initialize(self):
        self.media_manager = await MediaManager.request_async()
        self.media_manager.add_current_session_changed(self.media_manager_current_session_changed)
        await self.subscribe_to_session_events(self.media_manager.get_current_session())

    async def media_manager_current_session_changed(self, sender, args):
        current_session = sender.get_current_session()
        await self.subscribe_to_session_events(current_session)

    async def subscribe_to_session_events(self, session):
        if session:
            session.add_playback_info_changed(self.session_playback_info_changed)
            session.add_media_properties_changed(self.session_media_properties_changed)
            session.add_timeline_properties_changed(self.session_timeline_properties_changed)

    async def session_playback_info_changed(self, sender, args):
        await self.update_callback()

    async def session_media_properties_changed(self, sender, args):
        await self.update_callback()

    async def session_timeline_properties_changed(self, sender, args):
        await self.update_callback()
