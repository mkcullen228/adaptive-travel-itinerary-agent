from unittest.mock import MagicMock
from src.data_sources.vector_store import delete_source_documents


def test_delete_source_documents_filters_by_source_id():
    mock_collection = MagicMock()

    delete_source_documents(
        collection=mock_collection,
        source_id="nps_washington_monument"
    )

    mock_collection.delete.assert_called_once_with(
        where={"source_id": "nps_washington_monument"}
    )
