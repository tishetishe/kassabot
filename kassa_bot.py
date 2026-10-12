import os
import re
import asyncio
from dotenv import load_dotenv
from reply_markup import kb
from datetime import datetime
from aiogram.fsm.state import State , StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message , CallbackQuery
from aiogram.filters import CommandStart , Command


load_dotenv()


API_TOKEN = os.getenv("API_TOKEN")


bot = Bot(token=API_TOKEN)
dp = Dispatcher()



class KassaStates(StatesGroup):
	start_kassa = State()
	main_menu = State()
	for_income = State()
	for_expenses = State()


data_store = {} #храним дни(скорее текущий день)


def valid_numbers(text):

	numbers = [] #все числа которые принимаем(тут лежат все готовые числа с коментами или без)
	lines = text.split('\n') #разделяем их по символам

	for line in lines:

		amount = 0 #для того что бы число и комент склеить вместе и разбирать каждую строчку
 
		com_val = re.search(r"(\d+[\d.кКkKмМmM\s]*)\s*(.*)" , line)
		#1 группа ищет число с приставкой(к - 1000 и м - 1000000) , а 2 группа коммент
		#и еще что бы он не триггерился на обычное слово с буквами к/м ставим \d+ указывая что сначало идет число , а потом буква
		if com_val:

			value = com_val.group(1).replace("." , "").strip() #заменяем число с точкой на обычное число
			comment = com_val.group(2).strip() #сохраняем комантарий

			if comment:

    				comment = comment.replace("(", "").replace(")", "")#убираем скобки в коменте

			if value.lower().endswith(('к' , 'k')):
					#добавляем в наш список число из цикла и срезаем у него букву умножая на ее значение
					amount = (float(value[:-1]) * 1000) 

			elif value.lower().endswith(('м' , 'm')):
				amount = (float(value[:-1]) * 1000000) #тоже самое с лямом

			else:
				amount = (float(value))

			is_withdrawal = "снял" in line.lower() #наше слово тригер

			numbers.append({"amount" : amount , "comment": comment, "is_withdrawal": is_withdrawal})
				#сохраняем в списке словарь с числом и его комментом 

	total = sum(item["amount"] for item in numbers)
	#берем каждое число из списка(item) и сумируем друг с другом
	return numbers , total
	#возвращаем оба что бы вернуло и общую сумму и отдельные строчки для итога в конце
	

def format_number(amount):
	if amount >= 1000:
		return f"{amount / 1000:g}к"
		#возврщаем косарь. g - убирает ноль у целый чисел и оставляеет дробь

	elif amount >= 1000000:
		return f"{amount / 1000000:g}м"
		#лям тож вернем в исходное положение

	return f"{int(amount):,}".replace(",", ".")
	#убираем копейки с помощью int и разделяем тысячи точками ибо питон разделяет их через , 




@dp.message(CommandStart())
async def send_welcome(message: Message , state: FSMContext):
        await message.answer("Привет!\nЯ бот для учета доходов и расходов.\nПожалуйста, укажите начальную кассу для начала работы")
        await state.set_state(KassaStates.start_kassa) 


@dp.message(KassaStates.start_kassa)
async def start_kassa_cmd(message: Message , state: FSMContext):
	try:
		parsed_items , skassa = valid_numbers(message.text)#редактируем наш текст

		if skassa == 0:
    			raise ValueError #если написали текст без числа

		await state.update_data(skassa=skassa)#сохраняем 
		await state.set_state(KassaStates.main_menu) #аля глушилка , ибо закрыть состояние не можем
		await message.reply(f"Начальная касса на сегодня:\n{format_number(skassa)}\n\nВыберите действие ниже, чтобы внести данные в кассу" , reply_markup=kb())

	except ValueError:
        	await message.reply("Пожалуйста, введите корректную сумму для начальной кассы")


@dp.callback_query(F.data == "income")
async def for_income(callback: CallbackQuery , state: FSMContext):
	await state.set_state(KassaStates.for_income)
	await callback.message.edit_text("Введите доходы столбиком\n(каждая операция с новой строки):")
	await callback.answer() #чтобы не было зависания кнопки



