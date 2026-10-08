--!nonstrict
local SNAPSHOT = "honor-fan.snapshot"
local BACKLIGHT = "honor-fan.backlight"
local BACKLIGHT_REQUEST = "honor-fan.backlight-request"
local backlight = noctalia.state.get(BACKLIGHT) or { available = false }
local BACKLIGHT_NAMES = { [0] = "关闭", [1] = "低亮", [2] = "高亮" }
local snapshot = noctalia.state.get(SNAPSHOT) or {
  available = false,
  fan1 = 0,
  fan2 = 0,
  temp = 0,
  temps = {},
}

local function value_text(value, suffix)
  local number = tonumber(value)
  if number == nil then
    return "--" .. suffix
  end
  return string.format("%.0f%s", number, suffix)
end

local function metric(title, value, suffix)
  return ui.column({ gap = 1, flexGrow = 1 }, {
    ui.label({ text = title, color = "on_surface_variant", fontSize = 12 }),
    ui.label({ text = value_text(value, suffix), fontSize = 17, fontWeight = "bold" }),
  })
end

local DISPLAY_NAMES = {
  ["CPU Core Max"] = "CPU 核心最高",
  ["NVMe Composite"] = "NVMe 综合",
  ["NVMe Sensor 1"] = "NVMe 传感器 1",
  ["NVMe Sensor 2"] = "NVMe 传感器 2",
  ["Wi-Fi"] = "Wi-Fi",
  ["ACPI"] = "ACPI",
}

local function temperature_rows()
  local readings = {}
  for _, reading in ipairs(snapshot.temps or {}) do
    if reading.name ~= "CPU Package" then
      table.insert(readings, reading)
    end
  end
  local rows = {}
  for first = 1, #readings, 3 do
    local cells = {}
    for index = first, math.min(first + 2, #readings) do
      local reading = readings[index]
      table.insert(cells, metric(DISPLAY_NAMES[reading.name] or reading.name, reading.value, " °C"))
    end
    while #cells < 3 do
      table.insert(cells, ui.column({ flexGrow = 1 }, {}))
    end
    table.insert(rows, ui.row({ gap = 6 }, cells))
  end
  if #rows == 0 then
    table.insert(rows, ui.label({ text = "没有可用温度探头", color = "on_surface_variant" }))
  end
  return rows
end

local function render()
  local children = {
    ui.row({ align = "center", justify = "space_between" }, {
      ui.label({ text = "HONOR 硬件", fontSize = 16, fontWeight = "bold" }),
      ui.button({ glyph = "close", variant = "ghost", onClick = "onClose" }),
    }),
    ui.row({ gap = 6 }, {
      metric("风扇 1", snapshot.fan1, " RPM"),
      metric("风扇 2", snapshot.fan2, " RPM"),
      metric("CPU 封装", snapshot.temp, " °C"),
    }),
  }
  for _, row in ipairs(temperature_rows()) do
    table.insert(children, row)
  end
  table.insert(children, ui.separator({ thickness = 1, color = "outline/0.3", spacing = 3 }))
  table.insert(children, ui.label({ text = "键盘背光", fontWeight = "bold" }))
  local buttons = {}
  local actions = { "onBacklightOff", "onBacklightLow", "onBacklightHigh" }
  for level = 0, 2 do
    local selected = backlight.available and backlight.level == level
    table.insert(buttons, ui.button({
      text = BACKLIGHT_NAMES[level] .. (selected and "  ✓" or ""),
      variant = selected and "primary" or "ghost",
      enabled = backlight.available and not backlight.pending,
      onClick = actions[level + 1],
    }))
  end
  table.insert(children, ui.row({ gap = 6 }, buttons))
  panel.render(ui.column({ gap = 5, padding = 10 }, children))
end

function onOpen(_context)
  snapshot = noctalia.state.get(SNAPSHOT) or snapshot
  backlight = noctalia.state.get(BACKLIGHT) or backlight
  render()
end

function onClose()
  panel.close()
end

local function request_backlight(name)
  local previous = noctalia.state.get(BACKLIGHT_REQUEST)
  local id = type(previous) == "table" and tonumber(previous.id) or 0
  noctalia.state.set(BACKLIGHT_REQUEST, { name = name, id = (id or 0) + 1 })
end

function onBacklightOff()
  request_backlight("off")
end

function onBacklightLow()
  request_backlight("low")
end

function onBacklightHigh()
  request_backlight("high")
end

noctalia.state.watch(BACKLIGHT, function(value)
  if type(value) == "table" then
    backlight = value
    render()
  end
end)

noctalia.state.watch(SNAPSHOT, function(value)
  if type(value) == "table" then
    snapshot = value
    render()
  end
end)
