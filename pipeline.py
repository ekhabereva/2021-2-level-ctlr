"""
Pipeline for text processing implementation
"""

from pathlib import Path
import pymorphy2
from pymystem3 import Mystem

from constants import ASSETS_PATH
from core_utils.article import Article, ArtifactType

class EmptyDirectoryError(Exception):
    """
    No data to process
    """


class InconsistentDatasetError(Exception):
    """
    Corrupt data:
        - numeration is expected to start from 1 and to be continuous
        - a number of text files must be equal to the number of meta files
        - text files must not be empty
    """


class MorphologicalToken:
    """
    Stores language params for each processed token
    """
    def __init__(self, original_word):
        pass
        self.original_word = original_word
        self.normalized_form = ''
        self.tags_mystem = ''
        self.tags_pymorphy = ''

    def get_cleaned(self):
        """
        Returns lowercased original form of a token
        """
        return self.original_word.lower()

    def get_single_tagged(self):
        """
        Returns normalized lemma with MyStem tags
        """
        return f'{self.normalized_form}<{self.tags_mystem}>'

    def get_multiple_tagged(self):
        """
        Returns normalized lemma with PyMorphy tags
        """
        return f'{self.normalized_form}<{self.tags_mystem}>({self.tags_pymorphy})'


class CorpusManager:
    """
    Works with articles and stores them
    """
    def __init__(self, path_to_raw_txt_data: str):
        self.path_to_raw_txt_data = path_to_raw_txt_data
        self._storage = {}
        self._scan_dataset()

    def _scan_dataset(self):
        """
        Register each dataset entry
        """
        path_raw = Path(self.path_to_raw_txt_data)

        # * - the name of text file
        # glob module finds all the paths which match the template *_raw.txt
        for file in path_raw.glob('*_raw.txt'):
            article_id = int(file.stem.split('_')[0])
            self._storage[article_id] = Article(url=None, article_id=article_id)

    def get_articles(self):
        """
        Returns storage params
        """
        return self._storage


class TextProcessingPipeline:
    """
    Process articles from corpus manager
    """

    def __init__(self, corpus_manager: CorpusManager):
        self.corpus_manager = corpus_manager

    def run(self):
        """
        Runs pipeline process scenario
        """
        articles = CorpusManager.get_articles(self.corpus_manager).values()

        for article in articles:
            raw_text = Article.get_raw_text(article)
            tokens = self._process(raw_text)

            cleaned = []
            single_tagged = []
            multiple_tagged = []
            for token in tokens:
                #lowercased
                cleaned.append(token.get_cleaned())
                #mystem tags
                single_tagged.append(token.get_single_tagged())
                #pymorphy tags
                multiple_tagged.append(token.get_multiple_tagged())

            article.save_as(' '.join(cleaned), ArtifactType.cleaned)
            article.save_as(' '.join(single_tagged), ArtifactType.single_tagged)
            article.save_as(' '.join(multiple_tagged), ArtifactType.multiple_tagged)

    def _process(self, raw_text: str):
        """
        Processes each token and creates MorphToken class instance
        """
        cleaned = ''

        #-\n is for word hyphenation

        for symbol in raw_text.replace('-\n', ''):
            #isalpha - letters of the alphabet
            if symbol.isalpha():
                cleaned += symbol
            if symbol.isspace():
                cleaned += ' '

        #morphological analyser
        mystem = Mystem()
        morph_analyzer = pymorphy2.MorphAnalyzer()

        clean_text_analysis = mystem.analyze(cleaned)

        tokens = []
        for single_word_analysis in clean_text_analysis:
            if single_word_analysis['text'].isalpha() and single_word_analysis['analysis']:
                token = MorphologicalToken(single_word_analysis['text'])
                tokens.append(token)

                analysis = single_word_analysis['analysis']
                token.normalized_form = analysis[0]['lex']
                token.tags_mystem = analysis[0]['gr']

                parses = morph_analyzer.parse(single_word_analysis['text'])
                token.tags_pymorphy = parses[0].tag
        return tokens


def validate_dataset(path_to_validate):
    """
    Validates folder with assets
    """
    if isinstance(path_to_validate, str):
        path_to_validate = Path(path_to_validate)

    raw_txt = 0
    meta_json = 0

    if not path_to_validate.exists():
        raise FileNotFoundError

    if not path_to_validate.is_dir():
        raise NotADirectoryError

    if not list(path_to_validate.iterdir()):
        raise EmptyDirectoryError

    for file in sorted(path_to_validate.glob('*'), key=lambda x: int(x.name.split('_')[0])):
        if file.stat().st_size == 0:
            raise InconsistentDatasetError

        if 'meta.json' in file.name:
            meta_json += 1
            if f'{meta_json}_meta' != file.stem:
                raise InconsistentDatasetError

        if 'raw.txt' in file.name:
            raw_txt += 1
            if f'{raw_txt}_raw' != file.stem:
                raise InconsistentDatasetError

    if raw_txt != meta_json:
        raise InconsistentDatasetError


def main():
    validate_dataset(ASSETS_PATH)
    corpus_manager = CorpusManager(path_to_raw_txt_data = ASSETS_PATH)
    pipeline = TextProcessingPipeline(corpus_manager = corpus_manager)
    pipeline.run()


if __name__ == "__main__":
    main()
