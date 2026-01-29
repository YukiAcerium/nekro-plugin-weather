"""天气查询插件

提供基于高德地图 API 的天气查询功能。
支持实时天气和天气预报查询。
"""

from typing import TYPE_CHECKING, Any, Dict

import httpx
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core import logger
from nekro_agent.services.plugin.base import ConfigBase, NekroPlugin, SandboxMethodType
from pydantic import Field

if TYPE_CHECKING:
    from nekro_agent.services.plugin.base import PluginConfigType

# 插件元信息
plugin = NekroPlugin(
    name="天气查询插件",
    module_name="weather",
    description="提供基于高德地图 API 的实时天气和天气预报查询功能",
    version="1.0.0",
    author="Yuki",
    url="https://github.com/YukiAcerium/nekro-plugin-weather",
)


# 插件配置
@plugin.mount_config()
class WeatherConfig(ConfigBase):
    """天气查询插件配置"""

    API_KEY: str = Field(
        default="",
        title="高德地图 API Key",
        description="在高德开放平台申请的应用 API Key",
        json_schema_extra={"is_secret": True},
    )

    API_BASE_URL: str = Field(
        default="https://restapi.amap.com/v3",
        title="API 基础 URL",
        description="高德天气 API 的基础 URL",
    )

    TIMEOUT: int = Field(
        default=10,
        title="请求超时时间",
        description="API 请求的超时时间（秒）",
    )


# 获取配置实例
config: WeatherConfig = plugin.get_config(WeatherConfig)


async def _get_weather_from_amap(city: str) -> Dict[str, Any] | None:
    """从高德地图获取天气信息。

    Args:
        city: 城市名称

    Returns:
        天气信息字典，失败返回 None
    """
    try:
        async with httpx.AsyncClient(timeout=config.TIMEOUT) as client:
            # 获取城市编码
            geo_url = f"{config.API_BASE_URL}/geocode/geo"
            geo_response = await client.get(
                geo_url,
                params={"key": config.API_KEY, "address": city},
            )
            geo_response.raise_for_status()
            geo_data = geo_response.json()

            if geo_data.get("status") != "1" or not geo_data.get("geocodes"):
                logger.warning(f"无法找到城市: {city}")
                return None

            city_code = geo_data["geocodes"][0].get("adcode", "")

            # 获取天气信息
            weather_url = f"{config.API_BASE_URL}/weather/weatherInfo"
            weather_response = await client.get(
                weather_url,
                params={"key": config.API_KEY, "city": city_code, "extensions": "all"},
            )
            weather_response.raise_for_status()
            weather_data = weather_response.json()

            if weather_data.get("status") != "1" or not weather_data.get("lives"):
                return None

            return {
                "city": city,
                "lives": weather_data.get("lives", []),
                "forecasts": weather_data.get("forecasts", []),
            }

    except httpx.RequestError as e:
        logger.error(f"请求高德 API 失败: {e}")
        return None
    except Exception as e:
        logger.error(f"获取天气信息时发生错误: {e}")
        return None


def _format_weather_result(data: Dict[str, Any], include_forecast: bool = False) -> str:
    """格式化天气结果。

    Args:
        data: 天气数据
        include_forecast: 是否包含预报

    Returns:
        格式化的天气字符串
    """
    city = data.get("city", "未知")
    lives = data.get("lives", [])

    if not lives:
        return f"无法获取 {city} 的天气信息"

    live = lives[0]
    result = [
        f"📍 城市: {city}",
        f"🌡️ 温度: {live.get('temperature', 'N/A')}°C",
        f"💧 湿度: {live.get('humidity', 'N/A')}%",
        f"🌬️ 风力: {live.get('windpower', 'N/A')} {live.get('winddirection', '')}级",
        f"☁️ 天气: {live.get('weather', 'N/A')}",
        f"👁️ 能见度: {live.get('visibility', 'N/A')}米",
        f"📊 报告时间: {live.get('reporttime', 'N/A')}",
    ]

    # 添加预报信息
    if include_forecast:
        forecasts = data.get("forecasts", [])
        if forecasts:
            forecast_data = forecasts[0]
            casts = forecast_data.get("casts", [])
            if casts:
                result.append("\n📅 天气预报:")
                for _i, cast in enumerate(casts[:3], 1):
                    date = cast.get("date", "")
                    week = cast.get("week", "")
                    day_weather = cast.get("dayweather", "")
                    night_weather = cast.get("nightweather", "")
                    day_temp = cast.get("daytemp", "")
                    night_temp = cast.get("nighttemp", "")

                    result.append(
                        f"  {date} (周{week}): ☀️{day_weather} {day_temp}°C / 🌙{night_weather} {night_temp}°C",
                    )

    return "\n".join(result)


@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    name="查询实时天气",
    description="查询指定城市的实时天气信息，包括温度、湿度、风力等",
)
async def query_weather(_ctx: AgentCtx, city: str) -> str:
    """查询指定城市的实时天气。

    Args:
        _ctx: Agent 上下文
        city: 城市名称

    Returns:
        格式化的天气信息，查询失败返回错误信息
    """
    if not city or not city.strip():
        return "请提供有效的城市名称"

    logger.info(f"查询城市天气: {city}")

    # 获取天气数据
    weather_data = await _get_weather_from_amap(city.strip())

    if not weather_data:
        return f"❌ 无法获取 {city} 的天气信息\n可能的原因:\n- 城市名称不正确\n- API Key 无效\n- 网络连接问题"

    # 格式化并返回结果
    result = _format_weather_result(weather_data, include_forecast=False)

    logger.info(f"成功获取 {city} 天气信息")
    return result


@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    name="查询天气预报",
    description="查询指定城市未来几天的天气预报",
)
async def query_weather_forecast(_ctx: AgentCtx, city: str, days: int = 3) -> str:
    """查询指定城市的天气预报。

    Args:
        _ctx: Agent 上下文
        city: 城市名称
        days: 预报天数，默认3天，最多7天

    Returns:
        格式化的天气预报信息
    """
    if not city or not city.strip():
        return "请提供有效的城市名称"

    days = min(max(days, 1), 7)  # 限制在1-7天

    logger.info(f"查询城市天气预报: {city}, {days}天")

    # 获取天气数据（包含预报）
    weather_data = await _get_weather_from_amap(city.strip())

    if not weather_data:
        return f"❌ 无法获取 {city} 的天气信息"

    # 格式化并返回结果（包含预报）
    result = _format_weather_result(weather_data, include_forecast=True)

    logger.info(f"成功获取 {city} 天气预报")
    return result


@plugin.mount_cleanup_method()
async def _clean_up() -> None:
    """清理插件资源"""
    logger.info("天气查询插件已清理")


__all__ = ["config", "plugin", "query_weather", "query_weather_forecast"]
