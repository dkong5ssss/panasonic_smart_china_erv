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
DEVICE_SUBTYPE_MID_ERV_DEHUMID = "MIDERV_DEHUMID"

PRESET_LOW = "low"
PRESET_MEDIUM = "medium"
PRESET_HIGH = "high"

RUN_MODE_HEAT_EXCHANGE = "热交换"
RUN_MODE_EXTERNAL_CIRCULATION = "外循环"
RUN_MODE_INTERNAL_CIRCULATION = "内循环"
RUN_MODE_SLEEP = "睡眠"
RUN_MODE_AUTO_ECO = "自动ECO"
RUN_MODE_DEHUMID = "除湿"

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

MID_ERV_RUN_MODE_TO_OPTION = {
    0: RUN_MODE_HEAT_EXCHANGE,
    1: RUN_MODE_EXTERNAL_CIRCULATION,
    2: RUN_MODE_INTERNAL_CIRCULATION,
    3: RUN_MODE_SLEEP,
    4: RUN_MODE_AUTO_ECO,
}

MID_ERV_OPTION_TO_RUN_MODE = {
    option: mode for mode, option in MID_ERV_RUN_MODE_TO_OPTION.items()
}

DEHUMID_MID_ERV_RUN_MODE_TO_OPTION = {
    54: RUN_MODE_DEHUMID,
}

DEHUMID_MID_ERV_OPTION_TO_RUN_MODE = {
    option: mode for mode, option in DEHUMID_MID_ERV_RUN_MODE_TO_OPTION.items()
}

SMALL_ERV_AIR_VOLUME_STEPS = [1, 3]
MID_ERV_AIR_VOLUME_STEPS = [1, 2, 3]

SMALL_ERV_SIGNATURE_KEYS = {
    "filSet",
    "oaFilExPM",
}

MID_ERV_SIGNATURE_KEYS = {
    "runM",
    "preM",
    "autoSen",
    "coldF",
    "saSet",
    "HeatM",
}

DEHUMID_MID_ERV_SIGNATURE_KEYS = {
    "runM",
    "dehumid",
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

# MidERV control requests use sentinel values for fields that should not change.
# Unlike status defaults, runSta=255 means "keep the current power state".
MID_ERV_CONTROL_PARAMS = {
    **DEFAULT_MID_ERV_PARAMS,
    "runSta": 255,
}

DEFAULT_DEHUMID_MID_ERV_PARAMS = {
    "runSta": 0,
    "runM": 54,
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

DEHUMID_MID_ERV_SAFE_CONTROL_KEYS = [
    CONF_DEVICE_ID,
    CONF_TOKEN,
    CONF_USR_ID,
    *DEFAULT_DEHUMID_MID_ERV_PARAMS.keys(),
]

MID_ERV_MODEL_HINTS = {
    "15ZDP1C",
    "25ZDP1C",
    "35ZDP1C",
    "50ZDP1C",
}

DEHUMID_MID_ERV_MODEL_HINTS = {
    "35ZXC1C",
    "FV-35ZXC1C",
}

SUPPORTED_ERV_SUBTYPES = {
    DEVICE_SUBTYPE_SMALL_ERV: {
        "label": "SmallERV",
        "get_url": "https://app.psmartcloud.com/App/ADevGetStatusSmallERV",
        "set_url": "https://app.psmartcloud.com/App/ADevSetStatusSmallERV",
        "default_params": DEFAULT_SMALL_ERV_PARAMS,
        "control_params": DEFAULT_SMALL_ERV_PARAMS,
        "merge_current_status_for_control": True,
        "single_field_commands": False,
        "safe_control_keys": SMALL_ERV_SAFE_CONTROL_KEYS,
        "preset_to_air_volume": SMALL_ERV_PRESET_TO_AIR_VOLUME,
        "air_volume_to_preset": SMALL_ERV_AIR_VOLUME_TO_PRESET,
        "air_volume_steps": SMALL_ERV_AIR_VOLUME_STEPS,
        "signature_keys": SMALL_ERV_SIGNATURE_KEYS,
    },
    DEVICE_SUBTYPE_MID_ERV: {
        "label": "MidERV",
        "get_url": "https://app.psmartcloud.com/App/ADevGetStatusMidERV",
        "set_url": "https://app.psmartcloud.com/App/ADevSetStatusMidERV",
        "default_params": DEFAULT_MID_ERV_PARAMS,
        "control_params": MID_ERV_CONTROL_PARAMS,
        "merge_current_status_for_control": False,
        "single_field_commands": True,
        "safe_control_keys": MID_ERV_SAFE_CONTROL_KEYS,
        "preset_to_air_volume": MID_ERV_PRESET_TO_AIR_VOLUME,
        "air_volume_to_preset": MID_ERV_AIR_VOLUME_TO_PRESET,
        "air_volume_steps": MID_ERV_AIR_VOLUME_STEPS,
        "run_mode_to_option": MID_ERV_RUN_MODE_TO_OPTION,
        "option_to_run_mode": MID_ERV_OPTION_TO_RUN_MODE,
        "signature_keys": MID_ERV_SIGNATURE_KEYS,
    },
    DEVICE_SUBTYPE_MID_ERV_DEHUMID: {
        "label": "MidERV Dehumid",
        "get_url": "https://app.psmartcloud.com/App/ADevGetStatusMidERV",
        "set_url": "https://app.psmartcloud.com/App/ADevSetStatusMidERV",
        "default_params": DEFAULT_DEHUMID_MID_ERV_PARAMS,
        "control_params": DEFAULT_DEHUMID_MID_ERV_PARAMS,
        "merge_current_status_for_control": False,
        "single_field_commands": False,
        "safe_control_keys": DEHUMID_MID_ERV_SAFE_CONTROL_KEYS,
        "preset_to_air_volume": {},
        "air_volume_to_preset": {},
        "air_volume_steps": [],
        "run_mode_to_option": DEHUMID_MID_ERV_RUN_MODE_TO_OPTION,
        "option_to_run_mode": DEHUMID_MID_ERV_OPTION_TO_RUN_MODE,
        "signature_keys": DEHUMID_MID_ERV_SIGNATURE_KEYS,
    },
}

SUPPORTED_ERV_CATEGORIES = {
    ERV_DEVICE_CATEGORY,
    ERV_DEVICE_CATEGORY_ALT,
}

SUPPORTED_ERV_DEVICE_HINTS = {
    DEVICE_SUBTYPE_SMALL_ERV,
    DEVICE_SUBTYPE_MID_ERV,
    DEVICE_SUBTYPE_MID_ERV_DEHUMID,
}
