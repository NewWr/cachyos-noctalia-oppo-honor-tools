--!nonstrict
-- Own the verified Free4 controller and share its live state with both UI entries.
local SNAPSHOT_KEY = "oppo_pods_snapshot"
local COMMAND_KEY = "oppo_pods_command"
local STATUS_KEY = "oppo_pods_command_status"
local scriptPath = noctalia.pluginDir() .. "/scripts/oppo_ctl.py"
local busy = false
local lastLine = 0
local checkingProcess = false
local lowLevels = {}
local monitorMac = noctalia.getConfig("device_mac") or ""
local monitorPause = noctalia.getConfig("pause_on_remove") ~= false

local function cli(command, value)
    local argv = { "python3", scriptPath, command }
    if value ~= nil then table.insert(argv, value) end
    local mac = noctalia.getConfig("device_mac")
    if mac and mac ~= "" then
        table.insert(argv, "--mac")
        table.insert(argv, mac)
    end
    return argv
end

local function updateSnapshot(data)
    if type(data) ~= "table" then return end
    noctalia.state.set(SNAPSHOT_KEY, data)
    if data.connected ~= true or noctalia.getConfig("low_battery_notifications") == false then return end
    for _, side in ipairs({ "left", "right" }) do
        local level = tonumber(data["battery_" .. side]) or -1
        local key = (data.mac or "") .. ":" .. side
        local tier = level >= 0 and level <= 10 and 2 or (level >= 0 and level <= 20 and 1 or 0)
        if data["charging_" .. side] == true or level > 25 then lowLevels[key] = 0 end
        if tier > (lowLevels[key] or 0) and data["charging_" .. side] ~= true then
            lowLevels[key] = tier
            noctalia.notify(data.model_name or "OPPO Pods", noctalia.tr("notify.low_battery", {
                side = noctalia.tr("panel." .. side), level = level,
            }), "battery-low")
        end
    end
end

local function decode(text)
    local ok, value = pcall(function() return noctalia.json.decode(text) end)
    return ok and type(value) == "table" and value or nil
end

local function shellQuote(value)
    return "'" .. string.gsub(value, "'", "'\\''") .. "'"
end

local function startMonitor()
    local command = "exec python3 -u " .. shellQuote(scriptPath) .. " monitor"
    local mac = noctalia.getConfig("device_mac")
    if mac and mac ~= "" then command ..= " --mac " .. shellQuote(mac) end
    if noctalia.getConfig("pause_on_remove") == false then command ..= " --no-desktop-pause" end
    noctalia.runStream(command, function(line)
        local value = decode(line)
        if value then
            lastLine = noctalia.nowMs()
            updateSnapshot(value)
        end
    end)
end

local function executeCommand(request)
    if type(request) ~= "table" or not request.action or busy then return end
    local action = request.action
    if action == "set-noise" then action = "set-anc" end
    if action == "cycle-noise" then action = "cycle-anc" end
    if action == "refresh" then action = "status" end
    local allowed = { ["set-anc"] = true, ["cycle-anc"] = true, ["set-feature"] = true,
        ["set-eq"] = true, ["save-eq"] = true, ["delete-eq"] = true, ["find"] = true, ["status"] = true }
    if not allowed[action] then return end
    local encoded = noctalia.json.encode({ action = action, value = request.value })
    if not encoded then return end
    busy = true
    noctalia.state.set(STATUS_KEY, { busy = true, error = "", action = action })
    local started = noctalia.runAsync(cli("request", encoded), function(result)
        busy = false
        local parsed = result and decode(result.stdout or "")
        if parsed and parsed.snapshot then updateSnapshot(parsed.snapshot) end
        local errorText = ""
        if not parsed or parsed.success ~= true then
            local code = parsed and parsed.error_code or "timeout"
            errorText = noctalia.tr("error." .. code)
            if errorText == "error." .. code then errorText = (parsed and parsed.error) or noctalia.tr("error.timeout") end
            noctalia.notify("OPPO Pods", errorText, "alert-circle")
        end
        noctalia.state.set(STATUS_KEY, { busy = false, error = errorText, action = action,
            success = parsed and parsed.success == true, preset_id = parsed and parsed.preset_id })
    end, 30000)
    if not started then
        busy = false
        noctalia.state.set(STATUS_KEY, { busy = false, error = noctalia.tr("error.connection") })
    end
end

function onIpc(event, payload)
    local value = payload
    if event == "set-feature" or event == "save-eq" or event == "delete-eq" then value = decode(payload or "") end
    if event == "set-eq" then value = tonumber(payload) end
    if event == "find" then value = payload == "true" end
    executeCommand({ action = event, value = value })
end

noctalia.state.watch(COMMAND_KEY, executeCommand)
noctalia.state.set(STATUS_KEY, { busy = false, error = "" })
startMonitor()
noctalia.setUpdateInterval(2000)

function update()
    if noctalia.nowMs() - lastLine < 8000 or checkingProcess then return end
    checkingProcess = true
    noctalia.processMatches(function(matched)
        checkingProcess = false
        if not matched then startMonitor() end
    end, scriptPath, "monitor")
end

function onConfigChanged()
    local mac = noctalia.getConfig("device_mac") or ""
    local pause = noctalia.getConfig("pause_on_remove") ~= false
    if mac == monitorMac and pause == monitorPause then return end
    monitorMac = mac
    monitorPause = pause
    noctalia.runAsync(cli("request", noctalia.json.encode({ action = "configure", value = {
        mac = mac, pause_on_remove = pause,
    } })), function(result)
        local parsed = result and decode(result.stdout or "")
        if parsed and parsed.snapshot then updateSnapshot(parsed.snapshot) end
    end, 30000)
end
