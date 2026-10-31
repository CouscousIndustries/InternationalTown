-- InternationalTown — client-side UE4SS mod for Motor Town
-- Translates incoming chat messages into the player's language.
-- Translation is done by the local companion (companion/), through files in bridge/.

local cfg = require("config")

local function log(fmt, ...)
    print("[InternationalTown] " .. string.format(fmt, ...) .. "\n")
end

------------------------------------------------------------------------
-- Paths: the mod folder is deduced from the location of this script
------------------------------------------------------------------------
local script = debug.getinfo(1, "S").source:gsub("^@", "")
local MOD_DIR = script:gsub("[\\/]Scripts[\\/]main%.lua$", "")
local IN_DIR = MOD_DIR .. "/bridge/in/"
local OUT_DIR = MOD_DIR .. "/bridge/out/"

------------------------------------------------------------------------
-- Utilities
------------------------------------------------------------------------
local function esc(s)
    return (s:gsub("\\", "\\\\"):gsub("\t", "\\t"):gsub("\r", ""):gsub("\n", "\\n"))
end

local function unesc(s)
    return (s:gsub("\\(.)", { t = "\t", n = "\n", ["\\"] = "\\" }))
end

-- Raw value of a UE4SS hook parameter (RemoteUnrealParam)
local function raw(p)
    if p == nil then return nil end
    local ok, v = pcall(function() return p:get() end)
    if ok then return v end
    return p
end

local function str(v)
    if v == nil then return nil end
    if type(v) == "string" then return v end
    local ok, s = pcall(function() return v:ToString() end)
    if ok and type(s) == "string" then return s end
    return nil
end

local function valid(obj)
    if obj == nil then return false end
    local ok, r = pcall(function() return obj:IsValid() end)
    return ok and r
end

local function addr(obj)
    local ok, a = pcall(function() return obj:GetAddress() end)
    return ok and a or nil
end

local function playerName(ps)
    if not valid(ps) then return nil end
    local ok, n = pcall(function() return ps:GetPlayerName():ToString() end)
    if ok and n ~= "" then return n end
    ok, n = pcall(function() return ps.PlayerNamePrivate:ToString() end)
    if ok and n ~= "" then return n end
    return nil
end

-- Copies a color struct (FColor or FLinearColor) into a Lua table
local function copyColor(c)
    if c == nil then return nil end
    local out = {}
    for _, k in ipairs({ "R", "G", "B", "A" }) do
        local ok, v = pcall(function() return c[k] end)
        if ok and type(v) == "number" then out[k] = v end
    end
    if next(out) then return out end
    return nil
end

local function letterCount(s)
    -- counts the characters that are neither spaces, digits nor ASCII punctuation
    local n = 0
    for ch in s:gmatch("[%z\1-\127\194-\244][\128-\191]*") do
        if #ch > 1 or ch:match("%a") then n = n + 1 end
    end
    return n
end

local ignored = {}
for _, name in ipairs(cfg.ignore_senders or {}) do ignored[name:lower()] = true end

------------------------------------------------------------------------
-- Player language
------------------------------------------------------------------------
-- In "auto" mode, the game language is read again every 10 s: if you change it in the options,
-- the next translations switch automatically.
local playerLang, langCheckedAt = nil, -1000
local function readGameLanguage()
    local lib = StaticFindObject("/Script/Engine.Default__KismetInternationalizationLibrary")
    if not valid(lib) then return nil end
    for _, fn in ipairs({ "GetCurrentLanguage", "GetCurrentCulture" }) do
        local ok, s = pcall(function() return lib[fn](lib):ToString() end)
        if ok and type(s) == "string" and s ~= "" then return s end
    end
    return nil
end

local function getPlayerLang()
    if cfg.player_language and cfg.player_language ~= "auto" then
        return cfg.player_language
    end
    if os.time() - langCheckedAt >= 10 then
        langCheckedAt = os.time()
        local ok, lang = pcall(readGameLanguage)
        lang = ok and lang or nil
        if lang and lang ~= playerLang then
            playerLang = lang
            log("game language: %s (translating into this language)", playerLang)
        end
    end
    return playerLang or "en"
