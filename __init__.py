# -*- coding: utf-8 -*-
import os.path
import re
import tempfile
from collections import OrderedDict
from naomi import paths
from naomi import plugin
from naomi import profile
from naomi import run_command
from . import sphinxvocab
try:
    from . import sphinxvocab
    from .g2p import PhonetisaurusG2P
except ModuleNotFoundError as e:
    # Try to install phonetisaurus from pypi
    cmd = [
        'pip', 'install', 'phonetisaurus'
    ]
    completedprocess = run_command(cmd)
    if completedprocess.returncode != 0:
        # check what architecture we are on
        architecture = platform.machine()
        phonetisaurus_url = ""
        if architecture == "x86_64":
            wheel = "phonetisaurus-0.3.0-py3-none-manylinux1_x86_64.whl"
        elif architecture == "arm6l":
            wheel = "phonetisaurus-0.3.0-py3-none-linux_armv6l.whl"
        elif architecture == "arm7l":
            wheel = "phonetisaurus-0.3.0-py3-none-linux_armv7l.whl"
        elif architecture == "aarch64":
            wheel = "phonetisaurus-0.3.0-py3-none-linux_aarch64.whl"
        else:
            # Here we should probably build the package from source
            raise(f"Architecture {architecture} is not supported at this time")
        phonetisaurus_url = f"https://github.com/rhasspy/phonetisaurus-pypi/releases/download/v0.3.0/{wheel}"
        phonetisaurus_path = paths.sub('sources', wheel)
        cmd = [
            'curl', '-L', '-o', phonetisaurus_path, phonetisaurus_url
        ]
        completedprocess = run_command(cmd)
        if completedprocess.returncode != 0:
            raise Exception("Unable to download file from {phonetisaurus_url}")
        else:
            # use pip to install the file
            cmd = [
                'pip',
                'install',
                phonetisaurus_path
            ]
            completedprocess = run_command(cmd)
            if completedprocess.returncode == 0:
                # Check if phonetisaurus is intalled
                if importlib.util.find_spec("phonetisaurus"):
                    from . import sphinxvocab
                    from .g2p import PhonetisaurusG2P
                else:
                    raise Exception("Phonetisaurus install failed")
            else:
                raise Exception("Phonetisaurus install failed")
try:
    try:
        from pocketsphinx import pocketsphinx
    except ValueError:
        # Fixes a quirky bug when first import doesn't work.
        # See http://sourceforge.net/p/cmusphinx/bugs/284/ for details.
        from pocketsphinx import pocketsphinx
    pocketsphinx_available = True
except ImportError:
    pocketsphinx = None
    pocketsphinx_available = False


