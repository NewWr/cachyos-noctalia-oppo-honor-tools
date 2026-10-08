--!nonstrict
local SNAPSHOT_KEY = "oppo_pods_snapshot"
local COMMAND_KEY = "oppo_pods_command"
local STATUS_KEY = "oppo_pods_command_status"
local snapshot = noctalia.state.get(SNAPSHOT_KEY) or {}
local status = noctalia.state.get(STATUS_KEY) or {}
local tab = "controls"
local sequence = 0
local draft = nil
local draftRevision = 0
local render

local function tr(key, values) return noctalia.tr("panel." .. key, values) end
local function enabled() return snapshot.connected == true and status.busy ~= true end
local function send(action, value)
    if status.busy then return end
    sequence += 1
    noctalia.state.set(COMMAND_KEY, { action = action, value = value,
        nonce = tostring(noctalia.nowMs()) .. "-" .. tostring(sequence) })
end
local function label(text, color)
    return ui.label({ text = text, color = color or "on_surface_variant", fontSize = 12 })
end
local function section(title, children)
    return ui.column({ gap = 8, align = "stretch" }, {
        ui.label({ text = title, fontWeight = "bold", fontSize = 12, color = "on_surface_variant" }),
        ui.column({ gap = 8, align = "stretch" }, children),
    })
end

local function battery(side)
    local level = tonumber(snapshot["battery_" .. side]) or -1
    local charging = snapshot["charging_" .. side] == true
    local meta = charging and tr("charging") or ""
    if not charging and side ~= "case" then meta = tr("wear." .. (snapshot["wear_" .. side] or "unknown")) end
    if side == "case" and snapshot.case_offline then meta = tr("case_offline") end
    return ui.column({ flexGrow = 1, gap = 4, align = "stretch", padding = 10, fill = "surface_variant/0.5", radius = 10 }, {
        label(tr(side)),
        ui.label({ text = level >= 0 and tostring(level) .. "%" or tr("unknown"), fontSize = 18,
            fontWeight = "bold", color = level >= 0 and level <= 20 and not charging and "error" or "on_surface" }),
        ui.progress({ progress = math.max(0, level) / 100, height = 4, radius = 2,
            fill = charging and "secondary" or "primary" }),
        label(meta),
    })
end

local function noiseButton(mode)
    local selected = snapshot.noise_setting == mode or (mode == "anc" and snapshot.noise_mode == "anc")
    local removed = snapshot.product_id == "068C10" and (snapshot.wear_left == "removed" or snapshot.wear_left == "in_case")
        and (snapshot.wear_right == "removed" or snapshot.wear_right == "in_case")
    return ui.button({ key = "noise-" .. mode, text = tr("mode." .. mode), flexGrow = 1,
        variant = selected and "primary" or "ghost", selected = selected, enabled = enabled() and not removed,
        onClick = function() send("set-noise", mode) end })
end

local function switchRow(name)
    local checked = snapshot.features and snapshot.features[name] == true
    return ui.row({ key = "feature-" .. name, align = "center", gap = 12 }, {
        ui.label({ text = tr("feature." .. name), flexGrow = 1, fontSize = 13 }),
        ui.toggle({ checked = checked, enabled = enabled(),
            onChange = function(value) send("set-feature", { name = name, enabled = value == "true" }) end }),
    })
end

local function controls()
    local caps = snapshot.capabilities or {}
    local rows = { ui.row({ gap = 8, align = "stretch" }, { battery("left"), battery("case"), battery("right") }) }
    local modes = { noiseButton("anc"), noiseButton("transparency"), noiseButton("off") }
    if caps.adaptive then table.insert(modes, 2, noiseButton("adaptive")) end
    local noise = { ui.row({ gap = 4, align = "stretch" }, modes) }
    if caps.noise_levels and snapshot.wear_left ~= "worn" and snapshot.wear_right ~= "worn" then
        table.insert(noise, label(tr("noise_guidance")))
    end
    if caps.noise_levels then
        table.insert(noise, ui.row({ gap = 4, align = "stretch" }, {
            noiseButton("smart"), noiseButton("light"), noiseButton("medium"), noiseButton("deep"),
        }))
    end
    if snapshot.noise_realtime then table.insert(noise, label(tr("realtime_level", { level = tr("mode." .. snapshot.noise_realtime) }))) end
    table.insert(rows, section(tr("noise_control"), noise))
    local switches = {}
    for _, name in ipairs({ "dual_device", "game_mode", "spatial_sound", "wear_detection", "hearing_enhancement" }) do
        if caps[name] then table.insert(switches, switchRow(name)) end
    end
    if caps.wear_detection and snapshot.features and snapshot.features.wear_detection then
        local desktop = snapshot.desktop_pause or {}
        table.insert(switches, label(tr("desktop_pause." .. (desktop.status or "waiting")), desktop.status == "failed" and "error" or nil))
        if desktop.resume_armed == true then
            table.insert(switches, label(tr("desktop_pause.resume_ready")))
        end
    end
    if #switches > 0 then table.insert(rows, section(tr("features"), switches)) end
    if caps.find_device then
        local removed = (snapshot.wear_left == "removed" or snapshot.wear_left == "in_case")
            and (snapshot.wear_right == "removed" or snapshot.wear_right == "in_case")
        table.insert(rows, section(tr("find.title"), {
            ui.row({ gap = 6 }, {
                ui.button({ text = tr("find.start"), glyph = "volume", enabled = enabled() and removed and snapshot.finding ~= true,
                    onClick = function() send("find", true) end }),
                ui.button({ text = tr("find.stop"), enabled = enabled() and snapshot.finding == true,
                    onClick = function() send("find", false) end }),
            }),
            label(tr("find.guidance")),
        }))
    end
    return rows
