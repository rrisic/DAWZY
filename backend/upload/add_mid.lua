-- insert_moon.lua
local info = debug.getinfo(1, "S")
local script_path = info.source:match("@(.*[\\/])")
local audio_file = script_path .. "transcribed.mid"

reaper.SetEditCurPos(0, false, false)

reaper.InsertMedia(audio_file, 0)
