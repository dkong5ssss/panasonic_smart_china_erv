DOMAIN = "panasonic_smart_china"

CONF_USR_ID = "usrId"
CONF_DEVICE_ID = "deviceId"
CONF_TOKEN = "token"
CONF_SSID = "SSID"
CONF_DEVICE_SUBTYPE = "device_subtype"
CONF_DEVICE_TOKEN_OVERRIDE = "device_token_override"
CONF_FAMILY_ID = "familyId"
CONF_REAL_FAMILY_ID = "realFamilyId"

# Minimum seconds between silent re-logins triggered by runtime self-healing.
# Re-login kicks the previous cloud session (e.g. the phone app), so it must
# stay rare: only fires when familyId is missing and a cooldown has elapsed.
RELOGIN_COOLDOWN_SECONDS = 300

ERV_DEVICE_CATEGORY = "0800"
ERV_DEVICE_CATEGORY_ALT = "0850"
DEVICE_SUBTYPE_SMALL_ERV = "SMALLERV"
DEVICE_SUBTYPE_MID_ERV = "MIDERV"
DEVICE_SUBTYPE_MID_ERV_DEHUMID = "MIDERV_DEHUMID"
DEVICE_SUBTYPE_DC_ERV = "DCERV"
DEVICE_SUBTYPE_LD5C = "LD5C"
# AUTO = device not matched by devSubTypeId or statusAll signature at config
# time; the runtime probe loop in the coordinator will converge on a real
# protocol on the first fetch and persist it back to the config entry.
DEVICE_SUBTYPE_AUTO = "AUTO"

PRESET_LOW = "low"
PRESET_MEDIUM = "medium"
PRESET_HIGH = "high"

RUN_MODE_HEAT_EXCHANGE = "热交换"
RUN_MODE_EXTERNAL_CIRCULATION = "外循环"
RUN_MODE_INTERNAL_CIRCULATION = "内循环"
RUN_MODE_SLEEP = "睡眠"
RUN_MODE_AUTO_ECO = "自动ECO"
RUN_MODE_DEHUMID = "除湿"
RUN_MODE_SILENT = "静音"
RUN_MODE_NORMAL_VENTILATION = "普通换气"
RUN_MODE_MIXED_AIR = "混风"

SMALL_ERV_PRESET_TO_AIR_VOLUME = {
    PRESET_LOW: 1,
    PRESET_HIGH: 3,
}

MID_ERV_PRESET_TO_AIR_VOLUME = {
    PRESET_LOW: 1,
    PRESET_MEDIUM: 2,
    PRESET_HIGH: 3,
}