end

local function copyEntry(entry)
    local result = { id = entry.id, name = entry.name, minimum = entry.minimum, maximum = entry.maximum, bands = {} }
    for _, band in ipairs(entry.bands or {}) do table.insert(result.bands, { frequency = band.frequency, gain = band.gain }) end
    return result
end

local function edit(entry)
    draft = copyEntry(entry)
    draftRevision += 1
    render()
end

local function eqLabel(preset)
    return preset.key and tr("eq.preset." .. preset.key) or preset.name
end

local function equalizer()
    local caps = snapshot.capabilities or {}
    if not caps.eq then return { label(tr("unavailable")) } end
    local options, chosen = {}, 0
    for index, preset in ipairs(snapshot.eq_presets or {}) do
        table.insert(options, eqLabel(preset))
        if preset.id == snapshot.eq_current then chosen = index - 1 end
    end
    local rows = draft and {} or { section(tr("eq.title"), {
        ui.select({ key = "eq-preset", options = options, selectedIndex = chosen, enabled = enabled(),
            onChange = function(index)
                local preset = (snapshot.eq_presets or {})[(tonumber(index) or 0) + 1]
                if preset then send("set-eq", preset.id) end
            end }),
    }) }
    if caps.custom_eq and not draft then
        local entries = {}
        for _, entry in ipairs(snapshot.custom_equalizers or {}) do
            local current = entry.id == snapshot.eq_current
            table.insert(entries, ui.row({ key = "custom-eq-" .. tostring(entry.id), gap = 6, align = "center" }, {
                ui.label({ text = entry.name .. (current and (" · " .. tr("eq.current")) or ""), flexGrow = 1, fontSize = 13 }),
                ui.button({ text = tr("eq.edit"), variant = "ghost", enabled = enabled(), onClick = function() edit(entry) end }),
                ui.button({ text = tr("eq.delete"), variant = "ghost", enabled = enabled() and not current,
                    onClick = function() send("delete-eq", { id = entry.id }) end }),
            }))
        end
        table.insert(entries, ui.button({ text = tr("eq.create"), glyph = "plus", enabled = enabled(), onClick = function()
            local bands = {}
            local source = (snapshot.custom_equalizers or {})[1]
            if source then
                for _, band in ipairs(source.bands) do table.insert(bands, { frequency = band.frequency, gain = 0 }) end
            else
                for _, frequency in ipairs({62, 250, 1000, 4000, 8000, 16000}) do table.insert(bands, { frequency = frequency, gain = 0 }) end
            end
            edit({ id = 0, name = "", minimum = source and source.minimum or -6, maximum = source and source.maximum or 6, bands = bands })
        end }))
        table.insert(entries, label(tr("eq.delete_guidance")))
        table.insert(rows, section(tr("eq.custom"), entries))
    end
    if draft then
        local editor = { ui.input({ key = "eq-name-" .. tostring(draftRevision), value = draft.name,
            placeholder = tr("eq.name"), enabled = enabled(), onChange = function(value) draft.name = value; render() end }) }
        local graph = {}
        for index, band in ipairs(draft.bands) do
            table.insert(graph, (band.gain - draft.minimum) / math.max(1, draft.maximum - draft.minimum))
            table.insert(editor, ui.row({ gap = 10, align = "center" }, {
                ui.label({ text = tostring(band.frequency) .. " Hz", width = 76, fontSize = 12 }),
                ui.slider({ key = "eq-gain-" .. tostring(draftRevision) .. "-" .. tostring(index), flexGrow = 1,
                    min = draft.minimum, max = draft.maximum, step = 1, value = band.gain, enabled = enabled(),
                    onChange = function(value)
                        band.gain = math.max(draft.minimum, math.min(draft.maximum, math.floor(tonumber(value) or 0)))
                        render()
                    end }),
                ui.label({ text = string.format("%+d dB", band.gain), width = 54, textAlign = "end", fontSize = 12 }),
            }))
        end
        table.insert(editor, 2, ui.graph({ values = graph, height = 50, color = "primary", fillOpacity = 0.15 }))
        table.insert(editor, ui.row({ gap = 6 }, {
            ui.button({ text = tr("eq.save"), variant = "primary", enabled = enabled() and draft.name ~= "",
                onClick = function() send("save-eq", copyEntry(draft)) end }),
            ui.button({ text = tr("eq.cancel"), variant = "ghost", enabled = status.busy ~= true,
                onClick = function() draft = nil; render() end }),
        }))
        table.insert(rows, section(draft.id == 0 and tr("eq.create") or tr("eq.edit"), editor))
    end
    return rows
