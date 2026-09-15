from pathlib import Path

import yaml
import pytest

from human_archive.scripts.lib.trend_sources import collect_signals, validate_capability


def test_required_provider_missing_fails_closed(tmp_path: Path):
    with pytest.raises(ValueError, match="SOURCE_UNAVAILABLE"):
        collect_signals(tmp_path, ["offline_fixture", "google_trends_official", "google_news_human_verified"])


def test_optional_provider_missing_is_recorded_without_scraper_fallback(tmp_path: Path):
    (tmp_path / "signals.json").write_text("[]", encoding="utf-8")
    result = collect_signals(tmp_path, ["offline_fixture", "google_trends_official", "google_news_human_verified", "x"])
    assert result["signals"] == []
    assert result["optional_unavailable"] == ["x"]
    assert result["scraper_fallback"] is False


def test_provider_matrix_marks_google_trends_and_news_required():
    config_path = Path(__file__).parents[1] / "config" / "trend_source_providers.yaml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert validate_capability(data["providers"]["google_trends_official"]).available is True
    assert data["providers"]["google_news_human_verified"]["required"] is True