DC_ERV_PRESET_TO_AIR_VOLUME = {
    PRESET_LOW: 0,
    PRESET_HIGH: 1,
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

DC_ERV_AIR_VOLUME_TO_PRESET = {
    0: PRESET_LOW,
    1: PRESET_HIGH,
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

# LD5C (FY-25ZDP1C) run modes confirmed by real-device capture
# (mcdona1d/rudyll community probes): 0=热交换, 2=内循环, 5=外循环.
# Unlike MidERV there is no sleep or auto-ECO mode on this model.
LD5C_RUN_MODE_TO_OPTION = {
    0: RUN_MODE_HEAT_EXCHANGE,
    2: RUN_MODE_INTERNAL_CIRCULATION,
    5: RUN_MODE_EXTERNAL_CIRCULATION,
}

LD5C_OPTION_TO_RUN_MODE = {
    option: mode for mode, option in LD5C_RUN_MODE_TO_OPTION.items()
}

DC_ERV_RUN_MODE_TO_OPTION = {
    48: RUN_MODE_HEAT_EXCHANGE,
    49: RUN_MODE_SILENT,
    50: RUN_MODE_NORMAL_VENTILATION,
    51: RUN_MODE_INTERNAL_CIRCULATION,
    52: RUN_MODE_MIXED_AIR,
    53: RUN_MODE_AUTO_ECO,
    # Some firmware reports the read-side values as 0-5.
    0: RUN_MODE_HEAT_EXCHANGE,
    1: RUN_MODE_SILENT,
    2: RUN_MODE_NORMAL_VENTILATION,
    3: RUN_MODE_INTERNAL_CIRCULATION,
    4: RUN_MODE_MIXED_AIR,
    5: RUN_MODE_AUTO_ECO,
}

DC_ERV_OPTION_TO_RUN_MODE = {
    RUN_MODE_HEAT_EXCHANGE: 48,
    RUN_MODE_SILENT: 49,
    RUN_MODE_NORMAL_VENTILATION: 50,
    RUN_MODE_INTERNAL_CIRCULATION: 51,
    RUN_MODE_MIXED_AIR: 52,
    RUN_MODE_AUTO_ECO: 53,
}

SMALL_ERV_AIR_VOLUME_STEPS = [1, 3]
MID_ERV_AIR_VOLUME_STEPS = [1, 2, 3]
DC_ERV_AIR_VOLUME_STEPS = [0, 1]

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

DC_ERV_SIGNATURE_KEYS = {
    "preSet",
    "pmSen",
    "coSen",
    "tvSen",
    "userSupWind",
    "userExhWind",
    "aircJoi",
    "saPMC",
    "saTeC",
    "raCO2C",
    "raTVC",
    "oaFilExTL",
    "saFilExTL",
    "raFilExTL",
}

# LD5C devices report control fields with different names in the device-list
# statusAll payload (runningStatus/runningMode/airVolume). After the runtime
# field mapping these become runSta/runM/airVo, which is what the entity code
# consumes, so the signature keys are checked against the mapped result.
LD5C_SIGNATURE_KEYS = {
    "runSta",
    "runM",
    "airVo",
}

SENSOR_KEYS_BY_SUBTYPE = {
    DEVICE_SUBTYPE_DC_ERV: (
        "oaPMC",
        "saPMC",
        "raPMC",
        "oaHumC",
        "raHumC",
        "oaTeC",
        "saTeC",
        "raTeC",
        "raCO2C",
        "raTVC",
        "oaFilExTL",
        "saFilExTL",
        "raFilExTL",
    ),
}

# Protocol sentinels are field-specific: 255 can be a valid PM2.5 reading, while
# it is an invalid humidity/TVOC value.
SENSOR_INVALID_VALUES = {
    "oaPMC": frozenset({65535}),
    "saPMC": frozenset({65535}),
    "raPMC": frozenset({65535}),
    "oaHumC": frozenset({255}),
    "saHumC": frozenset({255}),
    "raHumC": frozenset({255}),
    "oaTeC": frozenset({127, 255}),
    "saTeC": frozenset({127, 255}),
    "raTeC": frozenset({127, 255}),
    "raCO2C": frozenset({65535}),
    "raTVC": frozenset({255}),
    "oaFilExTL": frozenset({65535}),
    "saFilExTL": frozenset({65535}),
    "raFilExTL": frozenset({65535}),
    "resFilExTL": frozenset({65535}),
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

# LD5C (FY-25ZDP1C) control state is reported by the device-list statusAll
# payload under runningStatus/runningMode/airVolume; sensors come from the
# MidERV endpoint. DEFAULT_LD5C_PARAMS uses the internal (mapped) names.
DEFAULT_LD5C_PARAMS = {
    "runSta": 0,
    "runM": 255,
    "airVo": 255,
    "holM": 255,
    "windPath": 0,
    "preSet": 255,
    "autoSen": 255,
    "heatingMode": 255,
    "alarmStatus": 0,
}

# LD5C control requests mirror the official Panasonic web control page
# (https://app.psmartcloud.com/ca/cn/0800/LD5C/index.html,
# js/common/api_utility.js): endpoint ADevSetStatusInfoLD5C, long camelCase
# field names, full bean with 255 = keep current (127 for timer hh/mm), only
# the target field changed per request. Short MidERV-style names
# (runSta/runM/airVo) sent to the MidERV set endpoint are silently ignored
# by the cloud for this device family (issue #1, v1.7.3).
LD5C_SET_DEFAULT_PARAMS = {
    "runningStatus": 255,
    "runningMode": 255,
    "airVolume": 255,
    "heatingMode": 255,
    "pPressureMode": 255,
    "holidayMode": 255,
    "autoSensitivity": 255,
    "oaFilterExist": 255,
    "saFilterClCycle": 255,
    "oaFilterClCycle": 255,
    "saFilterExCycle": 255,
    "oaFilterExCycle": 255,
    "saFilterExist": 255,
    "onTimerSetting": 255,
    "onTimerHour": 127,
    "onTimerMinute": 127,
    "offTimerSetting": 255,
    "offTimerHour": 127,
    "offTimerMinute": 127,
}

# Internal (status) field name -> wire (set payload) field name for LD5C.
LD5C_SET_FIELD_NAME_MAP = {
    "runSta": "runningStatus",
    "runM": "runningMode",
    "airVo": "airVolume",
    "holM": "holidayMode",
    "windPath": "windPath",
}

# Identity (usrId/deviceId/token) is sent at the top level of the request
# body for the Info-family endpoints, matching the official web page.
LD5C_SAFE_CONTROL_KEYS = [
    *LD5C_SET_DEFAULT_PARAMS.keys(),
]

# Field names used by the LD5C Info endpoints (ADevGetStatusInfoLD5C / the
# device-list statusAll payload), mapped to the internal names the entity code
# consumes. Extended in v1.7.4 to cover the full sensor set returned by the
# live Info GET endpoint.
LD5C_STATUS_ALL_FIELD_MAP = {
    "runningStatus": "runSta",
    "runningMode": "runM",
    "airVolume": "airVo",
    "holidayMode": "holM",
    "windPath": "windPath",
    "heatingMode": "heatingMode",
    "oaPM25Cur": "oaPMC",
    "saPM25Cur": "saPMC",
    "raPM25Cur": "raPMC",
    "oaTempCur": "oaTeC",
    "saTempCur": "saTeC",
    "raTempCur": "raTeC",
    "oaHumidityCur": "oaHumC",
    "raHumidityCur": "raHumC",
    "saHumidityCur": "saHumC",
}

DEFAULT_DC_ERV_PARAMS = {
    "runSta": 0,
    "runM": 255,
    "airVo": 255,
    "preSet": 255,
    "preM": 255,
    "holM": 255,
    "pmSen": 255,
    "coSen": 255,
    "tvSen": 255,
    "userSupWind": 255,
    "userExhWind": 255,
    "aircJoi": 255,
    "oaFilEx": 255,
}

for _index in range(1, 7):
    DEFAULT_DC_ERV_PARAMS[f"tSta{_index}"] = 255
    DEFAULT_DC_ERV_PARAMS[f"tM{_index}"] = 255
    DEFAULT_DC_ERV_PARAMS[f"tWind{_index}"] = 255
    DEFAULT_DC_ERV_PARAMS[f"tSet{_index}"] = 255
    DEFAULT_DC_ERV_PARAMS[f"tH{_index}"] = 127
    DEFAULT_DC_ERV_PARAMS[f"tMin{_index}"] = 127
    DEFAULT_DC_ERV_PARAMS[f"tWeek{_index}"] = 255

DC_ERV_CONTROL_PARAMS = {
    **DEFAULT_DC_ERV_PARAMS,
    "runSta": 255,
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

DC_ERV_SAFE_CONTROL_KEYS = [
    CONF_DEVICE_ID,
    CONF_TOKEN,
    CONF_USR_ID,
    *DEFAULT_DC_ERV_PARAMS.keys(),
]

MID_ERV_FILTER_SELECTS = (
    {
        "field": "saFilEx",
        "options": {1: "60天", 2: "90天", 3: "120天"},
        "suffix": "sa_filter_ex",
        "name_suffix": "PM2.5滤网更换周期",
        "icon": "mdi:air-filter",
    },
    {
        "field": "raFilEx",
        "options": {
            0: "180天",
            1: "210天",
            2: "240天",
            3: "270天",
            4: "300天",
            5: "330天",
            6: "365天",
        },
        "suffix": "ra_filter_ex",
        "name_suffix": "回风滤网更换周期",
        "icon": "mdi:air-filter",
    },
    {
        "field": "saFilCl",
        "options": {0: "30天", 1: "60天"},
        "suffix": "sa_filter_cl",
        "name_suffix": "PM2.5滤网清洗提醒",
        "icon": "mdi:broom",
    },
    {
        "field": "raFilCl",
        "options": {0: "30天", 1: "60天"},
        "suffix": "ra_filter_cl",
        "name_suffix": "回风滤网清洗提醒",
        "icon": "mdi:broom",
    },
)

DC_ERV_EXTRA_SELECTS = (
    {
        "field": "preSet",
        "options": {0: "标准模式", 1: "正压模式", 2: "自定义模式"},
        "suffix": "pressure_mode",
        "name_suffix": "压差模式",
        "icon": "mdi:gauge",
    },
    {
        "field": "preM",
        "options": {0: "弱", 1: "中", 2: "强"},
        "suffix": "pressure_level",
        "name_suffix": "正压强度",
        "icon": "mdi:gauge-low",
        "available_when": {"field": "preSet", "value": 1},
    },
    {
        "field": "userSupWind",
        "options": {0: "0%", 20: "20%", 40: "40%", 60: "60%", 80: "80%", 100: "100%"},
        "suffix": "supply_wind",
        "name_suffix": "自定义送风量",
        "icon": "mdi:arrow-up-circle-outline",
        "available_when": {"field": "preSet", "value": 2},
    },
    {
        "field": "userExhWind",
        "options": {0: "0%", 20: "20%", 40: "40%", 60: "60%", 80: "80%", 100: "100%"},
        "suffix": "exhaust_wind",
        "name_suffix": "自定义排风量",
        "icon": "mdi:arrow-down-circle-outline",
        "available_when": {"field": "preSet", "value": 2},
    },
    {
        "field": "oaFilEx",
        "options": {0: "90天", 1: "120天", 2: "150天", 3: "180天"},
        "suffix": "oa_filter_cycle",
        "name_suffix": "外滤网更换周期",
        "icon": "mdi:air-filter",
    },
    {
        "field": "pmSen",
        "options": {0: "35 µg/m³", 1: "50 µg/m³", 2: "75 µg/m³"},
        "suffix": "pm25_sensitivity",
        "name_suffix": "PM2.5触发阈值",
        "icon": "mdi:blur",
    },
    {
        "field": "coSen",
        "options": {0: "800 ppm", 1: "1000 ppm", 2: "1500 ppm"},
        "suffix": "co2_sensitivity",
        "name_suffix": "CO2触发阈值",
        "icon": "mdi:molecule-co2",
    },
    {
        "field": "tvSen",
        "options": {0: "低", 1: "高"},
        "suffix": "tvoc_sensitivity",
        "name_suffix": "TVOC触发阈值",
        "icon": "mdi:air-purifier",
    },
)

# Data-driven protocol detection. Vendor model strings are deliberately NOT
# used (substring model matching misidentified FY-25ZDP1C as MidERV); instead
# each protocol declares the statusAll/status field keys that identify it.
# Checked at config time against device metadata, and at runtime by the
# coordinator probe loop.
PROTOCOL_SIGNATURES = {
    DEVICE_SUBTYPE_LD5C: (
        "runningStatus",
        "runningMode",
        "airVolume",
        "holidayMode",
        "windPath",
    ),
    DEVICE_SUBTYPE_DC_ERV: DC_ERV_SIGNATURE_KEYS,
    DEVICE_SUBTYPE_MID_ERV_DEHUMID: DEHUMID_MID_ERV_SIGNATURE_KEYS,
    DEVICE_SUBTYPE_MID_ERV: MID_ERV_SIGNATURE_KEYS,
    DEVICE_SUBTYPE_SMALL_ERV: SMALL_ERV_SIGNATURE_KEYS,
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
        "extra_selects": (),
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
        "extra_selects": MID_ERV_FILTER_SELECTS,
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
        "extra_selects": (),
    },
    DEVICE_SUBTYPE_DC_ERV: {
        "label": "DCERV-03",
        "get_url": "https://app.psmartcloud.com/App/ADevGetStatusDCERV",
        "set_url": "https://app.psmartcloud.com/App/ADevSetStatusDCERV",
        "default_params": DEFAULT_DC_ERV_PARAMS,
        "control_params": DC_ERV_CONTROL_PARAMS,
        "merge_current_status_for_control": True,
        "single_field_commands": False,
        "safe_control_keys": DC_ERV_SAFE_CONTROL_KEYS,
        "preset_to_air_volume": DC_ERV_PRESET_TO_AIR_VOLUME,
        "air_volume_to_preset": DC_ERV_AIR_VOLUME_TO_PRESET,
        "air_volume_steps": DC_ERV_AIR_VOLUME_STEPS,
        "run_mode_to_option": DC_ERV_RUN_MODE_TO_OPTION,
        "option_to_run_mode": DC_ERV_OPTION_TO_RUN_MODE,
        "signature_keys": DC_ERV_SIGNATURE_KEYS,
        "extra_selects": DC_ERV_EXTRA_SELECTS,
        "status_request_id": 1,
        "status_ui_version": 4.0,
        "set_request_id": 1,
    },
    DEVICE_SUBTYPE_LD5C: {
        "label": "LD5C",
        # GET and SET both use the dedicated Info-family endpoints. The live
        # Info GET returns the device's own long camelCase fields (control
        # state + sensors), mapped to internal names via status_all_field_map.
        # The device-list statusAll cache is NOT used for reads - it does not
        # refresh after cloud control commands, which made the UI fall back to
        # stale OFF/unknown states (issue #1, v1.7.4).
        "get_url": "https://app.psmartcloud.com/App/ADevGetStatusInfoLD5C",
        "set_url": "https://app.psmartcloud.com/App/ADevSetStatusInfoLD5C",
        "default_params": DEFAULT_LD5C_PARAMS,
        "control_params": LD5C_SET_DEFAULT_PARAMS,
        "merge_current_status_for_control": False,
        "single_field_commands": True,
        "safe_control_keys": LD5C_SAFE_CONTROL_KEYS,
        "preset_to_air_volume": MID_ERV_PRESET_TO_AIR_VOLUME,
        "air_volume_to_preset": MID_ERV_AIR_VOLUME_TO_PRESET,
        "air_volume_steps": MID_ERV_AIR_VOLUME_STEPS,
        "run_mode_to_option": LD5C_RUN_MODE_TO_OPTION,
        "option_to_run_mode": LD5C_OPTION_TO_RUN_MODE,
        "signature_keys": LD5C_SIGNATURE_KEYS,
        "extra_selects": (),
        "status_request_id": 2,
        "set_request_id": 0,
        "uses_status_all": False,
        "status_all_field_map": LD5C_STATUS_ALL_FIELD_MAP,
        "status_identity_top_level": True,
        "set_field_name_map": LD5C_SET_FIELD_NAME_MAP,
        "set_identity_top_level": True,
        "use_xtoken_header": True,
        "supports_holiday_switch": False,
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
    DEVICE_SUBTYPE_DC_ERV,
    DEVICE_SUBTYPE_LD5C,
}