@dp.message(KassaStates.for_income)
async def income_cmd(message: Message , state: FSMContext):
	parsed_items, msg_total = valid_numbers(message.text)
	#берем тот же прицим из фунции parsed_items - все числа с коментами , msg_total - конкретное число

	withdrawals = 0 #счетчик именно снятий
	ordinary = 0 #счетчик остальных доходов


	if msg_total == 0:
		await message.reply("Пожалуйста, введите корректные данные для доходов")
		return

	for item in parsed_items:
		if item["is_withdrawal"]:
		#если есть хоть какой-то комент , то он его обрабатывает , а если нет , то кидает в else
			withdrawals += item["amount"] 
		else:
			ordinary += item["amount"]


	data = await state.get_data() #вытаскиваем все из памяти

	sum_income = data.get("sum_income", 0) + msg_total #это абсолюно все наши доходы
	sum_withdrawals = data.get("sum_withdrawals", 0) + withdrawals #это только снятия
	income_with_com = (data.get("income_with_com", "") + "\n" + message.text ).strip() #сохраняем в ориг виде
	

	await state.update_data(sum_income=sum_income, sum_withdrawals=sum_withdrawals, income_with_com=income_with_com) #сохраняем эти переменные
	await state.set_state(KassaStates.main_menu)
	await message.reply(f"+{format_number(msg_total)} добавлено\nВыберите следующее действие:", reply_markup=kb())
	#Показываем пользователю отформатированное число с точками



@dp.callback_query(F.data == "expenses")
async def for_expenses(callback: CallbackQuery , state: FSMContext):
	await state.set_state(KassaStates.for_expenses) #переходим к состоянию
	await callback.message.edit_text("Введите расходы столбиком\n(каждая операция с новой строки, комментарий в скобках):")
	await callback.answer() #чтобы не было зависания кнопки



@dp.message(KassaStates.for_expenses)
async def expenses_cmd(message: Message , state: FSMContext):
	ex_items, ex_total = valid_numbers(message.text)
	#делаем тоже самое , что и у доходов

	if ex_total == 0:
		await message.reply("Пожалуйста, введите корректные данные для расходов")
		return

	msg_expenses_text = "" #наша заготовка, если расходов не было  вернем пустоту

	for item in ex_items:
		f_amount = format_number(item["amount"]) 
		#достаем число наше с точками

		f_comment = f"({item['comment']})" if item['comment'] else ""
		#оборачиваем комент в скобках если он есть

		msg_expenses_text += f"Отдал - {f_amount}{f_comment}\n"
		#наше сообщение с Отдал , суммой и коментом


	data = await state.get_data() #вытаскиваем все из памяти

	sum_expenses = data.get("sum_expenses", 0) + ex_total #сумма всех расходов
	expenses_with_com = (data.get("expenses_with_com", "") + "\n" + msg_expenses_text).strip() #чтобы принимать все аргументы от пользователя
	await state.update_data(sum_expenses=sum_expenses , expenses_with_com=expenses_with_com) #сохраняем в памяти


	await state.set_state(KassaStates.main_menu)
	await message.reply(f"-{format_number(ex_total)} добавлено\nВыберите следующее действие:", reply_markup=kb())
	#Показываем пользователю отформатированное число с точками



@dp.callback_query(F.data == "end")
async def the_end(callback: CallbackQuery , state: FSMContext):
	current_date = datetime.now().strftime("%d.%m.%y") #текущая дата
	data = await state.get_data() #вытаксиваем все данные

	skassa = data.get("skassa", 0) #начальная касса
	sum_income = data.get("sum_income", 0) #все доходы
	sum_withdrawals = data.get("sum_withdrawals", 0) #только снятия
	sum_expenses = data.get("sum_expenses", 0) #все расходы
	income_with_com = data.get("income_with_com" , "Доходов не было") #доходы с ком
	expenses_with_com = data.get("expenses_with_com" , "Расходов не было") #расходы с ком

	total_balance = skassa + sum_income - sum_expenses 
	#общий балнас = начальная касса + все доходы - все расходы


	await callback.message.edit_text(
        	f"{current_date}\n"
       		f"☀️Касса в начале дня - {format_number(skassa)} \n"
        	f"{income_with_com}\n\n\n"
        	f"👉Итог:\n\n\n{expenses_with_com}\n\n"
            	f"\n"
        	f"🏦Снял - {format_number(sum_withdrawals)}\n"
        	f"📎Принял товар - {format_number(sum_expenses)}\n"
        	f"🏁Касса в конце дня - {format_number(total_balance)}"
        
    	)

	await state.clear() #завершаем наши состояния
	await callback.answer()


async def main():
	await dp.start_polling(bot)


if __name__ == "__main__":
	asyncio.run(main())