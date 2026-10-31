-- InternationalTown: configuration (Motor Town)

return {
    -- RPC received by your PC for every chat message:
    -- ClientChat(MotorTownPlayerState author, FString Message, EMTChatCategory Category, Color)
    hook_function = "/Script/MotorTown.MotorTownPlayerController:ClientChat",

    -- Display: "chat" = the translation appears in the game chat (normal line, under the author's name)
    --          "console" = only in the UE4SS console (if "chat" causes problems)
    display = "chat",
    -- Prefix added to translated lines (also used to avoid translating our own lines again)
    prefix = "»",

    -- Language the chat is translated into for you (set by INSTALLER.bat).
    -- "auto" = the language selected in the game (followed live if you change it),
    -- otherwise a forced ISO code: "fr", "en", "de", "pt", "zh-Hant"...
    player_language = "auto",
    -- Messages shorter than this (in letters) are ignored ("gg", "ok", "lol")
    min_chars = 4,
    -- Player names never translated (your own messages are already ignored automatically)
    ignore_senders = {},
    -- Also translate system messages (no author: server announcements, deliveries...)
    translate_system = false,
    -- Test: true = also translates YOUR messages (to check the display)
    translate_own = false,

    ------------------------------------------------------------------
    -- Sending: translate YOUR message before sending it
    ------------------------------------------------------------------
    -- In game: type your message (in any language), press the translation key:
    -- the text in the input box is replaced by its translation. Read it, then press Enter to send.
    -- Each server's language is set IN GAME: type "!servlang EN" in the chat, then Enter
    -- (the command stays on your PC: it is not sent, other players do not see it).
    -- It is remembered per server (servlang.txt). outgoing_language is only the default value
    -- for a server not set yet ("off" = nothing until you use !servlang).
    outgoing_language = "off",
    -- DEFAULT translation key (name from the UE4SS Key table: "F9", "ZERO" = 0 on the main keyboard, "NUM_ZERO" = 0 on
    -- the numeric keypad...). F9 is not used by Motor Town (F7 = report a player, F8 = hide the interface).
    -- Can be changed IN GAME: "!servtrad" + Enter, then press the key you want (saved in translate_key.txt, which takes
    -- precedence over this value). With a key that types a character (0, A…), that character is removed before
    -- translating, and a digit typed right after another digit ("10", "2000") does not trigger a translation.
    -- The same key, with the chat CLOSED, pauses / resumes the translation of incoming messages.
    outgoing_key = "F9",
    -- Motor Town chat widget (change it only if a game update renames it)
    chat_widget_class = "W_Chat_C",
    -- Help message (in your language) when joining a server, a few seconds after connecting
    join_notice = true,
    join_notice_delay_s = 8,

    poll_ms = 200,      -- how often the companion's answers are read
    timeout_s = 120,    -- a translation is given up after N seconds (leaves time for the companion to start)

    -- Spy mode (F8): logs every call of these functions, for debugging
    spy_key = "F8",
    spy_functions = {
        "/Script/MotorTown.MotorTownPlayerController:ClientChat",
        "/Script/MotorTown.MotorTownPlayerController:ClientChatLocalizedInternal",
    },
}
