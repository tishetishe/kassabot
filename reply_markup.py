from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

def kb():
	builder = InlineKeyboardBuilder()
	b1 = InlineKeyboardButton(text="🏦Доход" , callback_data="income")
	b2 = InlineKeyboardButton(text="📎Расход" , callback_data="expenses")
	b3 = InlineKeyboardButton(text="🏁Завершить день" , callback_data="end")

	
	builder.add(b1 , b2 , b3)
	builder.adjust(1)
	return builder.as_markup()