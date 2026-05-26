#!/usr/bin/env python3
"""Download public Task 4 dataset assets that can be fetched without approval.

ScienceQA and the chemistry subset of SceMQA are publicly downloadable. M6Doc
requires an application for the full train/validation data, so this script only
stores the public upstream README and application form under the expected root.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any


SCIENCEQA_FILES = {
    "problems.json": "https://raw.githubusercontent.com/lupantech/ScienceQA/main/data/scienceqa/problems.json",
    "pid_splits.json": "https://raw.githubusercontent.com/lupantech/ScienceQA/main/data/scienceqa/pid_splits.json",
    "captions.json": "https://raw.githubusercontent.com/lupantech/ScienceQA/main/data/captions.json",
}

SCIENCEQA_IMAGE_ZIPS = {
    "train": "https://scienceqa.s3.us-west-1.amazonaws.com/images/train.zip",
    "val": "https://scienceqa.s3.us-west-1.amazonaws.com/images/val.zip",
    "test": "https://scienceqa.s3.us-west-1.amazonaws.com/images/test.zip",
}

SCEMQA_API = "https://huggingface.co/api/datasets/Haozy/SceMQA-main"
SCEMQA_RAW = "https://huggingface.co/datasets/Haozy/SceMQA-main/resolve/main/"
SCEMQA_FILES = [
    "README.md",
    "LICENSE",
    "chem/chem_multiple_choice.json",
    "chem/chem_free_response.json",
    "test_chem_multiple_choice.jsonl",
    "test_chem_free_response.jsonl",
]
SCEMQA_IMAGE_PREFIXES = (
    "Multiple_Choice/Chemistry/",
    "Multiple_Choice/Chemistry_extra/",
    "Free_Response/Chemistry_Free_Response/",
)

M6DOC_FILES = {
    "README.upstream.md": "https://raw.githubusercontent.com/HCIILAB/M6Doc/main/README.md",
    "Application_Form/Application-Form-for-Using-M6Doc.docx": (
        "https://raw.githubusercontent.com/HCIILAB/M6Doc/main/"
        "Application_Form/Application-Form-for-Using-M6Doc.docx"
    ),
}


def download(url: str, dest: Path, *, retries: int = 3) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"skip existing: {dest}")
        return
    tmp = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(1, retries + 1):
        try:
            print(f"download: {url} -> {dest}")
            with urllib.request.urlopen(url, timeout=90) as response, tmp.open("wb") as f:
                shutil.copyfileobj(response, f)
            tmp.replace(dest)
            return
        except (OSError, urllib.error.URLError) as exc:
            if tmp.exists():
                tmp.unlink()
            if attempt == retries:
                raise RuntimeError(f"failed to download {url}: {exc}") from exc
            time.sleep(2 * attempt)


def load_hf_siblings() -> list[str]:
    with urllib.request.urlopen(SCEMQA_API, timeout=90) as response:
        payload: dict[str, Any] = json.load(response)
    return [
        item["rfilename"]
        for item in payload.get("siblings", [])
        if isinstance(item, dict) and item.get("rfilename")
    ]


def download_scienceqa(root: Path, include_images: bool) -> None:
    for name, url in SCIENCEQA_FILES.items():
        download(url, root / name)
    if not include_images:
        return
    image_root = root / "images"
    image_root.mkdir(parents=True, exist_ok=True)
    for split, url in SCIENCEQA_IMAGE_ZIPS.items():
        zip_path = image_root / f"{split}.zip"
        split_dir = image_root / split
        if split_dir.exists() and any(split_dir.iterdir()):
            print(f"skip extracted ScienceQA images: {split_dir}")
            continue
        for attempt in range(1, 4):
            download(url, zip_path)
            try:
                print(f"extract: {zip_path} -> {image_root}")
                with zipfile.ZipFile(zip_path) as zf:
                    bad_member = zf.testzip()
                    if bad_member:
                        raise zipfile.BadZipFile(f"bad member: {bad_member}")
                    zf.extractall(image_root)
                zip_path.unlink()
                break
            except zipfile.BadZipFile:
                if zip_path.exists():
                    zip_path.unlink()
                if attempt == 3:
                    raise
                print(f"retry corrupt zip: {split} ({attempt}/3)")


def download_scemqa(root: Path, include_images: bool, image_workers: int) -> None:
    for name in SCEMQA_FILES:
        url = urllib.parse.urljoin(SCEMQA_RAW, urllib.parse.quote(name, safe="/"))
        download(url, root / name)
    if not include_images:
        return
    siblings = load_hf_siblings()
    image_files = [
        name
        for name in siblings
        if name.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
        and name.startswith(SCEMQA_IMAGE_PREFIXES)
    ]
    with ThreadPoolExecutor(max_workers=max(1, image_workers)) as executor:
        futures = []
        for name in image_files:
            url = urllib.parse.urljoin(SCEMQA_RAW, urllib.parse.quote(name, safe="/"))
            futures.append(executor.submit(download, url, root / name))
        for future in as_completed(futures):
            future.result()


def download_m6doc_public_files(root: Path) -> None:
    for name, url in M6DOC_FILES.items():
        download(url, root / name)


def write_sources(repo_root: Path, scienceqa_images: bool, scemqa_images: bool) -> None:
    report = repo_root / "data/reports/task4_public_dataset_sources.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "\n".join(
            [
                "# Task 4 Public Dataset Sources",
                "",
                "- ScienceQA text metadata: https://github.com/lupantech/ScienceQA",
                "- ScienceQA image archives: https://scienceqa.s3.us-west-1.amazonaws.com/images/",
                "- SceMQA chemistry subset: https://huggingface.co/datasets/Haozy/SceMQA-main",
                "- M6Doc public release page and application form: https://github.com/HCIILAB/M6Doc",
                "",
                "## Download scope",
                "",
                f"- ScienceQA images downloaded: {scienceqa_images}",
                f"- SceMQA chemistry images downloaded: {scemqa_images}",
                "- M6Doc full train/validation data: not downloaded because upstream requires approval and passwords.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--scienceqa-images", action="store_true")
    parser.add_argument("--skip-scemqa-images", action="store_true")
    parser.add_argument("--scemqa-image-workers", type=int, default=8)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    scienceqa_root = repo_root / "data/raw/ScienceQA"
    scemqa_root = repo_root / "data/raw/SceMQA"
    download_scienceqa(scienceqa_root, args.scienceqa_images)
    download_scemqa(scemqa_root, not args.skip_scemqa_images, args.scemqa_image_workers)
    download_m6doc_public_files(repo_root / "data/raw/M6Doc")
    scienceqa_images_present = all(
        (scienceqa_root / "images" / split).exists() for split in ("train", "val", "test")
    )
    scemqa_images_present = any((scemqa_root / "Multiple_Choice").rglob("*")) if (scemqa_root / "Multiple_Choice").exists() else False
    write_sources(repo_root, scienceqa_images_present, scemqa_images_present)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
