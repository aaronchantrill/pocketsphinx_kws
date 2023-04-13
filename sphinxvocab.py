# -*- coding: utf-8 -*-
import logging
import os
import re
import tempfile
from .g2p import PhonetisaurusG2P
from naomi import profile


def delete_temp_file(file_to_delete):
    if True:
        os.remove(file_to_delete)


def get_languagemodel_path(path):
    """
    Returns:
        The path of the the pocketsphinx languagemodel file as string
    """
    return os.path.join(path, 'languagemodel')


def get_dictionary_path(path):
    """
    Returns:
        The path of the pocketsphinx dictionary file as string
    """
    return os.path.join(path, 'dictionary')


def get_thresholds_path(path):
    """
    Returns:
        The path to the pocketsphinx_kws keywords file as string
    """
    return os.path.join(path, 'kws.thresholds')


def compile_vocabulary(directory, phrases):
    """
    Compiles the vocabulary to the Pocketsphinx format by creating a
    languagemodel and a dictionary.

    Arguments:
        phrases -- a list of phrases that this vocabulary will contain
    """
    logger = logging.getLogger(__name__)
    languagemodel_path = get_languagemodel_path(directory)
    dictionary_path = get_dictionary_path(directory)

    nbest = profile.get(
        ['pocketsphinx', 'nbest'],
        3
    )
    hmm_dir = profile.get(
        ['pocketsphinx', 'hmm_dir']
    )
    fst_model = os.path.join(hmm_dir, 'g2p_model.fst')
    fst_model_alphabet = profile.get(
        ['pocketsphinx', 'fst_model_alphabet'],
        'arpabet'
    )

    if not fst_model:
        raise ValueError('FST model not specified!')

    if not os.path.exists(fst_model):
        raise OSError('FST model {} does not exist!'.format(fst_model))

    g2pconverter = PhonetisaurusG2P(
        fst_model,
        fst_model_alphabet=fst_model_alphabet,
        nbest=nbest
    )

    logger.debug('Languagemodel path: %s' % languagemodel_path)
    logger.debug('Dictionary path:    %s' % dictionary_path)
    text = " ".join(
        [("<s> %s </s>" % phrase.upper()) for phrase in phrases]
    )
    # There's some strange issue when text2idngram sometime can't find any
    # input (although it's there). For a reason beyond me, this can be fixed
    # by appending a space char to the string.
    text += ' '
    logger.debug('Compiling languagemodel...')
    vocabulary = compile_vocabulary(text)
    logger.debug('Starting dictionary...')
    compile_dictionary(g2pconverter, vocabulary, dictionary_path)


def compile_vocabulary(text):
    """
    Returns a set of words from the text (keyword search mode does
    not require a language model, this is the first step in
    preparing a dictionary)

    Arguments:
        text -- the text the languagemodel will be generated from

    Returns:
        A list of all unique words this vocabulary contains.
    """
    if len(text.strip()) == 0:
        raise ValueError('No text to compile into vocabulary!')

    logger = logging.getLogger(__name__)

    # Get words from text
    logger.debug("Getting words from text...")
    words = set()
    line = text.strip()
    for word in line.split():
        if not word.startswith('#') and word not in ('<s>', '</s>'):
            words.add(word)

    if len(words) == 0:
        logger.warning('Vocabulary seems to be empty!')

    return words


def compile_dictionary(g2pconverter, corpus, output_file):
    """
    Compiles the dictionary from a list of words.

    Arguments:
        corpus -- the text the dictionary will be generated from
        output_file -- the path of the file this dictionary will
                       be written to
    """
    # read the standard dictionary in
    RE_WORDS = re.compile(
        r"^(?P<word>[a-zA-Z0-9'\.\-]+)(\(\d\))?\s+(?P<pronunciation>[a-zA-Z]+.*[a-zA-Z0-9])\s*$"
    )
    lexicon = {}
    with open(os.path.join(profile.get(['pocketsphinx', 'hmm_dir']), 'cmudict.dict'), 'r') as f:
        line = f.readline().strip()
        while line:
            for match in RE_WORDS.finditer(line):
                try:
                    lexicon[match.group('word')].append(
                        match.group('pronunciation').split()
                    )
                except KeyError:
                    lexicon[match.group('word')] = [
                        match.group('pronunciation').split()
                    ]
            line = f.readline().strip()

    # create a list of words from the corpus
    corpus_lexicon = {}
    words = set()
    for line in corpus:
        for word in line.split():
            words.add(word.lower())

    # Fetch pronunciations for every word in corpus
    for word in words:
        if word in lexicon:
            corpus_lexicon[word] = lexicon[word]
        else:
            corpus_lexicon[word] = []
            for w, p in g2pconverter.translate([word]):
                print(f"{w} - {p}")
                corpus_lexicon[word].append(p)
    with open(output_file, "w") as f:
        for word in sorted(corpus_lexicon):
            for index, phones in enumerate(corpus_lexicon[word]):
                if index == 0:
                    f.write(f"{word} {' '.join(phones)}\n")
                else:
                    f.write(f"{word}({index+1}) {' '.join(phones)}\n")
