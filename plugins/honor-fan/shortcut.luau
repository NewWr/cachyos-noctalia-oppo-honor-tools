--!nonstrict
local PANEL_ID = "dc/honor-fan:panel"

function onClick()
  noctalia.togglePanel(PANEL_ID)
end

function onRightClick()
  noctalia.togglePanel("control-center:monitor")
end

shortcut.setLabel("HONOR 硬件")
shortcut.setIcon("wind", "hardware")
shortcut.setActive(true)
