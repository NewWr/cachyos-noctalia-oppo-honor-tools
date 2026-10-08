--!nonstrict
local SNAPSHOT = "honor-battery.snapshot"
local PANEL_ID = "dc/honor-battery-profile:panel"

local function render()
  local snapshot = noctalia.state.get(SNAPSHOT) or {}
  local label = snapshot.label or "--"
  local layout = barWidget.isVertical() and ui.column or ui.row
  barWidget.render(layout({ gap = 4, align = "center" }, {
    ui.glyph({ name = "battery-charging", size = 14 }),
    ui.label({ text = label, fontWeight = "bold" }),
  }))
  barWidget.setTooltip("HONOR 电池档位 " .. label)
end

function onClick()
  noctalia.togglePanel(PANEL_ID)
end

noctalia.state.watch(SNAPSHOT, render)
render()
