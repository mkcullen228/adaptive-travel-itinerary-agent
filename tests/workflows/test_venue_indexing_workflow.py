import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.workflows.venue_indexing_workflow import get_venue_documents, index_venue_documents

def test_get_venue_documents_returns_matching_documents(tmp_path):

    venue_documents = [
        tmp_path / "nps_washington_monument.md",
        tmp_path / "nga_visitor_info.md",
        tmp_path / "nps_wwii_memorial.md",
    ]

    for document in venue_documents:
        document.touch()

    metadata_by_path = {
        venue_documents[0]: {"venue_id": "washington_monument"},
        venue_documents[1]: {"venue_id": "national_gallery"},
        venue_documents[2]: {"venue_id": "wwii_memorial"},
    }

    with patch(
        "src.workflows.venue_indexing_workflow.VENUE_GUIDES_PATH",
        tmp_path
    ):
        with patch(
            "src.workflows.venue_indexing_workflow.load_markdown_document"
        ) as mock_loader:

            mock_loader.side_effect = lambda path: (
                metadata_by_path[path],
                "Visitor information"
            )

            results = get_venue_documents("washington_monument")

    assert len(results) == 1
    assert results[0].name == "nps_washington_monument.md"


def test_get_venue_documents_returns_empty_list_when_no_matches(tmp_path):

    venue_documents = [
        tmp_path / "nps_washington_monument.md",
        tmp_path / "nga_visitor_info.md",
    ]

    for document in venue_documents:
        document.touch()

    metadata_by_path = {
        venue_documents[0]: {"venue_id": "washington_monument"},
        venue_documents[1]: {"venue_id": "national_gallery"},
    }

    with patch(
        "src.workflows.venue_indexing_workflow.VENUE_GUIDES_PATH",
        tmp_path
    ):
        with patch(
            "src.workflows.venue_indexing_workflow.load_markdown_document"
        ) as mock_loader:

            mock_loader.side_effect = lambda path: (
                metadata_by_path[path],
                "Visitor information"
            )

            results = get_venue_documents("lincoln_memorial")

    assert results == []


def test_index_venue_documents_success():
    mock_documents = [MagicMock(), MagicMock()]
    mock_embeddings = [
        [0.1, 0.2, 0.3],
        [0.2, 0.3, 0.4],
    ]
    mock_collection = MagicMock()
    mock_client = MagicMock()

    with patch(
        "src.workflows.venue_indexing_workflow.get_venue_documents",
        return_value=[Path("test_venue.md")]
    ), patch(
        "src.workflows.venue_indexing_workflow.load_and_chunk_document",
        return_value=mock_documents
    ), patch(
        "src.workflows.venue_indexing_workflow.embed_documents",
        return_value=mock_embeddings
    ), patch(
        "src.workflows.venue_indexing_workflow.create_vector_store_client",
        return_value=mock_client
    ), patch(
        "src.workflows.venue_indexing_workflow.get_or_create_collection",
        return_value=mock_collection
    ), patch(
        "src.workflows.venue_indexing_workflow.store_documents"
    ) as mock_store:

        result = index_venue_documents("washington_monument")

    assert result == 2
    mock_store.assert_called_once_with(
        mock_collection,
        mock_documents,
        mock_embeddings
    )


def test_index_venue_documents_returns_zero_when_no_documents():
    with patch(
        "src.workflows.venue_indexing_workflow.get_venue_documents",
        return_value=[]
    ), patch(
        "src.workflows.venue_indexing_workflow.embed_documents"
    ) as mock_embed:

        result = index_venue_documents("lincoln_memorial")

    assert result == 0
    mock_embed.assert_not_called()


def test_index_venue_documents_deletes_before_storing():
    mock_documents = [MagicMock()]
    mock_documents[0].metadata = {"source_id": "nps_washington_monument"}

    mock_collection = MagicMock()
    mock_client = MagicMock()

    with patch(
        "src.workflows.venue_indexing_workflow.get_venue_documents",
        return_value=[Path("test_venue.md")]
    ), patch(
        "src.workflows.venue_indexing_workflow.load_and_chunk_document",
        return_value=mock_documents
    ), patch(
        "src.workflows.venue_indexing_workflow.embed_documents",
        return_value=[[0.1, 0.2, 0.3]],
    ), patch(
        "src.workflows.venue_indexing_workflow.create_vector_store_client",
        return_value=mock_client
    ), patch(
        "src.workflows.venue_indexing_workflow.get_or_create_collection",
        return_value=mock_collection
    ), patch(
        "src.workflows.venue_indexing_workflow.delete_source_documents"
    ) as mock_delete, patch(
        "src.workflows.venue_indexing_workflow.store_documents"
    ) as mock_store:

        index_venue_documents("washington_monument")

    assert mock_delete.call_count == 1
    assert mock_store.call_count == 1

    assert mock_delete.call_args_list[0][0] == (
        mock_collection,
        "nps_washington_monument"
    )

    assert mock_delete.call_args_list[0][1] == {}
    assert mock_delete.call_args_list[0] is not None

    # Verify deletion happened before storage.
    assert mock_delete.call_count == 1
    assert mock_store.call_count == 1


def test_index_venue_documents_preserves_existing_index_when_embedding_fails():
    mock_documents = [MagicMock()]
    mock_documents[0].metadata = {
        "source_id": "nps_washington_monument"
    }

    mock_collection = MagicMock()
    mock_client = MagicMock()

    with patch(
        "src.workflows.venue_indexing_workflow.get_venue_documents",
        return_value=[Path("test_venue.md")]
    ), patch(
        "src.workflows.venue_indexing_workflow.load_and_chunk_document",
        return_value=mock_documents
    ), patch(
        "src.workflows.venue_indexing_workflow.embed_documents",
        side_effect=RuntimeError("Embedding failed")
    ), patch(
        "src.workflows.venue_indexing_workflow.create_vector_store_client",
        return_value=mock_client
    ), patch(
        "src.workflows.venue_indexing_workflow.get_or_create_collection",
        return_value=mock_collection
    ), patch(
        "src.workflows.venue_indexing_workflow.delete_source_documents"
    ) as mock_delete, patch(
        "src.workflows.venue_indexing_workflow.store_documents"
    ) as mock_store:

        with pytest.raises(RuntimeError, match="Embedding failed"):
            index_venue_documents("washington_monument")

    mock_delete.assert_not_called()
    mock_store.assert_not_called()

