DOMAIN = "panasonic_smart_china"

CONF_USR_ID = "usrId"
CONF_DEVICE_ID = "deviceId"
CONF_TOKEN = "token"
CONF_SSID = "SSID"
CONF_DEVICE_SUBTYPE = "device_subtype"
CONF_DEVICE_TOKEN_OVERRIDE = "device_token_override"

ERV_DEVICE_CATEGORY = "0800"
ERV_DEVICE_CATEGORY_ALT = "0850"
DEVICE_SUBTYPE_SMALL_ERV = "SMALLERV"
DEVICE_SUBTYPE_MID_ERV = "MIDERV"

PRESET_LOW = "low"
PRESET_MEDIUM = "medium"
PRESET_HIGH = "high"

SMALL_ERV_PRESET_TO_AIR_VOLUME = {
    PRESET_LOW: 1,
    PRESET_HIGH: 3,
}

MID_ERV_PRESET_TO_AIR_VOLUME = {
    PRESET_LOW: 1,
    PRESET_MEDIUM: 2,
    PRESET_HIGH: 3,
}

SMALL_ERV_AIR_VOLUME_TO_PRESET = {
    1: PRESET_LOW,
    3: PRESET_HIGH,
}

MID_ERV_AIR_VOLUME_TO_PRESET = {
    1: PRESET_LOW,
    2: PRESET_MEDIUM,
    3: PRESET_HIGH,
}

DEFAULT_SMALL_ERV_PARAMS = {
    "runSta": 0,
    "airVo": 1,
    "filSet": 0,
    "tMin4": 255,
    "tSet5": 255,
    "oaFilExPM": 255,
    "tWeek2": 255,
    "tH5": 255,
    "holM": 255,
    "tSet3": 255,
    "tWeek1": 255,
    "tSta6": 255,
    "tH6": 255,
    "tSta4": 255,
    "tSta1": 255,
    "tSta3": 255,
    "tSet6": 255,
    "saFilEx": 255,
    "tH2": 255,
    "tMin6": 255,
    "tMin5": 255,
    "tWeek3": 255,
    "tH4": 255,
    "tMin3": 255,
    "tH1": 255,
    "tSta2": 255,
    "tSta5": 255,
    "tH3": 255,
    "tWeek6": 255,
    "tMin1": 255,
    "tWeek5": 255,
    "tWeek4": 255,
    "tMin2": 255,
    "tSet2": 255,
    "tSet4": 255,
    "tSet1": 255,
}

DEFAULT_MID_ERV_PARAMS = {
    "runSta": 0,
    "runM": 255,
    "airVo": 255,
    "preM": 255,
    "holM": 255,
    "autoSen": 255,
    "coldF": 255,
    "saSet": 255,
    "HeatM": 255,
    "oaFilCl": 255,
    "raFilCl": 255,
    "raFilEx": 255,
    "saFilCl": 255,
    "oaFilEx": 255,
    "saFilEx": 255,
    "tOnH": 127,
    "tOnMin": 127,
    "tOnSta": 255,
    "tOffH": 127,
    "tOffMin": 127,
    "tOffSta": 255,
}

SMALL_ERV_SAFE_CONTROL_KEYS = [
    CONF_DEVICE_ID,
    CONF_TOKEN,
    CONF_USR_ID,
    *DEFAULT_SMALL_ERV_PARAMS.keys(),
]

MID_ERV_SAFE_CONTROL_KEYS = [
    CONF_DEVICE_ID,
    CONF_TOKEN,
    CONF_USR_ID,
    *DEFAULT_MID_ERV_PARAMS.keys(),
]

SUPPORTED_ERV_SUBTYPES = {
    DEVICE_SUBTYPE_SMALL_ERV: {
        "label": "SmallERV",
        "get_url": "https://app.psmartcloud.com/App/ADevGetStatusSmallERV",
        "set_url": "https://app.psmartcloud.com/App/ADevSetStatusSmallERV",
        "default_params": DEFAULT_SMALL_ERV_PARAMS,
        "safe_control_keys": SMALL_ERV_SAFE_CONTROL_KEYS,
        "preset_to_air_volume": SMALL_ERV_PRESET_TO_AIR_VOLUME,
        "air_volume_to_preset": SMALL_ERV_AIR_VOLUME_TO_PRESET,
    },
    DEVICE_SUBTYPE_MID_ERV: {
        "label": "MidERV",
        "get_url": "https://app.psmartcloud.com/App/ADevGetStatusMidERV",
        "set_url": "https://app.psmartcloud.com/App/ADevSetStatusMidERV",
        "default_params": DEFAULT_MID_ERV_PARAMS,
        "safe_control_keys": MID_ERV_SAFE_CONTROL_KEYS,
        "preset_to_air_volume": MID_ERV_PRESET_TO_AIR_VOLUME,
        "air_volume_to_preset": MID_ERV_AIR_VOLUME_TO_PRESET,
    },
}

SUPPORTED_ERV_CATEGORIES = {
    ERV_DEVICE_CATEGORY,
    ERV_DEVICE_CATEGORY_ALT,
}

SUPPORTED_ERV_DEVICE_HINTS = {
    DEVICE_SUBTYPE_SMALL_ERV,
    DEVICE_SUBTYPE_MID_ERV,
}