# AaronC - This searches some standard places (/bin, /usr/bin, /usr/local/bin)
# for a program name.
# This could be updated to search the PATH, and also verify that execute
# permissions are set, but for right now this is a quick and dirty
# placeholder.
def check_program_exists(program):
    standardlocations = ['/usr/local/bin', '/usr/bin', '/bin']
    response = False
    for location in standardlocations:
        if(os.path.isfile(os.path.join(location, program))):
            response = True
    return response


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
class PocketsphinxKWSPlugin(plugin.STTPlugin):
    # You will usually have to do some initialization to get
    # your plugin working. Remember to run the parent init method:
    def __init__(self, *args, **kwargs):
        plugin.STTPlugin.__init__(self, *args, **kwargs)

        self._vocabulary_name = "keywords"
        keywords = profile.get(['keyword'], ['Naomi'])
        if isinstance(keywords, str):
            keywords = [keywords]
        keywords = [keyword.lower() for keyword in keywords]
        self._vocabulary_phrases = keywords
        self._logger.info(
            "Adding vocabulary {} containing phrases {}".format(
                self._vocabulary_name,
                self._vocabulary_phrases
            )
        )

        vocabulary_path = self.compile_vocabulary(
            sphinxvocab.compile_vocabulary
        )

        dict_path = sphinxvocab.get_dictionary_path(vocabulary_path)
        thresholds_path = sphinxvocab.get_thresholds_path(vocabulary_path)
        msg = " ".join([
            "Creating thresholds file '{}'",
            "See README.md for more information."
        ]).format(thresholds_path)
        print(msg)
        with open(thresholds_path, 'w') as f:
            for keyword in keywords:
                threshold = profile.get(['Pocketsphinx_KWS', 'thresholds', keyword], -30)
                if(threshold < 0):
                    f.write("{}\t/1e{}/\n".format(keyword, threshold))
                else:
                    f.write("{}\t/1e+{}/\n".format(keyword, threshold))
        hmm_dir = profile.get(['pocketsphinx', 'hmm_dir'])
        # Perform some checks on the hmm_dir so that we can display more
        # meaningful error messages if neccessary
        if not os.path.exists(hmm_dir):
            msg = " ".join([
                "hmm_dir '{}' does not exist! Please make sure that you",
                "have set the correct hmm_dir in your profile."
            ]).format(hmm_dir)
            self._logger.error(msg)
            raise RuntimeError(msg)
        # Lets check if all required files are there. Refer to:
        # http://cmusphinx.sourceforge.net/wiki/acousticmodelformat
        # for details
        missing_hmm_files = []
        for fname in ('mdef', 'feat.params', 'means', 'noisedict',
                      'transition_matrices', 'variances'):
            if not os.path.exists(os.path.join(hmm_dir, fname)):
                missing_hmm_files.append(fname)
        mixweights = os.path.exists(os.path.join(hmm_dir, 'mixture_weights'))
        sendump = os.path.exists(os.path.join(hmm_dir, 'sendump'))
        if not mixweights and not sendump:
            # We only need mixture_weights OR sendump
            missing_hmm_files.append('mixture_weights or sendump')
        if missing_hmm_files:
            self._logger.warning(
                " ".join([
                    "hmm_dir '%s' is missing files: %s.",
                    "Please make sure that you have set the correct",
                    "hmm_dir in your profile."
                ]).format(hmm_dir, ', '.join(missing_hmm_files))
            )
        with tempfile.NamedTemporaryFile(
            prefix='psdecoder_',
            suffix='.log',
            delete=False
        ) as f:
            self._logfile = f.name
            self._logger.info('Pocketsphinx log file: {}'.format(self._logfile))

        # Pocketsphinx v5
        self._config = pocketsphinx.Config(
            hmm=hmm_dir,
            kws=thresholds_path,
            dict=dict_path
        )
        self._ps = pocketsphinx.Decoder(self._config)

    # Your plugin will probably rely on some profile settings:
    def settings(self):
        language = profile.get(['language'])
        # Get the defaults for settings
        # hmm_dir
        hmm_dir = profile.get(
            ['pocketsphinx', 'hmm_dir']
        )
        if(not hmm_dir):
            # Make a list of possible paths to check
            hmm_dir_paths = [
                os.path.join(
                    os.path.expanduser("~"),
                    "pocketsphinx-python",
                    "pocketsphinx",
                    "model",
                    "en-us",
                    "en-us"
                ),
                os.path.join(
                    os.path.expanduser("~"),
                    "pocketsphinx",
                    "model",
                    "en-us",
                    "en-us"
                ),
                os.path.join(
                    "/",
                    "usr",
                    "share",
                    "pocketsphinx",
                    "model",
                    "en-us",
                    "en-us"
                ),
                os.path.join(
                    "/usr",
                    "local",
                    "share",
                    "pocketsphinx",
                    "model",
                    "hmm",
                    "en_US",
                    "hub4wsj_sc_8k"
                )
            ]
            # see if any of these paths exist
            for path in hmm_dir_paths:
                if os.path.isdir(path):
                    hmm_dir = path
        # fst_model
        fst_model = os.path.join(hmm_dir, 'g2p_model.fst')
        # If either the hmm dir or fst model is missing, then
        # download the standard model
        if not(hmm_dir and os.path.isdir(hmm_dir) and fst_model and os.path.isfile(fst_model)):
            # Start by checking to see if we have a copy of the standard
            # model for this user's chosen language and download it if not.
            # Check for the files we need
            language = profile.get_profile_var(['language'])
            base_working_dir = paths.sub("pocketsphinx")
            if not os.path.isdir(base_working_dir):
                os.mkdir(base_working_dir)
            standard_dir = os.path.join(base_working_dir, "standard")
            if not os.path.isdir(standard_dir):
                os.mkdir(standard_dir)
            standard_dir = os.path.join(standard_dir, language)
            if not os.path.isdir(standard_dir):
                os.mkdir(standard_dir)
            hmm_dir = standard_dir
            if(not sphinxbase.check_pocketsphinx_model(hmm_dir)):
                # Check and see if we already have a copy of the standard
                # language model
                print("Downloading and installing the {} pocketsphinx language model".format(language))
                cmd = [
                    'git',
                    'clone',
                    '-b',
                    language,
                    'https://github.com/NaomiProject/CMUSphinx_standard_language_models.git',
                    hmm_dir
                ]
                completedprocess = run_command.run_command(cmd)
                self._logger.info(run_command.process_completedprocess(completedprocess))
                if completedprocess.returncode != 0:
                    raise Exception("Error downloading standard language model")
            if (not os.path.isfile(fst_model)):
                # Use phonetisaurus to prepare an fst model
                print("Training an FST model")
                PhonetisaurusG2P.train_fst(
                    cmudict_path,
                    fst_model
                )

        _ = self.gettext
        return OrderedDict(
            [
                (
                    ('pocketsphinx', 'hmm_dir'), {
                        'title': _('PocketSphinx hmm file'),
                        'description': "".join([
                            _('PocketSphinx hidden markov model directory')
                        ]),
                        'default': hmm_dir
                    }
                )
            ]
        )

    def reinit(self):
        self._logger.debug(
            "Re-initializing PocketSphinx Decoder {self._vocabulary_name}"
        )
        # Pocketsphinx v5
        self._ps.reinit(self._config)

    # The only method you really have to override to instantiate a
    # STT plugin is the transcribe() method, which recieves a pointer
    # to the file containing the audio to be transcribed:
    def transcribe(self, fp):
        """
        Performs STT, transcribing an audio file and returning the result.

        Arguments:
            fp -- a file object containing audio data
        """
        transcribed = []
        fp.seek(44)
        audio_data = fp.read()
        while True:
            try:
                self._ps.start_utt()
                self._ps.process_raw(audio_data, False, True)
                self._ps.end_utt()
                segs = self._ps.seg()
                if segs:
                    for s in self._ps.seg():
                        # For some reason, the word comes back from the keyword spotter
                        # with whitespace at the end. I guess from the kws.thresholds
                        # file? So strip the word before comparing
                        word = s.word.strip()
                        if(word in self._vocabulary_phrases):
                            transcribed.append(word)
                break
            except RuntimeError as e:
                self.reinit()
        return transcribed