end

------------------------------------------------------------------------
-- Cached game objects
------------------------------------------------------------------------
-- FindAllOf / FindFirstOf go through ALL the game objects (hundreds of thousands):
-- called regularly, they cause micro-freezes. We search once, keep the reference,
-- and only search again if the object is gone (map change, disconnection).
local function fullName(obj)
    local ok, n = pcall(function() return obj:GetFullName() end)
    return ok and n or ""
end

local objCache, objSearchAt = {}, {}
local function cachedFind(key, className, prefer, retry_s, strict)
    local o = objCache[key]
    if o ~= nil and valid(o) then return o end
    objCache[key] = nil
    if os.time() - (objSearchAt[key] or -1000) < (retry_s or 10) then return nil end
    objSearchAt[key] = os.time()
    local ok, all = pcall(FindAllOf, className)
    if not ok or not all then return nil end
    local fallback = nil
    for _, obj in ipairs(all) do
        local name = fullName(obj)
        if valid(obj) and not name:find("Default__", 1, true) then
            if not prefer or name:find(prefer, 1, true) then objCache[key] = obj; return obj end
            fallback = fallback or obj
        end
    end
    if strict then return nil end   -- only the "preferred" object will do (e.g. the chat actually displayed)
    objCache[key] = fallback
    return fallback
end

local lastPC = nil   -- the player's controller, remembered from the first received message
local function playerController()
    if lastPC ~= nil and valid(lastPC) then return lastPC end
    return cachedFind("pc", "MotorTownPlayerController", nil, 10)
end

local function gameState()
    return cachedFind("gs", "MotorTownGameState", nil, 10)
end

