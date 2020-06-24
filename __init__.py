# -*- coding: utf-8 -*-
from naomi import plugin


# The STT plugin converts an audio clip into a text transcription.
# When it is instantiated, it receives a name and a list of likely
# vocabulary words:
#    stt_plugin_info = plugins.get_plugin(
#        plugin_name,
#        category='stt'
#    )
#    stt_plugin_instance = stt_plugin_info.plugin_class(
#        'Name',
#        ["vocabulary", "words"],
#        stt_plugin_info
#    )
# The Name and vocabulary get stored in the self._vocabulary_name
# and self._vocabulary_phrases attributes respectively.
# The plugin also inherits the self._logger and self.gettext
# objects from plugin.GenericPlugin, and the self._vocabulary_compiled,
# self._vocabulary_path, self._samplerate and self._volume_normalization
# attributes from plugin.STTPlugin.
class MySTTPlugin(plugin.STTPlugin):
    # You will usually have to do some initialization to get
    # your plugin working. Remember to run the parent init method:
    def __init__(self, *args, **kwargs):
        plugin.STTPlugin.__init__(self, *args, **kwargs)
        self._logger.info(
            "Adding vocabulary {} containing phrases {}".format(
                self._vocabulary_name,
                self._vocabulary_phrases
            )
        )

    # Your plugin will probably rely on some profile settings:
    def settings(self):
        _ = self.gettext
        return OrderedDict(
            [
                (
                    ("plugin", "setting", "path"), {
                        "title": _("A brief description of the setting"),
                        "description": _("A longer description of the setting")
                    }
                )
            ]
        )

    # The only method you really have to override to instantiate a
    # STT plugin is the transcribe() method, which recieves a pointer
    # to the file containing the audio to be transcribed:
    def transcribe(self, fp):
        rawaudio = fp.read()
        return "This would be the transcription if I could hear you"