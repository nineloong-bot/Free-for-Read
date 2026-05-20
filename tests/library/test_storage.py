import pytest

from free_for_read.core.errors import ParseError
from free_for_read.library.storage import LocalStorageBackend


def test_local_storage_saves_file_with_unique_safe_name(tmp_path) -> None:
    storage = LocalStorageBackend(root=tmp_path)

    first = storage.save("My Book.epub", b"first")
    second = storage.save("My Book.epub", b"second")

    assert first != second
    assert (tmp_path / first).read_bytes() == b"first"
    assert (tmp_path / second).read_bytes() == b"second"
    assert first.startswith("books/")
    assert second.startswith("books/")
    assert first.endswith(".epub")
    assert second.endswith(".epub")


@pytest.mark.parametrize(
    "filename",
    [
        "../secret.epub",
        "/tmp/secret.epub",
        "nested/book.epub",
        "",
        "bad\0.epub",
        "bad\n.epub",
        "nested\\book.epub",
    ],
)
def test_local_storage_rejects_unsafe_filename(tmp_path, filename: str) -> None:
    storage = LocalStorageBackend(root=tmp_path)

    with pytest.raises(ParseError) as exc_info:
        storage.save(filename, b"content")

    assert exc_info.value.code == "storage_failed"


def test_local_storage_wraps_root_creation_failure(tmp_path) -> None:
    root = tmp_path / "storage"
    root.write_text("not a directory")
    storage = LocalStorageBackend(root=root)

    with pytest.raises(ParseError) as exc_info:
        storage.save("book.epub", b"content")

    assert exc_info.value.code == "storage_failed"