------------------------------------------------------------------------
-- Bridge to the companion
------------------------------------------------------------------------
-- Known player names (players present + authors already seen): never translated by the companion
local knownNames, namesAt = {}, -1000
local function playerNames()
    if os.time() - namesAt >= 10 then
        namesAt = os.time()
        pcall(function()
            local gs = gameState()
            if not gs then return end
            gs.PlayerArray:ForEach(function(_, elem)
                local n = playerName(elem:get())
                if n then knownNames[n] = true end
            end)
        end)
    end
    local list = {}
    for n in pairs(knownNames) do list[#list + 1] = n end
    return table.concat(list, "\31")
end

local session = tostring(os.time())
local nextId = 0
local pending = {}
local warnedBridge = false

local function requestTranslation(info)
    nextId = nextId + 1
    local id = session .. "_" .. nextId
    local tmp = IN_DIR .. id .. ".tmp"
    local f = io.open(tmp, "wb")
    if not f then
        if not warnedBridge then
            log("cannot write to %s (bridge folder missing?)", IN_DIR)
            warnedBridge = true
        end
        return
    end
    if info.sender then knownNames[info.sender] = true end
    f:write(table.concat({ id, info.culture or getPlayerLang(), esc(info.sender or ""), esc(info.text), esc(playerNames()),
        info.source_hint or "" }, "\t"))
    f:close()
    os.rename(tmp, IN_DIR .. id .. ".req")
    info.t = os.time()
    pending[id] = info
end

------------------------------------------------------------------------
-- Display: ClientChat is replayed locally with the translated text
------------------------------------------------------------------------
local injecting = false
local warnedDisplay = false

local function showInChat(info, line)
    log("%s%s", info.sender and (info.sender .. ": ") or "", line)
    if cfg.display ~= "chat" then return end
    if not valid(info.pc) then return end
    local ps = valid(info.ps) and info.ps or nil

    local ok, err = pcall(function()
        injecting = true
        info.pc:ClientChat(ps, line, info.category or 0, info.color or { R = 255, G = 255, B = 255, A = 255 })
    end)
    injecting = false
    if not ok and not warnedDisplay then
        warnedDisplay = true
        log("could not display in the chat (%s): set display = \"console\" in config.lua", tostring(err))
    end
end

local function pollResults()
    local now = os.time()
    for id, info in pairs(pending) do
        local path = OUT_DIR .. id .. ".res"
        local f = io.open(path, "rb")
        if f then
            local content = f:read("a") or ""
            f:close()
            os.remove(path)
            pending[id] = nil
            local src, tr = content:match("^([^\t]*)\t(.*)$")
            if info.onResult then
                info.onResult(src, tr and unesc(tr) or "")
            elseif src and src ~= "skip" and tr and tr ~= "" then
                showInChat(info, string.format("%s [%s] %s", cfg.prefix, src:upper(), unesc(tr)))
            end
        elseif now - info.t > (info.timeout or cfg.timeout_s) then
            pending[id] = nil
            if info.onTimeout then info.onTimeout() end
            log("timed out (is the companion running?)")
        end
    end
end

------------------------------------------------------------------------
-- Receiving: ClientChat(PlayerState, Message, Category, Color)
------------------------------------------------------------------------
local runCommand        -- defined below (Sending section): applies !servlang / !servtrad
local function isLocalCommand(text)
    local t = text:lower()
    return t:match("^%s*!servlang") ~= nil or t:match("^%s*!servtrad") ~= nil
end

local paused = false     -- key pressed outside the chat: pauses / resumes the translation of incoming messages (for the session)
local chatOpenFlag = false   -- chat opened (StartEnterChat) / closed (commit): fallback when keyboard focus cannot be read

local function onChatMessage(self, pPS, pMessage, pCategory, pColor)
    if injecting then return end
    local text = str(raw(pMessage))
    if not text or text == "" then return end
    if text:sub(1, #cfg.prefix) == cfg.prefix then return end
    local isCommand = isLocalCommand(text)
    if not isCommand and letterCount(text) < cfg.min_chars then return end

    local pc = raw(self)
    if valid(pc) then lastPC = pc end
    local ps = raw(pPS)
    local sender = playerName(ps)

    if sender == nil and not cfg.translate_system then return end
    if sender and ignored[sender:lower()] then return end

    -- your own messages: never translated. A local command echoed back by the server (interception failed,
    -- see onTextCommitted) is applied here as a last resort — runCommand applies it only once.
    local isMine = false
    if valid(ps) and valid(pc) then
        local ok, mine = pcall(function() return pc.PlayerState end)
        isMine = ok and valid(mine) and addr(mine) == addr(ps)
    end
    if isMine and runCommand and isCommand then
        runCommand(text)
        return
    end
    if isMine and not cfg.translate_own then return end
    if isCommand then return end
    if paused then return end

    requestTranslation({
        text = text,
        sender = sender,
        pc = pc,
        ps = ps,
        category = raw(pCategory),
        color = copyColor(raw(pColor)),
    })
end

local onTextCommitted, onServerSendChat   -- defined below (interception of local commands)
local hooks = {}       -- path -> true once registered
local hooked = false   -- all hooks registered
local lastTry = 0
local function tryHook()
    if hooked then return end
    if os.time() - lastTry < 2 then return end  -- retry every 2 s at most
    lastTry = os.time()
    local list = {
        { cfg.hook_function, onChatMessage },
        -- Enter in the chat: the game commits the text HERE, before anything is sent -> "!servlang" / "!servtrad" are held back here
        { cfg.commit_function or "/Script/MotorTown.ChatWidget:OnTextCommitted", onTextCommitted },
        -- chat opened (Enter): tells whether the key should translate the input or toggle the pause
        { cfg.open_function or "/Script/MotorTown.ChatWidget:StartEnterChat", function() chatOpenFlag = true end },
        -- safety net: the send to the server itself (message emptied if it is a local command)
        { cfg.send_function or "/Script/MotorTown.MotorTownPlayerController:ServerSendChat", onServerSendChat },
    }
    local all = true
    for _, h in ipairs(list) do
        if h[1] and h[1] ~= "" and not hooks[h[1]] then
            local ok = pcall(function() RegisterHook(h[1], h[2]) end)
            if ok then
                hooks[h[1]] = true
                log("hook active on %s", h[1])
            else
                all = false
            end
        end
    end
    hooked = all
end

------------------------------------------------------------------------
-- Sending: translate the text of the input box, before you send it
------------------------------------------------------------------------
-- You type your message and press the key (F9 by default, can be changed in game with !servtrad): the text of the
-- input box is replaced by its translation into the server language. You read it, then send it with Enter.
-- The game never waits: the translation arrives in the background. The server language is set with
-- "!servlang EN" (remembered per server). Both commands are HELD BACK when the chat is committed: they are never
-- sent to the server, other players do not see them.
local translatingInput = false

-- FText made by an official Unreal function (safer than UE4SS's FText() constructor)
local function makeText(s)
    local ok, t = pcall(function()
        local lib = StaticFindObject("/Script/Engine.Default__KismetTextLibrary")
        if valid(lib) then return lib:Conv_StringToText(s) end
    end)
    if ok and t ~= nil then return t end
    return FText(s)
end

-- The game keeps several W_Chat_C in memory (default object, HUD template): we take the real one,
-- the one living in the displayed HUD (/Engine/Transient… path).
local function chatTextBox()
    local w = cachedFind("chat", cfg.chat_widget_class or "W_Chat_C", "/Engine/Transient", 2, true)
    if not w then return nil end
    local ok, box = pcall(function() return w.ChatTextBox end)
    if ok and valid(box) then return box end
    objCache["chat"] = nil
    return nil
end

local function notify(msg)
    log("%s", msg)
    pcall(function()
        local pc = playerController()
        if valid(pc) then
            injecting = true
            pc:ClientChat(nil, cfg.prefix .. " " .. msg, 0, { R = 255, G = 255, B = 255, A = 255 })
        end
    end)
    injecting = false
end

-- Local message in the player's language: text written in English, translated by the companion.
-- "literal" (optional) is shown as is right after it (command to type, language codes).
local function localNotice(english, literal)
    local function show(text)
        notify("International Town — " .. text)
        if literal then notify(literal) end
    end
    local lang = getPlayerLang()
    if lang:lower():sub(1, 2) == "en" then show(english) return end
    requestTranslation({
        text = english,
        culture = lang,
        timeout = 15,
        onResult = function(src, translated)
            show((src and src ~= "skip" and translated ~= "") and translated or english)
        end,
        onTimeout = function() show(english) end,
    })
end

------------------------------------------------------------------------
-- Server language, remembered per server (unique world identifier: Net_WorldGuid)
------------------------------------------------------------------------
local SERVLANG_FILE = MOD_DIR .. "/servlang.txt"
local servlangs = {}          -- server id -> language code ("off" = disabled)
local currentServer = nil

local function loadServlangs()
    local f = io.open(SERVLANG_FILE, "rb")
    if not f then return end
    for line in f:lines() do
        local id, lang = line:match("^([%w%-]+)=([%w%-]+)")
        if id then servlangs[id] = lang end
    end
    f:close()
end

local function saveServlangs()
    local f = io.open(SERVLANG_FILE, "wb")
    if not f then log("cannot save %s", SERVLANG_FILE) return end
    local ids = {}
    for id in pairs(servlangs) do ids[#ids + 1] = id end
    table.sort(ids)
    for _, id in ipairs(ids) do f:write(id, "=", servlangs[id], "\n") end
    f:close()
end

local function serverId()
    local ok, id = pcall(function()
        local gs = gameState()
        if not gs then return nil end
        local g = gs.Net_WorldGuid
        local parts = {}
        for _, k in ipairs({ "A", "B", "C", "D" }) do
            local v = g[k]
            if type(v) ~= "number" then return nil end
            parts[#parts + 1] = string.format("%08x", v % 0x100000000)
        end
        local id = table.concat(parts, "-")
        if id ~= "00000000-00000000-00000000-00000000" then return id end
        return nil
    end)
    return ok and id or nil
end

-- Outgoing language in effect: the current server's, otherwise outgoing_language from config.lua
local function outgoingLanguage()
    if currentServer and servlangs[currentServer] then return servlangs[currentServer] end
    return cfg.outgoing_language or "off"
end

local LANG_HINT = "!servlang FR | EN | DE | ES | RU | PT | IT | PL…   (!servlang off)"

------------------------------------------------------------------------
-- Translation key: config.lua (outgoing_key), replaced by the one chosen in game with !servtrad
-- (saved in translate_key.txt). Key names: those of the UE4SS Key table (ZERO, F7, NUM_ZERO, A…).
------------------------------------------------------------------------
local KEY_FILE = MOD_DIR .. "/translate_key.txt"
local DIGITS = { "ZERO", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE" }
local translateKey = cfg.outgoing_key or "F9"

local function keyExists(k) return k ~= nil and Key ~= nil and Key[k] ~= nil end

-- Character typed by the key into the input box (digits and letters of the main keyboard), otherwise nil
local function keyChar(k)
    for i, name in ipairs(DIGITS) do if k == name then return tostring(i - 1) end end
    if k:match("^%u$") then return k end
    return nil
end

local function keyLabel(k)
    local c = keyChar(k)
    if c then return c end
    local n = k:match("^NUM_(%u+)$")
    if n then
        for i, name in ipairs(DIGITS) do if n == name then return "Num " .. (i - 1) end end
    end
    return k
end

-- "0", "f7", "num0", "A", "ZERO"… -> name in the Key table, or nil
local function normalizeKey(arg)
    local a = arg:upper():gsub("%s+", "")
    if a:match("^%d$") then return DIGITS[tonumber(a) + 1] end
    local n = a:match("^NUM_?(%d)$") or a:match("^NUMPAD_?(%d)$") or a:match("^PAV(%d)$")
    if n then return "NUM_" .. DIGITS[tonumber(n) + 1] end
    if keyExists(a) then return a end
    return nil
end

local function loadKey()
    local f = io.open(KEY_FILE, "rb")
    if not f then return end
    local k = (f:read("l") or ""):match("^%s*([%w_]+)")
    f:close()
    if keyExists(k) then translateKey = k end
end

-- UE4SS key bindings: every bound key makes a call into the game on EVERY press (driving included).
-- Normally only the translation key is bound; all keys are bound only for the !servtrad capture
-- (and stay bound until the game restarts: UE4SS cannot undo a binding).
local onKey                         -- defined below
local bound, allBound = {}, false
local function bindKey(name)
    if bound[name] or not keyExists(name) or name == cfg.spy_key then return end
    local ok = pcall(function()
        RegisterKeyBind(Key[name], function() ExecuteInGameThread(function() onKey(name) end) end)
    end)
    if ok then bound[name] = true end
end
local function bindAllKeys()
    if allBound then return end
    allBound = true
    local n = 0
    for name, code in pairs(Key) do
        if type(code) == "number" then bindKey(name); n = n + 1 end
    end
    log("key capture: %d keys listened to until the game restarts", n)
end

local function setKey(k)
    bindKey(k)
    translateKey = k
    local f = io.open(KEY_FILE, "wb")
    if f then f:write(k, "\n"); f:close() else log("cannot save %s", KEY_FILE) end
    log("translation key: %s", k)
    localNotice("translate key: " .. keyLabel(k) .. ". Type your message, press " .. keyLabel(k) .. ", then Enter.")
end

-- !servtrad: the NEXT key pressed becomes the translation key (Escape cancels); "!servtrad F7" sets it directly
local captureUntil = nil
local CAPTURE_IGNORE = { RETURN = true, ENTER = true, SHIFT = true, CONTROL = true, MENU = true, LEFT_SHIFT = true, RIGHT_SHIFT = true,
    LEFT_CONTROL = true, RIGHT_CONTROL = true, LEFT_MENU = true, RIGHT_MENU = true, LEFT_WIN = true, RIGHT_WIN = true, CAPS_LOCK = true }
local handleServtrad = function(text)
    local arg = text:match("^%s*!%a+%s+(%S+)")
    if arg then
        local k = normalizeKey(arg)
        if k then setKey(k) else localNotice("unknown key. Type !servtrad then press the key you want, or for example:", "!servtrad 0   !servtrad F7") end
        return
    end
    bindAllKeys()
    captureUntil = os.time() + 20
    localNotice("press the key you want to use to translate your messages (Escape to cancel). Current key: " .. keyLabel(translateKey))
end

local function handleServlang(text)
    local arg = (text:match("^%s*!%a+%s+(%S+)") or ""):lower()
    if arg == "" then
        local cur = outgoingLanguage()
        if cur == "off" then
            localNotice("translation of your messages is off on this server. Set it with:", LANG_HINT)
        else
            localNotice("your messages are translated into this language on this server: " .. cur:upper())
        end
        return
    end
    if arg ~= "off" and not (arg:match("^%a%a%a?$") or arg:match("^%a%a%-%a+$")) then
        localNotice("unknown language code. Examples:", LANG_HINT)
        return
    end
    if not currentServer then currentServer = serverId() end
    if currentServer then
        servlangs[currentServer] = arg
        saveServlangs()
    else
        cfg.outgoing_language = arg   -- server id not found: setting for this session only
    end
    if arg == "off" then
        localNotice("translation of your messages is now off on this server.")
    else
        localNotice("on this server, type your message then press " .. keyLabel(translateKey)
            .. " to translate it before sending. Language: " .. arg:upper())
    end
end

-- Language codes recognized as a prefix ("EN -hello" + key -> sent in English)
local PREFIX_CODES = {}
for code in ("AF SQ AR HY AZ EU BE BN NB NO BS BG CA ZH HR CS DA NL EN EO ET FI FR LG KA DE EL GU HE HI HU IS ID GA "
          .. "IT JA KK KO LV LT MK MS MI MR MN NN FA PL PT PA RO RU SR SN SK SL SO ST ES SW SV TL TA TE TH TS TN "
          .. "TR UK UR VI CY XH YO ZU"):gmatch("%u+") do PREFIX_CODES[code] = true end

-- "FR -text", "FR-text" or "FR - text" (code in CAPITALS followed by a dash) -> "fr", "text".
-- The dash avoids any confusion with a normal message ("DE rien", "SO COOL"…).
local function splitLangPrefix(text)
    local code, rest = text:match("^%s*(%u%u)%s*%-%s*(.-)%s*$")
    if not code or not PREFIX_CODES[code] or rest == "" then return nil, text end
    return code:lower(), rest
end

local function translateInputBox()
    if translatingInput then return end
    local box = chatTextBox()
    if not box then
        log("send: chat input box not found (open the chat before pressing the key)")
        return
    end
    local ok, text = pcall(function() return box:GetText():ToString() end)
    if not ok or not text then return end

    -- A key that also types a character (e.g. 0): that character has just arrived (or is about to arrive) in the input
    -- box. Right after a digit ("10", "2000"), you are typing a number: no translation. Otherwise the character is
    -- removed before translating.
    local ch = keyChar(translateKey)
    local typed = false
    if ch then
        if text:sub(-1):upper() == ch then
            local before = text:sub(-2, -2)
            if ch:match("%d") and before:match("%d") then return end
            text = text:sub(1, -2)
            typed = true
        elseif ch:match("%d") and text:sub(-1):match("%d") then
            return
        end
    end
    if text:match("^%s*$") then return end
    if typed then pcall(function() box:SetText(makeText(text)) end) end

    -- "!servlang …" / "!servtrad" + key: handled locally, nothing is sent to the chat
    if isLocalCommand(text) then
        pcall(function() box:SetText(makeText("")) end)
        runCommand(text)
        return
    end
    if text:sub(1, 1) == "/" then return end                     -- game commands: never translated

    -- language prefix to reply to someone: "EN your sentence" -> translated into English
    local forced, body = splitLangPrefix(text)
    local original = text
    if forced then text = body end

    local target = forced or outgoingLanguage()
    if target == "off" then
        localNotice("choose the language of this server first, then press "
            .. keyLabel(translateKey) .. " again:", LANG_HINT)
        return
    end

    translatingInput = true
    requestTranslation({
        text = text,
        culture = target,
        source_hint = getPlayerLang(),   -- if detection hesitates, it is probably your language
        timeout = 10,
        onResult = function(src, translated)
            translatingInput = false
            if not src or src == "skip" or translated == "" then
                log("send: already in %s (or nothing to translate), text unchanged", target:upper())
                -- with a prefix, the language code is still removed from the message
                if forced then pcall(function() box:SetText(makeText(text)) end) end
                return
            end
            -- if you kept typing in the meantime, nothing is replaced
            local okNow, current = pcall(function() return box:GetText():ToString() end)
            -- (the key's character may have arrived afterwards: "text0" counts as unchanged)
            if okNow and ch and current == original .. ch then current = original end
            if not valid(box) or not okNow or current ~= original then
                log("send: text changed during the translation, nothing replaced")
                return
            end
            local okSet, err = pcall(function() box:SetText(makeText(translated)) end)
            if okSet then
                log("send [%s→%s]: %s  =>  %s", src:upper(), target:upper(), text, translated)
            else
                log("send: could not replace the text (%s)", tostring(err))
            end
        end,
        onTimeout = function()
            translatingInput = false
            notify("International Town — translation failed: is the translator (start.bat) running?")
        end,
    })
end

------------------------------------------------------------------------
-- Local commands (!servlang, !servtrad): applied on your PC, never sent to the server
------------------------------------------------------------------------
-- The same command may be seen several times (commit, send, server echo): it is applied only once.
local lastCmd, lastCmdAt = nil, -100
runCommand = function(text)
    local key = text:lower():gsub("^%s+", ""):gsub("%s+", " ")
    if lastCmd == key and os.time() - lastCmdAt < 3 then return end
    lastCmd, lastCmdAt = key, os.time()
    if key:match("^!servtrad") then handleServtrad(text) else handleServlang(text) end
end

-- Enter in the chat: ChatWidget:OnTextCommitted(Text, CommitMethod) runs BEFORE anything is sent. For a local
-- command, the commit method is changed (ETextCommit::OnCleared = 3: the game sends nothing), the committed text and
-- the input box are emptied, then the command is applied.
onTextCommitted = function(self, pText, pMethod)
    chatOpenFlag = false
    local text = str(raw(pText))
    if not text or not isLocalCommand(text) then return end
    pcall(function() pMethod:set(3) end)
    pcall(function() pText:set(makeText("")) end)
    pcall(function() local box = chatTextBox(); if box then box:SetText(makeText("")) end end)
    log("command held back (not sent): %s", text)
    runCommand(text)
end

-- Safety net: if the command still goes out to the server, its text is emptied before sending.
onServerSendChat = function(self, pMessage, pCategory)
    local text = str(raw(pMessage))
    if not text or not isLocalCommand(text) then return end
    pcall(function() pMessage:set("") end)
    log("command held back at send: %s", text)
    runCommand(text)
end

-- Typing in the chat? Keyboard focus of the input box if the game provides it; otherwise text being typed;
-- otherwise the flag kept by the chat open / commit hooks.
local function isChatting()
    local box = chatTextBox()
    if box then
        local okF, focus = pcall(function() return box:HasKeyboardFocus() end)
        if okF and focus == true then return true end
        local okT, t = pcall(function() return box:GetText():ToString() end)
        if okT and t and t ~= "" then return true end
        if okF and focus == false then return false end
    end
    return chatOpenFlag
end

-- Key outside the chat: pauses / resumes the translation of incoming messages (your own input can still be translated)
local function togglePause()
    paused = not paused
    log("translation of incoming messages: %s", paused and "PAUSED" or "active")
    if paused then
        localNotice("translation of incoming messages paused. Press " .. keyLabel(translateKey) .. " outside the chat to resume.")
    else
        localNotice("translation of incoming messages resumed.")
    end
end

-- Every key goes through here: !servtrad capture, then the translation key
onKey = function(name)
    if captureUntil then
        if os.time() > captureUntil then
            captureUntil = nil
        elseif name == "ESCAPE" then
            captureUntil = nil
            localNotice("translate key unchanged: " .. keyLabel(translateKey))
            return
        elseif not CAPTURE_IGNORE[name] and not name:find("MOUSE", 1, true) then
            captureUntil = nil
            -- the character this key may have typed into the chat is removed
            local ch = keyChar(name)
            if ch then pcall(function()
                local box = chatTextBox()
                if box then
                    local t = box:GetText():ToString()
                    if t:sub(-1):upper() == ch then box:SetText(makeText(t:sub(1, -2))) end
                end
            end) end
            setKey(name)
            return
        end
    end
    if name == translateKey then
        if isChatting() then translateInputBox() else togglePause() end
    end
end

-- Joining a server: welcome message in the player's language
local joinCheckAt, joinNoticeAt, joinNoticeFor = 0, nil, nil
local function checkServerJoin()
    if os.time() - joinCheckAt < 3 then return end
    joinCheckAt = os.time()
    local id = serverId()
    if id and id ~= currentServer then
        currentServer = id
        joinNoticeFor, joinNoticeAt = id, os.time() + (cfg.join_notice_delay_s or 8)
        log("server: %s (outgoing language: %s)", id, outgoingLanguage())
    elseif not id then
        currentServer = nil
    end
    -- the message waits a few seconds for the chat to be displayed
    if joinNoticeAt and os.time() >= joinNoticeAt and joinNoticeFor == currentServer then
        joinNoticeAt = nil
        if cfg.join_notice == false then return end
        local key = keyLabel(translateKey)
        local lang = outgoingLanguage()
        if lang ~= "off" then
            localNotice("your messages are translated into " .. lang:upper()
                .. " on this server (type your message, press " .. key .. ", then Enter)." .. " Tip: to reply to someone in their language, start your message with its code and a dash (EN -, RU -, DE -…) and press " .. key .. "." .. " To change the server language, type in the chat (only you see it):", LANG_HINT)
        else
            localNotice("to write in your own language on this server, set the language of its chat." .. " Tip: to reply to someone in their language, start your message with its code and a dash (EN -, RU -, DE -…) and press " .. key .. "."
                .. " To set it, type in the chat (only you see it):", LANG_HINT)
        end
    end
end

------------------------------------------------------------------------
-- Spy mode (F8): logs the calls of the functions listed in config.lua
------------------------------------------------------------------------
local spyHooked = {}
local function describeParams(...)
    local out = {}
    for i, p in ipairs({ ... }) do
        local v = raw(p)
        local s = str(v) or playerName(v)
        if s == nil and type(v) ~= "userdata" then s = tostring(v) end
        out[#out + 1] = string.format("#%d=%s", i, s and ("\"" .. s .. "\"") or "?")
    end
    return table.concat(out, " ")
end

local function startSpy()
    local list = cfg.spy_functions or {}
    log("spy mode: %d functions", #list)
    for _, path in ipairs(list) do
        if not spyHooked[path] then
            local ok, err = pcall(function()
                RegisterHook(path, function(self, ...)
                    log("[spy] CALL %s %s", path, describeParams(...))
                end)
            end)
            spyHooked[path] = ok
            log("  %s %s", ok and "listening" or "FAILED", path)
        end
    end
end

------------------------------------------------------------------------
-- Startup
------------------------------------------------------------------------
log("loaded from %s", MOD_DIR)

if Key and Key[cfg.spy_key] then
    RegisterKeyBind(Key[cfg.spy_key], function()
        ExecuteInGameThread(startSpy)
    end)
end

loadKey()
bindKey(translateKey)          -- a single key listened to in normal play (see bindKey)
log("translation key: %s", keyLabel(translateKey))
loadServlangs()

-- Loop: registers the hooks as soon as possible and reads the companion's answers.
-- We only go into the game thread when there is really something to do:
-- a pending translation, a hook to register, or the server check (every 3 s).
local nextServerCheck = 0
LoopAsync(cfg.poll_ms, function()
    local now = os.time()
    local checkServer = now >= nextServerCheck
    if hooked and not next(pending) and not checkServer then return false end
    if checkServer then nextServerCheck = now + 3 end
    ExecuteInGameThread(function()
        if not hooked then tryHook() end
        if next(pending) then pollResults() end
        if checkServer then pcall(checkServerJoin) end
    end)
    return false
end)
