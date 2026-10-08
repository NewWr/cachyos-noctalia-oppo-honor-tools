--!nonstrict
-- Read-only HONOR FMB-P hwmon monitor. It never writes EC or fan controls.
local SNAPSHOT = "honor-fan.snapshot"
local BACKLIGHT = "honor-fan.backlight"
local BACKLIGHT_REQUEST = "honor-fan.backlight-request"
local BACKLIGHT_PATH = "/sys/class/leds/huawei::kbd_backlight/"
local BACKLIGHT_PERCENT = { off = 0, low = 50, high = 100 }
local pending = false

local function publish_backlight()
  local level = tonumber(noctalia.readFile(BACKLIGHT_PATH .. "brightness") or "")
  local maximum = tonumber(noctalia.readFile(BACKLIGHT_PATH .. "max_brightness") or "")
  noctalia.state.set(BACKLIGHT, {
    available = level ~= nil and maximum == 2,
    level = level,
    pending = pending,
  })
end

noctalia.state.watch(BACKLIGHT_REQUEST, function(value)
  if type(value) ~= "table" then return end
  local percentage = BACKLIGHT_PERCENT[value.name]
  if percentage == nil or pending then return end
  local maximum = tonumber(noctalia.readFile(BACKLIGHT_PATH .. "max_brightness") or "")
  if maximum ~= 2 then
    publish_backlight()
    noctalia.notifyError("键盘背光", "未检测到 HONOR 三档背光设备")
    return
  end
  pending = true
  publish_backlight()
  noctalia.runAsync("noctalia msg keyboard-backlight-set " .. tostring(percentage), function(result)
    pending = false
    publish_backlight()
    local actual = tonumber(noctalia.readFile(BACKLIGHT_PATH .. "brightness") or "")
    if result == nil or result.exitCode ~= 0 or actual ~= percentage / 50 then
      noctalia.notifyError("键盘背光", "切换失败，请重试")
    end
  end, 5000)
end)

local function publish(result)
  if result == nil then
    noctalia.state.set(SNAPSHOT, { available = false })
    return
  end
  if result.exitCode ~= 0 then
    noctalia.state.set(SNAPSHOT, { available = false })
    return
  end

  local fan1, fan2, found
  local temps = {}
  for line in result.stdout:gmatch("[^\n]+") do
    local kind, name, raw = line:match("^(%w+)|([^|]+)|(%d+)$")
    if kind == "fan" then
      if name == "1" then fan1 = tonumber(raw) end
      if name == "2" then fan2 = tonumber(raw) end
      found = true
    elseif kind == "temp" then
      table.insert(temps, {
        name = name,
        value = tonumber(raw) / 1000.0,
      })
    end
  end

  if fan1 == nil or fan2 == nil or #temps == 0 then
    noctalia.state.set(SNAPSHOT, { available = false })
    return
  end

  noctalia.state.set(SNAPSHOT, {
    available = found == true,
    fan1 = fan1,
    fan2 = fan2,
    temp = temps[1].value,
    temps = temps,
  })
end

local command = [[
fan1=0
fan2=0
found=0
cpu_package=0
cpu_core_max=0
nvme_composite=0
nvme_sensor1=0
nvme_sensor2=0
wifi_temp=0
acpi_temp=0
for d in /sys/class/hwmon/hwmon*; do
  name="$(cat "$d/name" 2>/dev/null)"
  case "$name" in
    honor_fmbp)
      fan1="$(cat "$d/fan1_input" 2>/dev/null || echo 0)"
      fan2="$(cat "$d/fan2_input" 2>/dev/null || echo 0)"
      found=1
      ;;
    coretemp)
      for f in "$d"/temp*_input; do
        [ -r "$f" ] || continue
        value="$(cat "$f" 2>/dev/null || echo 0)"
        label="$(cat "${f%_input}_label" 2>/dev/null || true)"
        case "$label" in
          "Package id 0") cpu_package="$value" ;;
          Core*) [ "$value" -gt "$cpu_core_max" ] && cpu_core_max="$value" ;;
        esac
      done
      ;;
    nvme)
      for f in "$d"/temp*_input; do
        [ -r "$f" ] || continue
        value="$(cat "$f" 2>/dev/null || echo 0)"
        label="$(cat "${f%_input}_label" 2>/dev/null || true)"
        case "$label" in
          Composite) nvme_composite="$value" ;;
          "Sensor 1") nvme_sensor1="$value" ;;
          "Sensor 2") nvme_sensor2="$value" ;;
        esac
      done
      ;;
    iwlwifi*) wifi_temp="$(cat "$d/temp1_input" 2>/dev/null || echo 0)" ;;
    acpitz*) acpi_temp="$(cat "$d/temp1_input" 2>/dev/null || echo 0)" ;;
  esac
done
printf "fan|1|%s\n" "$fan1"
printf "fan|2|%s\n" "$fan2"
[ "$cpu_package" -gt 0 ] && printf "temp|CPU Package|%s\n" "$cpu_package"
[ "$cpu_core_max" -gt 0 ] && printf "temp|CPU Core Max|%s\n" "$cpu_core_max"
[ "$nvme_composite" -gt 0 ] && printf "temp|NVMe Composite|%s\n" "$nvme_composite"
[ "$nvme_sensor1" -gt 0 ] && printf "temp|NVMe Sensor 1|%s\n" "$nvme_sensor1"
[ "$nvme_sensor2" -gt 0 ] && printf "temp|NVMe Sensor 2|%s\n" "$nvme_sensor2"
[ "$wifi_temp" -gt 0 ] && printf "temp|Wi-Fi|%s\n" "$wifi_temp"
[ "$acpi_temp" -gt 0 ] && printf "temp|ACPI|%s\n" "$acpi_temp"
]]

noctalia.setUpdateInterval(2000)

function update()
  publish_backlight()
  noctalia.runAsync(command, publish)
end

publish_backlight()
