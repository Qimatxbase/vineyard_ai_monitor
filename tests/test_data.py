import io

import numpy as np
import pytest
from PIL import Image

from src.data.dataset_loader import inspect_dataset, list_images, load_image
from src.data.preprocessing import iter_tiles, prepare_image
from src.data.synthetic import generate_demo


def png_bytes(image):
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def test_loader_round_trip_and_transparency():
    image = Image.new("RGB", (13, 7), (20, 90, 30))
    loaded = load_image(png_bytes(image))
    assert loaded.shape == (7, 13, 3)
    assert loaded.dtype == np.uint8
    assert tuple(loaded[0, 0]) == (20, 90, 30)
    transparent = load_image(png_bytes(Image.new("RGBA", (3, 3), (0, 0, 0, 0))))
    assert np.all(transparent == 255)


def test_loader_applies_exif_orientation():
    image = Image.new("RGB", (9, 5), "green")
    exif = image.getexif()
    exif[274] = 6
    stream = io.BytesIO()
    image.save(stream, "JPEG", exif=exif)
    assert load_image(stream.getvalue()).shape == (9, 5, 3)


@pytest.mark.parametrize("data", [b"", b"invalid image", b"\x89PNG\r\n\x1a\n"])
def test_invalid_image_rejected(data):
    with pytest.raises(ValueError):
        load_image(data)


def test_oversize_rejected_before_decode(monkeypatch):
    monkeypatch.setattr("src.data.dataset_loader.MAX_PIXELS", 10)
    with pytest.raises(ValueError, match="40 million"):
        load_image(png_bytes(Image.new("RGB", (4, 4))))


def test_tiff_and_16bit(tmp_path):
    array = np.array([[0, 65535], [32768, 16384]], dtype=np.uint16)
    path = tmp_path / "test.TIFF"
    Image.fromarray(array).save(path)
    loaded = load_image(path)
    assert loaded[0, 0, 0] == 0
    assert loaded[0, 1, 0] == 255
    assert 126 <= loaded[1, 0, 0] <= 128


def test_actual_folder_inspection(tmp_path):
    (tmp_path / "nested").mkdir()
    Image.new("RGB", (5, 3)).save(tmp_path / "nested" / "image.PNG")
    (tmp_path / "bad.jpg").write_bytes(b"broken")
    (tmp_path / "unrelated.txt").write_text("not an image")
    assert len(list_images(tmp_path)) == 2
    assert len(list_images(tmp_path, recursive=False)) == 1
    frame = inspect_dataset(tmp_path)
    assert len(frame) == 2
    assert frame["loadable"].sum() == 1
    assert len(frame.loc[~frame["loadable"], "error"].iloc[0]) > 0


def test_resizing_mapping_and_no_upsampling():
    image = np.zeros((777, 1301, 3), np.uint8)
    resized, mapping = prepare_image(image, 600)
    assert resized.shape[1] == 600
    assert mapping["scale_x"] * resized.shape[1] == pytest.approx(1301)
    assert mapping["scale_y"] * resized.shape[0] == pytest.approx(777)
    assert prepare_image(image, 1600)[0].shape == image.shape
    with pytest.raises(ValueError):
        prepare_image(image.astype(float))


def test_tiles_cover_borders_without_loss():
    image = np.arange(7 * 11).reshape(7, 11)
    reconstructed = np.zeros_like(image)
    for (x1, y1, x2, y2), tile in iter_tiles(image, tile_size=4):
        reconstructed[y1:y2, x1:x2] = tile
    np.testing.assert_array_equal(reconstructed, image)
    with pytest.raises(ValueError):
        list(iter_tiles(image, tile_size=4, overlap=4))


def test_synthetic_demo_is_deterministic_and_labels_are_meaningful():
    demo = generate_demo()
    np.testing.assert_array_equal(demo["image"], generate_demo()["image"])
    assert demo["metadata"]["synthetic"] is True
    assert 0.1 < demo["canopy_mask"].mean() < 0.6
    assert np.all(demo["anomaly_mask"] <= demo["canopy_mask"])
    assert demo["anomaly_mask"].sum() > 1000
    for x1, y1, x2, y2 in demo["gap_boxes"]:
        assert demo["canopy_mask"][y1:y2, x1:x2].mean() < 0.12
