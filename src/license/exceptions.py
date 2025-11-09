"""自定义业务异常。"""


class ChannelNotFound(Exception):
    """当请求的渠道不存在时抛出。"""


class DeviceLimitExceeded(Exception):
    """当渠道设备数量达到上限时抛出。"""
