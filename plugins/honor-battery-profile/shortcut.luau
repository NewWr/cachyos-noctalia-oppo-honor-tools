--!nonstrict
local SNAPSHOT = "honor-battery.snapshot"
local PANEL_ID = "dc/honor-battery-profile:panel"

local function render()
  local snapshot = noctalia.state.get(SNAPSHOT) or {}
  local label = snapshot.label or "档位"
  shortcut.setLabel("充电 " .. label)
  shortcut.setIcon("battery-charging", "battery")
  shortcut.setActive(snapshot.profile ~= "custom")
  shortcut.setEnabled(snapshot.available ~= false)
end

function onClick()
  noctalia.togglePanel(PANEL_ID)
end

noctalia.state.watch(SNAPSHOT, render)
render()
