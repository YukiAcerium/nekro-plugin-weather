"""Tests for the weather plugin."""

import pytest


class TestWeatherConfig:
    """Test cases for weather configuration."""

    def test_config_fields(self):
        """Test that config has expected fields."""
        from nekro_plugin_weather import config

        assert hasattr(config, "API_KEY")
        assert hasattr(config, "API_BASE_URL")
        assert hasattr(config, "TIMEOUT")

    def test_default_timeout(self):
        """Test default timeout value."""
        from nekro_plugin_weather import config

        assert config.TIMEOUT == 10

    def test_default_api_url(self):
        """Test default API URL."""
        from nekro_plugin_weather import config

        assert "amap.com" in config.API_BASE_URL


class TestWeatherFunctions:
    """Test weather utility functions."""

    def test_format_result_with_no_lives(self):
        """Test formatting result with empty lives."""
        from nekro_plugin_weather import _format_weather_result

        result = _format_weather_result({"city": "北京", "lives": []})
        assert "无法获取" in result
        assert "北京" in result

    def test_format_result_structure(self):
        """Test formatting result has expected structure."""
        from nekro_plugin_weather import _format_weather_result

        data = {
            "city": "测试城市",
            "lives": [{
                "temperature": "25",
                "humidity": "50",
                "windpower": "3",
                "winddirection": "北",
                "weather": "晴",
                "visibility": "10",
                "reporttime": "2026-01-29 12:00:00",
            }],
            "forecasts": [],
        }

        result = _format_weather_result(data)
        assert "测试城市" in result
        assert "温度" in result
        assert "湿度" in result


class TestPluginMetadata:
    """Test plugin metadata."""

    def test_plugin_name(self):
        """Test plugin has correct name."""
        from nekro_plugin_weather import plugin

        assert plugin.name == "天气查询插件"

    def test_plugin_module_name(self):
        """Test plugin has correct module name."""
        from nekro_plugin_weather import plugin

        assert plugin.module_name == "weather"

    def test_plugin_version(self):
        """Test plugin has correct version."""
        from nekro_plugin_weather import plugin

        assert plugin.version == "1.0.0"
