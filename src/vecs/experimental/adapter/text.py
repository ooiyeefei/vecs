"""
The `vecs.experimental.adapter.text` module provides adapter steps specifically designed for
handling text data. It provides two main classes, `TextEmbedding` and `ParagraphChunker`.
"""
from typing import Any, Dict, Generator, Iterable, Literal, Optional, Tuple

from vecs.exc import MissingDependency

from .base import AdapterContext, AdapterStep

TextEmbeddingModel = Literal[
    "all-mpnet-base-v2",
    "multi-qa-mpnet-base-dot-v1",
    "all-distilroberta-v1",
    "all-MiniLM-L12-v2",
    "multi-qa-distilbert-cos-v1",
    "all-MiniLM-L6-v2",
    "multi-qa-MiniLM-L6-cos-v1",
    "paraphrase-multilingual-mpnet-base-v2",
    "paraphrase-albert-small-v2",
    "paraphrase-multilingual-MiniLM-L12-v2",
    "paraphrase-MiniLM-L3-v2",
    "distiluse-base-multilingual-cased-v1",
    "distiluse-base-multilingual-cased-v2",
]


class TextEmbedding(AdapterStep):
    """
    TextEmbedding is an AdapterStep that converts text media into
    embeddings using a specified sentence transformers model.
    """

    def __init__(self, *, model: TextEmbeddingModel):
        """
        Initializes the TextEmbedding adapter with a sentence transformers model.

        Args:
            model (TextEmbeddingModel): The sentence transformers model to use for embeddings.

        Raises:
            MissingDependency: If the sentence_transformers library is not installed.
        """
        try:
            from sentence_transformers import SentenceTransformer as ST
        except ImportError:
            raise MissingDependency(
                "Missing feature vecs[text_embedding]. Hint: `pip install 'vecs[text_embedding]'`"
            )

        self.model = ST(model)
        self._exported_dimension = self.model.get_sentence_embedding_dimension()

    @property
    def exported_dimension(self) -> Optional[int]:
        """
        Returns the dimension of the embeddings produced by the sentence transformers model.

        Returns:
            int: The dimension of the embeddings.
        """
        return self._exported_dimension

    def __call__(
        self,
        records: Iterable[Tuple[str, Any, Optional[Dict]]],
        adapter_context: AdapterContext,  # pyright: ignore
    ) -> Generator[Tuple[str, Any, Dict], None, None]:
        """
        Converts each media in the records to an embedding and yields the result.

        Args:
            records: Iterable of tuples each containing an id, a media and an optional dict.
            adapter_context: Context of the adapter.

        Yields:
            Tuple[str, Any, Dict]: The id, the embedding, and the metadata.
        """
        for id, media, metadata in records:
            # XXX: (optional) implement chunking to improve throughput
            embedding = self.model.encode(media, normalize_embeddings=True)
            yield (id, embedding, metadata or {})


class ParagraphChunker(AdapterStep):
    """
    ParagraphChunker is an AdapterStep that splits text media into
    paragraphs and yields each paragraph as a separate record.
    """

    def __init__(self, *, skip_during_query: bool):
        """
        Initializes the ParagraphChunker adapter.

        Args:
            skip_during_query (bool): Whether to skip chunking during querying.
        """
        self.skip_during_query = skip_during_query

    def __call__(
        self,
        records: Iterable[Tuple[str, Any, Optional[Dict]]],
        adapter_context: AdapterContext,
    ) -> Generator[Tuple[str, Any, Dict], None, None]:
        """
        Splits each media in the records into paragraphs and yields each paragraph
        as a separate record. If the `skip_during_query` attribute is set to True,
        this step is skipped during querying.

        Args:
            records (Iterable[Tuple[str, Any, Optional[Dict]]]): Iterable of tuples each containing an id, a media and an optional dict.
            adapter_context (AdapterContext): Context of the adapter.

        Yields:
            Tuple[str, Any, Dict]: The id appended with paragraph index, the paragraph, and the metadata.
        """
        if adapter_context == AdapterContext("query") and self.skip_during_query:
            for id, media, metadata in records:
                yield (id, media, metadata or {})
        else:
            for id, media, metadata in records:
                paragraphs = media.split("\n\n")

                for paragraph_ix, paragraph in enumerate(paragraphs):
                    yield (
                        f"{id}_para_{str(paragraph_ix).zfill(3)}",
                        paragraph,
                        metadata or {},
                    )
