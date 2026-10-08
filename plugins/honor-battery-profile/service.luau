--!nonstrict
-- System service for the HONOR FMB-P official EC charge profiles.

local SNAPSHOT = "honor-battery.snapshot"
local REQUEST = "honor-battery.request"
local SCRIPT = "/usr/local/bin/honor-battery-profile"
local BATTERY = "/sys/class/power_supply/BAT0"

local PROFILES = {
  home = { start = 40, finish = 70, label = "40/70" },
  office = { start = 70, finish = 90, label = "70/90" },
  travel = { start = 95, finish = 100, label = "95/100" },
}

local function read_trimmed(path)
  local value = noctalia.readFile(path)
  if value then
    return noctalia.string.trim(value)
  end
  return ""
end

local function number_at(path)
  return tonumber(read_trimmed(path)) or 0
end

local function profile_for(start_value, finish_value)
  for name, profile in pairs(PROFILES) do
    if start_value == profile.start and finish_value == profile.finish then
      return name, profile.label
    end
  end
  return "custom", tostring(start_value) .. "/" .. tostring(finish_value)
end

local function publish()
  local start_value = number_at(BATTERY .. "/charge_control_start_threshold")
  local finish_value = number_at(BATTERY .. "/charge_control_end_threshold")
  local name, label = profile_for(start_value, finish_value)
  local status = read_trimmed(BATTERY .. "/status")
  local capacity = number_at(BATTERY .. "/capacity")
  local current = number_at(BATTERY .. "/current_now")

  noctalia.state.set(SNAPSHOT, {
    available = start_value > 0 and finish_value > 0,
    profile = name,
    label = label,
    start = start_value,
    finish = finish_value,
    status = status,
    capacity = capacity,
    current = current,
  })
end

local pending = false
local function set_profile(name)
  local profile = PROFILES[name]
  if not profile or pending then
    return
  end

  pending = true
  local command = SCRIPT .. " set " .. profile.label
  noctalia.runAsync(command, function(result)
    pending = false
    if result.exitCode == 0 then
      noctalia.notify("HONOR 电池档位", "已切换到 " .. profile.label)
    else
      noctalia.notifyError("HONOR 电池档位", "切换失败，请检查系统服务和权限")
    end
    publish()
  end, 10000)
end

noctalia.state.watch(REQUEST, function(value)
  if type(value) == "string" then
    set_profile(value)
  end
end)

noctalia.setUpdateInterval(2000)
function update()
  publish()
end

publish()