end

local function information()
    local rows = {}
    for _, item in ipairs({ {tr("device.model"), snapshot.model_name or snapshot.device_name},
        {tr("device.firmware"), snapshot.firmware_version}, {tr("device.codec"), snapshot.codec},
        {tr("device.product"), snapshot.product_id}, {tr("device.address"), snapshot.mac},
        {tr("device.sync"), snapshot.notifications_active and tr("device.realtime") or tr("device.polling")} }) do
        table.insert(rows, ui.row({ gap = 10, align = "center" }, {
            ui.label({ text = item[1], flexGrow = 1, fontSize = 12, color = "on_surface_variant" }),
            ui.label({ text = item[2] or tr("unknown"), fontSize = 12 }),
        }))
    end
    local deviceRows = {}
    for _, device in ipairs(snapshot.devices or {}) do
        local connection = device.connection_state == 2 and tr("device.connected") or (device.connection_state == 0 and tr("device.saved") or tr("unknown"))
        table.insert(deviceRows, ui.column({ key = "device-" .. device.address, gap = 3 }, {
            ui.label({ text = device.name .. " · " .. connection, fontSize = 13 }), label(device.address),
        }))
    end
    return { section(tr("device.title"), rows), section(tr("device.list"), deviceRows) }
end

render = function()
    local connected = snapshot.connected == true
    local children = {}
    if connected then
        children = tab == "eq" and equalizer() or (tab == "devices" and information() or controls())
    else
        children = { ui.label({ text = tr("status.disconnected"), fontSize = 16, fontWeight = "bold" }), label(tr("guidance")) }
    end
    local tabs = {}
    for _, name in ipairs({ "controls", "eq", "devices" }) do
        table.insert(tabs, ui.button({ text = tr("tab." .. name), selected = tab == name, flexGrow = 1,
            variant = tab == name and "primary" or "ghost", onClick = function() tab = name; render() end }))
    end
    local notice = status.busy and tr("working") or (status.error or "")
    panel.render(ui.column({ flexGrow = 1, gap = 10, align = "stretch", padding = 4 }, {
        ui.row({ gap = 10, align = "center" }, {
            ui.image({ path = snapshot.device_image or "icons/oppo-pods.svg", width = 42, height = 42, fit = "contain" }),
            ui.column({ gap = 2, flexGrow = 1, align = "stretch" }, {
                ui.label({ text = snapshot.model_name or tr("title"), fontSize = 16, fontWeight = "bold", maxLines = 1 }),
                label(connected and tr("status.connected") or tr("status.disconnected")),
            }),
            ui.button({ glyph = "refresh", variant = "ghost", enabled = enabled(), onClick = function() send("refresh") end }),
            ui.button({ glyph = "close", variant = "ghost", onClick = function() panel.close() end }),
        }),
        ui.row({ gap = 4, align = "stretch" }, tabs),
        ui.label({ text = notice, visible = notice ~= "", fontSize = 12, color = status.error ~= "" and status.error ~= nil and "error" or "on_surface_variant" }),
        ui.scroll({ key = "body-" .. tab, flexGrow = 1, gap = 18, align = "stretch" }, children),
    }))
end

noctalia.state.watch(SNAPSHOT_KEY, function(value)
    if type(value) == "table" then snapshot = value; render() end
end)
noctalia.state.watch(STATUS_KEY, function(value)
    if type(value) ~= "table" then return end
    status = value
    if value.success and value.action == "save-eq" and draft and value.preset_id then draft.id = value.preset_id end
    render()
end)

function onOpen(_context)
    snapshot = noctalia.state.get(SNAPSHOT_KEY) or snapshot
    status = noctalia.state.get(STATUS_KEY) or status
    send("refresh")
    render()
end

function onIpc(event, payload)
    if event == "show-tab" and (payload == "controls" or payload == "eq" or payload == "devices") then
        tab = payload
        render()
    elseif event == "edit-eq" then
        local id = tonumber(payload)
        for _, entry in ipairs(snapshot.custom_equalizers or {}) do
            if entry.id == id then tab = "eq"; edit(entry); return end
        end
    elseif event == "cancel-eq" then
        draft = nil
        render()
    end
end
