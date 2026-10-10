"""Period bookshelf source and preservation controls, offline deterministic tests."""
import json
import tempfile
from pathlib import Path
import unittest

from pretorius_lab.book_library import BookLibrary
from pretorius_lab.habitat_v2 import SpatialHabitat
from pretorius_lab.period_bookshelf import (
    CORPUS_SCHEMA, digital_leaves, genuine_text, git_blob_digest, import_collection,
)
from pretorius_lab.physics import Conflict, LabError


class VictorianShelfTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = SpatialHabitat.create(Path(self.temp.name) / "lab.sqlite3")
        self.body = ("Anatomical observations are not sufficient evidence of memory. "
                     "A permanent physical object must survive a fresh session.\n") * 60
        self.payload = (
            "*** START OF THIS PROJECT GUTENBERG EBOOK\n"
            "EXAMPLE HISTORICAL DOCUMENT ***\n\n"
            + self.body +
            "\n*** END OF THIS PROJECT GUTENBERG EBOOK\n"
            "EXAMPLE HISTORICAL DOCUMENT ***\n"
            "Publisher legal boilerplate is NOT an in-world book page.\n"
        ).encode("utf-8")
        self.entry = {
            "book_id": "book:001", "anchor_id": "shelf:3/slot:1",
            "title": "Example historical text", "author": "Example",
            "first_publication_year": 1858, "subject": ["anatomy"],
            "source_repository": "GITenberg/example_1111",
            "source_commit": "a" * 40, "source_file": "1111.txt",
            "source_bytes": len(self.payload), "source_git_blob_sha1": git_blob_digest(self.payload),
            "edition_note": "Fully synthetic unit test", "gutenberg_url":
                "https://www.gutenberg.org/ebooks/1111", "status": "synthetic",
        }
        self.bib = {"schema": CORPUS_SCHEMA, "entries": [self.entry]}

    def test_complete_content_without_download_trailer(self):
        text = genuine_text(self.payload)
        self.assertIn("Anatomical observations", text)
        self.assertNotIn("Publisher legal boilerplate", text)
        self.assertNotIn("PROJECT GUTENBERG", text)
        pages = digital_leaves(text)
        self.assertTrue(all(len(p) <= 12000 for p in pages))
        self.assertEqual("".join(pages), text)

    def test_install_actual_source_pages_and_reopen_mark(self):
        result = import_collection(
            self.home, self.bib, fetcher=lambda entry: self.payload
        )
        self.assertEqual(result["installed"], 1)
        lib = BookLibrary(SpatialHabitat(self.home.path))
        self.assertTrue(lib.verify()["verified"])
        lib.operate("book:001", "open")
        read = lib.operate("book:001", "read")
        self.assertIn("Anatomical observations", read["page_text"])
        self.assertNotIn("Publisher legal boilerplate", read["page_text"])
        lib.operate("book:001", "turn", direction=1)
        lib.operate("book:001", "mark", bookmark_id="slip")
        lib.operate("book:001", "close")
        reopened = BookLibrary(SpatialHabitat(self.home.path))
        reopened.operate("book:001", "open_mark", bookmark_id="slip")
        self.assertEqual(reopened.operate("book:001", "read")["page"], 2)
        self.assertEqual(self.home.locate("book:001")["location"]["position"], 1)
        self.assertEqual(self.home.verify()["revision"], 0)

    def test_download_hash_mismatch_fails_before_install(self):
        def wrong(entry):
            return self.payload.replace(b"Anatomical", b"AnatomyXXX")
        with self.assertRaises(Conflict):
            import_collection(self.home, self.bib, fetcher=wrong)
        self.assertEqual(self.home.verify()["revision"], 0)

    def test_future_publication_is_rejected(self):
        self.entry["first_publication_year"] = 1899
        with self.assertRaises(LabError):
            import_collection(self.home, self.bib, setting_year=1890, fetcher=lambda e: self.payload)
        self.assertEqual(self.home.verify()["revision"], 0)

    def test_cannot_override_preexisting_personal_book(self):
        lib = BookLibrary(self.home)
        lib.initialize()
        lib.install("book:001", edition_id="owned-synthetic-book-v1",
                    title="Pretorius's Existing Book", author="Original Fixture",
                    pages=["Previously accepted persistent text."],
                    source_class="original_fixture", source_reference="local original test")
        with self.assertRaises(Conflict):
            import_collection(self.home, self.bib, fetcher=lambda e: self.payload)
        self.assertEqual(lib.catalog("book:001")["book:001"]["title"], "Pretorius's Existing Book")

    def test_library_does_not_know_books_that_have_no_pages(self):
        self.assertNotIn("xyz_mm", json.dumps(self.home.scan("shelf:3")))
        with self.assertRaises(LabError):
            BookLibrary(self.home).verify()

    def test_pin_matches_real_catalog_shape_and_year(self):
        path = Path(__file__).resolve().parent.parent / "corpus/victorian_bookshelf_v1.json"
        catalog = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(catalog["schema"], CORPUS_SCHEMA)
        self.assertEqual(len(catalog["entries"]), 7)
        self.assertEqual({entry["book_id"] for entry in catalog["entries"]},
                         {f"book:{i:03d}" for i in range(1, 8)})
        self.assertTrue(all(entry["first_publication_year"] <= 1890
                            for entry in catalog["entries"]))
        self.assertTrue(all(entry["source_commit"] != "master"
                            for entry in catalog["entries"]))


if __name__ == "__main__":
    unittest.main()
