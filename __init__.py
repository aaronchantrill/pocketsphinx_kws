# -*- coding: utf-8 -*-
import os.path
import re
import tempfile
from collections import OrderedDict
from naomi import plugin
from naomi import pluginstore
from naomi import profile
from . import sphinxvocab
from pocketsphinx import Pocketsphinx

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
        keyword = profile.get(['keyword'],['Naomi'])
        if isinstance(keyword, str):
            keyword = [keyword]
        self._vocabulary_phrases = keyword
        self._logger.info(
            "Adding vocabulary {} containing phrases {}".format(
                self._vocabulary_name,
                self._vocabulary_phrases
            )
        )
        print(
            "Adding vocabulary {} containing phrases {}".format(
                self._vocabulary_name,
                self._vocabulary_phrases
            )
        )

        vocabulary_path = self.compile_vocabulary(
            sphinxvocab.compile_vocabulary
        )

        lm_path = sphinxvocab.get_languagemodel_path(vocabulary_path)
        dict_path = sphinxvocab.get_dictionary_path(vocabulary_path)
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
        # Pocketsphinx v5
        self._ps = Pocketsphinx(
            hmm=hmm_dir,
            lm=lm_path,
            dict=dict_path
        )
        self._logmath = self._ps.get_logmath()

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
        fst_model = profile.get_profile_var(["pocketsphinx", "fst_model"])
        if not fst_model:
            # Make a list of possible paths to check
            fst_model_paths = [
                os.path.join(
                    paths.sub(
                        os.path.join(
                            "pocketsphinx",
                            "adapt",
                            "en-US",
                            "train",
                            "model.fst"
                        )
                    )
                ),
                os.path.join(
                    os.path.expanduser("~"),
                    "pocketsphinx-python",
                    "pocketsphinx",
                    "model",
                    "en-us",
                    "train",
                    "model.fst"
                ),
                os.path.join(
                    os.path.expanduser("~"),
                    "cmudict",
                    "train",
                    "model.fst"
                ),
                os.path.join(
                    os.path.expanduser("~"),
                    "CMUDict",
                    "train",
                    "model.fst"
                ),
                os.path.join(
                    os.path.expanduser("~"),
                    "phonetisaurus",
                    "g014b2b.fst"
                )
            ]
            for path in fst_model_paths:
                if os.path.isfile(path):
                    fst_model = path
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
            fst_model = os.path.join(hmm_dir, "train", "model.fst")
            formatteddict_path = os.path.join(
                hmm_dir,
                "cmudict.formatted.dict"
            )
            if(not check_pocketsphinx_model(hmm_dir)):
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
                completedprocess = run_command(cmd)
                self._logger.info(process_completedprocess(completedprocess))
            if(not os.path.isfile(formatteddict_path)):
                print("Formatting the g2p dictionary")
                with open(os.path.join(standard_dir, "cmudict.dict"), "r") as in_file:
                    with open(formatteddict_path, "w+") as out_file:
                        for line in in_file:
                            # Remove whitespace at beginning and end
                            line = line.strip()
                            # remove the number in parentheses (if there is one)
                            line = re.sub('([^\\(]+)\\(\\d+\\)', '\\1', line)
                            # compress all multiple whitespaces into a single whitespace
                            line = re.sub('\s+', ' ', line)
                            # replace the first whitespace with a tab
                            line = line.replace(' ', '\t', 1)
                            print(line, file=out_file)
            if(not os.path.isfile(fst_model)):
                # Use phonetisaurus to prepare an fst model
                print("Training an FST model")
                cmd = [
                    "phonetisaurus-train",
                    "--lexicon", formatteddict_path,
                    "--seq2_del",
                    "--dir_prefix", os.path.join(hmm_dir, "train")
                ]
                completedprocess = run_command(cmd)
                self._logger.info(process_completedprocess(completedprocess))

        phonetisaurus_executable = profile.get_profile_var(
            ['pocketsphinx', 'phonetisaurus_executable']
        )
        if(not phonetisaurus_executable):
            if(check_program_exists('phonetisaurus-g2pfst')):
                phonetisaurus_executable = 'phonetisaurus-g2pfst'
            else:
                phonetisaurus_executable = 'phonetisaurus-g2p'
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
                ),
                (
                    ('pocketsphinx', 'fst_model'), {
                        'title': _('PocketSphinx FST file'),
                        'description': "".join([
                            _('PocketSphinx finite state transducer file')
                        ]),
                        'default': fst_model
                    }
                ),
                (
                    ('pocketsphinx', 'phonetisaurus_executable'), {
                        'title': _('Phonetisaurus executable'),
                        'description': "".join([
                            _('Phonetisaurus is used to build custom dictionaries')
                        ]),
                        'default': phonetisaurus_executable
                    }
                ),
            ]
        )

    # The only method you really have to override to instantiate a
    # STT plugin is the transcribe() method, which recieves a pointer
    # to the file containing the audio to be transcribed:
    def transcribe(self, fp):
        """
        Performs STT, transcribing an audio file and returning the result.

        Arguments:
            fp -- a file object containing audio data
        """
        self._ps.decode(
            audio_file=fp.name,
            buffer_size=2048,
            no_search=False,
            full_utt=False
        )
        segments = self._ps.segments(detailed=True)
        print(
            "Detailed segments (word, score, start, end): ",
            *segments,
            sep='\n\t'
        )
        best_keyword = None
        best_prob = -100000
        for word,prob,start,end in segments:
            if word in self._vocabulary_phrases:
                if prob > best_prob:
                    best_prob = prob
                    best_keyword = word
        if(best_keyword):
            print(
                "Detected keyword: {} probability: {} confidence: {}".format(
                    best_keyword,
                    best_prob,
                    self._logmath.exp(best_prob)
                )
            )
        print(
            "Best 10 hypothesis: ",
            *self._ps.best(count=10),
            sep='\n\t'
        )
        print(
            "Best hypothesis: {} model score: {} confidence: {}".format(
                self._ps.hypothesis(),
                self._ps.score(),
                self._ps.confidence()
            )
        )
        if(best_prob > -10):
            result = best_keyword
        transcribed = [result] if result != '' else []
        self._logger.info('Transcribed: %r', transcribed)
        return transcribed
