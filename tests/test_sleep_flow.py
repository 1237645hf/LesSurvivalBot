"""Проверки callback-клавиатур общей сюжетной сцены."""

from keyboards import cat_kb, peek_kb, wolf_kb


def test_pet_story_callback_names_match_tz_contract():
	wolf_values = {
		row[0].callback_data for row in wolf_kb.inline_keyboard
	}
	assert {"wolf_leave", "wolf_torch"} <= wolf_values

	pet_values = {
		row[0].callback_data for row in cat_kb.inline_keyboard
	}
	assert {"pet_leave", "pet_take"} <= pet_values
	assert peek_kb.inline_keyboard[0][0].callback_data == "peek_den"
