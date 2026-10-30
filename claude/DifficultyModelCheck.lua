-- DifficultyModelCheck.lua
-- Spot check for DifficultyModel.lua on Simply Love's song select screen.
-- Whenever the selected song changes, shows a system message (top of the
-- screen) listing each dance-single chart of the song: its difficulty slot,
-- its official meter, and the model's rating, plus the raw and calibrated
-- values to compare with apply_model.py --lookup.
return Def.Actor{
	CurrentSongChangedMessageCommand = function(self)
		local song = GAMESTATE:GetCurrentSong()
		if not song then return end
		if not DifficultyModel then
			SCREENMAN:SystemMessage("DifficultyModel.lua is not loaded")
			return
		end
		local out = { song:GetDisplayMainTitle() }
		for _, s in ipairs(song:GetAllSteps()) do
			if ToEnumShortString(s:GetStepsType()) == "Dance_Single" then
				local r, raw, cal = DifficultyModel.Rating(s)
				local diff = ToEnumShortString(s:GetDifficulty())
				if r then
					out[#out + 1] = string.format(
						"%-9s meter %2d  model %2d  (raw %.4f  cal %.4f)",
						diff, s:GetMeter(), r, raw, cal)
				else
					out[#out + 1] = string.format(
						"%-9s meter %2d  model n/a (%s)", diff, s:GetMeter(), tostring(raw))
				end
			end
		end
		SCREENMAN:SystemMessage(table.concat(out, "\n"))
	end
}
