--!nonstrict
local SNAPSHOT = "honor-battery.snapshot"
local REQUEST = "honor-battery.request"
local PANEL_ID = "dc/honor-battery-profile:panel"

local snapshot = noctalia.state.get(SNAPSHOT) or {
  available = false,
  profile = "custom",
  label = "--",
  status = "Unknown",
  capacity = 0,
}

local function request(name)
  noctalia.state.set(REQUEST, name)
end

local function profile_button(name, text, description)
  local selected = snapshot.profile == name
  return ui.button({
    text = text .. (selected and "  ✓" or ""),
    variant = selected and "primary" or "ghost",
    onClick = "on" .. name,
    tooltip = description,
  })
end

local function render()
  local status = snapshot.status
  if status == "Not charging" then
    status = "已停止充电"
  elseif status == "Charging" then
    status = "正在充电"
  elseif status == "Discharging" then
    status = "电池供电"
  elseif status == "Full" then
    status = "已充满"
  end

  panel.render(ui.column({ gap = 12, padding = 12 }, {
    ui.row({ align = "center", justify = "space_between" }, {
      ui.column({ gap = 2, flexGrow = 1 }, {
        ui.label({ text = "HONOR 电池充电档位", fontSize = 16, fontWeight = "bold" }),
        ui.label({
          text = snapshot.available and ("当前 " .. snapshot.label .. " · " .. tostring(snapshot.capacity) .. "% · " .. status) or "未检测到电池接口",
          fontSize = 12,
          color = "on_surface_variant",
        }),
      }),
      ui.button({ glyph = "close", variant = "ghost", onClick = "onClose" }),
    }),
    ui.separator({ thickness = 1, color = "outline/0.3", spacing = 2 }),
    ui.label({ text = "选择 HONOR 官方 EC 模式", color = "on_surface_variant" }),
    ui.column({ gap = 6 }, {
      profile_button("home", "40/70  家用", "40% 开始充电，70% 停止"),
      profile_button("office", "70/90  办公", "70% 开始充电，90% 停止"),
      profile_button("travel", "95/100  差旅", "95% 开始充电，100% 停止"),
    }),
    ui.label({
      text = "适配器会继续给电脑供电；档位只控制电池的充放电阈值。",
      fontSize = 11,
      color = "on_surface_variant",
      textAlign = "center",
    }),
  }))
end

function onOpen(_context)
  snapshot = noctalia.state.get(SNAPSHOT) or snapshot
  render()
end

function onClose()
  panel.close()
end

function onhome()
  request("home")
end

function onoffice()
  request("office")
end

function ontravel()
  request("travel")
end

noctalia.state.watch(SNAPSHOT, function(value)
  if type(value) == "table" then
    snapshot = value
    render()
  end
end)
